"""Compose the native agent with governed providers and existing Idea lineage."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid5

from pydantic import Field, model_validator
from pydantic_ai.toolsets import FunctionToolset
from pydantic_core import to_jsonable_python

from alon_ai.agents.idea_agent import run_idea_agent
from alon_ai.agents.idea_discovery import (
    IdeaCandidateAdvice,
    IdeaCandidateSetAdvice,
    ReturnedIdeaBriefAdvice,
    SeededIdeaBriefAdvice,
    SelectedCandidateIdeaBriefAdvice,
)
from alon_ai.agents.runtime import OpenAIExecution
from alon_ai.agents.schemas.idea import (
    IdeaAgentInput,
    IdeaOperation,
    IncompleteDiscovery,
    MarketResearchAssessment,
    PriceKind,
    PriceObservation,
    ResearchBasis,
    ResearchedCandidateSet,
    ResearchedOpportunity,
)
from alon_ai.agents.schemas.openai import Route, canonical_json, sha256
from alon_ai.agents.tools.research import ResearchTools
from alon_ai.db.repositories.accounting import (
    GovernanceProvisioner,
    GovernanceRepository,
)
from alon_ai.db.repositories.agent_run_steps import AgentRunStepRepository
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.repositories.intake import IntakeRepository
from alon_ai.db.repositories.openai_idea import OpenAIIdeaInputRepository
from alon_ai.db.repositories.openai_live import _ensure_exact_config
from alon_ai.db.repositories.openai_run import OpenAIRunOutcome
from alon_ai.db.repositories.records import ProductRecordsRepository
from alon_ai.integrations.live_idea import LiveIdeaRuntimeConfig
from alon_ai.integrations.live_research import (
    RESEARCH_CAPABILITIES,
    ResearchCapabilityBinding,
    ResearchRunPolicy,
)
from alon_ai.integrations.schemas.provider import Capability, StrictDTO
from alon_ai.provider_usage.live_idea import (
    CombinedModelLimits,
    build_live_combined_model_provider,
)
from alon_ai.provider_usage.live_research import GovernedLiveResearchPort
from alon_ai.provider_usage.schemas.accounting import CallState
from alon_ai.services.experiments import ExperimentContext, _id
from alon_ai.services.research import ResearchService
from alon_ai.services.run_diagnostics import record_diagnostic
from alon_ai.services.schemas.records import (
    ArtifactDraft,
    ArtifactInput,
    ArtifactKind,
    SourceReference,
)
from alon_ai.services.schemas.research import (
    AppendSourceFindingRequest,
    MarketResearchReportPayload,
    ResearchDimension,
)


def stable_config_hash(config) -> str:
    """Normalize unordered permission sets while preserving ordered policy data."""

    def normalize(value):
        if isinstance(value, (set, frozenset)):
            return sorted((normalize(item) for item in value), key=canonical_json)
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [normalize(item) for item in value]
        return to_jsonable_python(value)

    return sha256(canonical_json(normalize(config.model_dump(mode="python"))))


class CombinedIdeaConfig(StrictDTO):
    version: Literal[1]
    model: LiveIdeaRuntimeConfig
    limits: CombinedModelLimits
    research_policy: ResearchRunPolicy
    research_bindings: tuple[ResearchCapabilityBinding, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def reject_unreconciled_map(self):
        if any(
            binding.config.intended_use.capability is Capability.FIRECRAWL_MAP
            for binding in self.research_bindings
        ):
            raise ValueError(
                "FIRECRAWL_MAP is unsupported until billed usage can be reconciled"
            )
        return self


_TOPIC_DIMENSION: dict[str, ResearchDimension] = {
    "PRODUCT_WORKFLOW": "DELIVERY",
    "CUSTOMER_PROBLEM": "CUSTOMER_PAIN",
    "BUYER_AND_GEOGRAPHY": "BUYER",
    "MARKET_STRUCTURE": "COMPETITION",
    "DEMAND_AND_SPENDING": "DEMAND",
    "ALTERNATIVES": "ALTERNATIVES",
    "OBSERVED_PRICING": "PRICING",
    "DISTRIBUTION_AND_ADOPTION": "REACHABILITY",
    "DELIVERY_FEASIBILITY": "DELIVERY",
    "RISK": "DELIVERY",
}


def exact_idea_text(subject) -> str:
    key = {
        "IDEA_SEED": "statement",
        "IDEA_CANDIDATE": "hypothesis",
        "IDEA_BRIEF": "core_intent",
    }[subject["kind"]]
    return subject["payload"][key]


def return_context_text(subject, resolved) -> str:
    feedback = next(
        item for item in resolved if item["kind"] == "RESEARCH_FEEDBACK_BRIEF"
    )
    return canonical_json(
        {
            "prior_idea_brief": subject["payload"],
            "research_feedback": feedback["payload"],
        }
    )


def profile_context_text(profile, row) -> str:
    """Render every approved profile entry within its existing 200 × 1,000 bound."""
    for field in ("capabilities", "constraints"):
        entries = profile[field]
        if len(entries) > 100 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 1000
            for item in entries
        ):
            raise ExperimentError(409, "IDEA_INPUT_STALE")
    return "\n".join(
        [
            f"Profile version: {row['profile_version']}",
            f"Profile hash: {row['profile_hash']}",
            "Capabilities:",
            *profile["capabilities"],
            "Constraints:",
            *profile["constraints"],
        ]
    )


def candidate_analysis_requests(
    run_id: UUID, subject: ArtifactInput, option: ResearchedOpportunity
) -> tuple[AppendSourceFindingRequest, ...]:
    """Retain original comparison reasoning without promoting hypotheses to facts."""
    fields: list[tuple[str, str, ResearchDimension, str]] = [
        ("customer", "Customer hypothesis", "BUYER", option.customer),
        ("problem", "Problem hypothesis", "CUSTOMER_PAIN", option.problem),
        ("approach", "Proposed approach", "DELIVERY", option.approach),
        ("commercial", "Commercial reasoning", "DEMAND", option.commercial_reasoning),
        *(
            (f"alternative/{index}", f"Alternative {index + 1}", "ALTERNATIVES", value)
            for index, value in enumerate(option.alternatives)
        ),
        *(
            (f"risk/{index}", f"Risk {index + 1}", "DELIVERY", value)
            for index, value in enumerate(option.risks)
        ),
    ]
    return tuple(
        AppendSourceFindingRequest(
            run_id=run_id,
            step_key=uuid5(run_id, f"{subject.artifact_id}/analysis/{key}"),
            subject=subject,
            dimension=dimension,
            claim=label,
            finding=value,
            evidence_status="INCONCLUSIVE",
            limitations=["Agent-generated hypothesis; not an observed market fact."],
        )
        for key, label, dimension, value in fields
    )


def mapped_advice(output, *, seed_kind=None, returned=False):
    """Retain existing operator review contracts; evidence lives in linked records."""
    if isinstance(output, ResearchedCandidateSet):
        return IdeaCandidateSetAdvice(
            candidates=tuple(
                IdeaCandidateAdvice(
                    title=option.title,
                    hypothesis=option.problem,
                    demand_status="UNVERIFIED",
                    grounding_refs=("OPERATOR_PROFILE",),
                    uncertainties=option.unknowns,
                )
                for option in output.options
            )
        )
    if isinstance(output, MarketResearchAssessment) and output.status == "ASSESSED":
        model = (
            ReturnedIdeaBriefAdvice
            if returned
            else SeededIdeaBriefAdvice
            if seed_kind == ArtifactKind.IDEA_SEED
            else SelectedCandidateIdeaBriefAdvice
        )
        return model.model_validate_json(output.brief.model_dump_json())
    return None


def price_finding_requests(
    run_id: UUID,
    subject: ArtifactInput,
    index: int,
    price: PriceObservation,
    sources: tuple[SourceReference, ...],
) -> tuple[AppendSourceFindingRequest, ...]:
    """Preserve typed price facts as original analysis, without inventing an offer."""
    not_found = price.kind is PriceKind.NOT_FOUND
    if not_found:
        sources = ()
    fields = price.model_dump(mode="json", exclude={"source_refs", "subject"})
    body = canonical_json(fields)
    parts = [("observation", body)]
    # Native text fields may individually fill the record's 4,000-character bound.
    # Split long metadata into separately labeled observations rather than lose it.
    if len(body) > 4000:
        parts = [
            (
                "observation",
                canonical_json(
                    {
                        key: value
                        for key, value in fields.items()
                        if key not in {"unit", "package"}
                    }
                ),
            )
        ]
        parts.extend(
            (field, fields[field])
            for field in ("unit", "package")
            if fields[field] is not None
        )
    return tuple(
        AppendSourceFindingRequest(
            run_id=run_id,
            step_key=uuid5(run_id, f"{subject.artifact_id}/price/{index}/{part}"),
            subject=subject,
            dimension="PRICING",
            claim=price.subject,
            finding=text,
            evidence_status="INCONCLUSIVE" if not_found else "SUPPORTED",
            limitations=[
                f"Price observation {index + 1}; field: {part}; kind: {price.kind.value}.",
                "No published price was found within this run; this does not establish that no price exists."
                if not_found
                else "Observed provider pricing is not our offer price or proof of buyer willingness to pay.",
            ],
            sources=sources,
        )
        for part, text in parts
    )


class CombinedIdeaRuntime:
    def __init__(self, context, config, provisioned, port, row):
        self.context, self.config, self.provisioned, self.port, self.row = (
            context,
            config,
            provisioned,
            port,
            row,
        )
        self.native = None
        self.output_hash = None
        self.steps = AgentRunStepRepository(context.engine)
        self.runs = AgentRunRepository(context.engine)
        self.step_key = uuid5(row["run_id"], "combined-result")
        self._diagnostic_stage = "REFERENCE_RESOLUTION"

    async def discover_system(self, attribution, *, facts, idempotency_key):
        return await self._run(IdeaOperation.DISCOVER)

    async def refine_cycle(self, attribution, *, cycle_id, facts, idempotency_key):
        try:
            cycle, _ = await OpenAIIdeaInputRepository(
                self.context.engine
            ).cycle_origin(self.row["experiment_id"], cycle_id)
            command = await IntakeRepository(self.context.engine).command(
                self.row["experiment_id"], self.row["command_key"]
            )
            history = await IntakeRepository(self.context.engine).history(
                self.row["experiment_id"]
            )
            revision = next(
                (
                    item
                    for item in history
                    if item["id"] == cycle["seed_artifact_id"]
                    and item["parent_artifact_id"] is not None
                ),
                None,
            )
            refinement = (
                cycle["purpose"] == "SAME_INTENT_RETURN"
                or revision is not None
                or (command is not None and command["action"] == "REVISE")
            )
        except Exception as error:
            await record_diagnostic(
                self.runs, self.row["run_id"], "REFERENCE_RESOLUTION", error
            )
            raise
        return await self._run(
            IdeaOperation.REFINE if refinement else IdeaOperation.SELECTED_DEEPEN,
            returned=cycle["purpose"] == "SAME_INTENT_RETURN",
            revision_guidance=revision["payload"]["hypothesis"] if revision else None,
        )

    async def _research_allowance(self):
        # Refresh advisory counts before each model request. Dispatch still owns
        # atomic admission, so this snapshot never expands provider authority.
        repository = GovernanceRepository(self.context.engine)
        quotas = await repository.quota_snapshot(
            tuple(
                (
                    binding.config.intended_use.account_handle,
                    binding.config.intended_use.capability,
                )
                for binding in self.config.research_bindings
            )
        )
        policy = self.config.research_policy
        rows = await self.steps.list(self.row["run_id"])
        kinds = {capability.value for capability in RESEARCH_CAPABILITIES} | {
            "BRAVE_SEARCH"
        }
        research = [row for row in rows if row["kind"] in kinds]
        discovery_used = sum(
            row["kind"] in {"BRAVE_SEARCH", "FIRECRAWL_MAP"} for row in research
        )
        pages_used = sum(
            policy.max_pdf_pages
            if row["kind"] == "FIRECRAWL_PDF_CAPTURE"
            else 1
            if row["kind"] in {"FIRECRAWL_PAGE_CAPTURE", "FIRECRAWL_JS_RETRIEVAL"}
            else 0
            for row in research
        )
        remaining = max(0, policy.max_calls - len(research))
        return {
            "run_limits": {
                "max_calls": policy.max_calls,
                "max_pages": policy.max_pages,
                "max_results": policy.max_results,
                "max_spend_usd": str(policy.max_spend_usd),
                "timeout_seconds": policy.timeout_seconds,
            },
            "run_usage": {
                "calls_used": len(research),
                "calls_remaining": remaining,
                "pages_used": pages_used,
                "pages_remaining": max(0, policy.max_pages - pages_used),
                "discovery_calls_remaining": min(
                    remaining, max(0, policy.max_calls // 2 - discovery_used)
                ),
            },
            "provider_quotas": quotas,
        }

    async def _research_instructions(self, _context):
        limits = await self._research_allowance()
        return (
            "Approved research limits and current provider quota: "
            + canonical_json(limits)
            + "\nUse a few high-yield searches; reserve calls for page captures and "
            "evidence inspection. These counts are upper bounds, not targets. "
            "Do not request more provider calls than the remaining allowance. "
            "Discovery is limited to half the research calls to preserve capture capacity. "
            "Search URLs are discovery hints, not evidence: capture promising sources and "
            "read their retained evidence before searching again. A NOT_DISPATCHED result "
            "provides no evidence and consumes no provider call; follow its guidance. "
            "When provider quota or calls are zero, stop that capability and synthesize "
            "from retained evidence in the required native result shape with named gaps. "
            "Finish with a truthful assessment or named gaps before limits are exhausted."
        )

    async def _scheduled_research(self, capability, method, *args, **kwargs):
        # This local scheduling stop is not an admission decision. Governed
        # errors still propagate; dispatch retains atomic quota/rights checks.
        snapshot = await self._research_allowance()
        usage = snapshot["run_usage"]
        quota = min(
            (
                item["remaining_calls"]
                for item in snapshot["provider_quotas"]
                if item["capability"] == capability.value
            ),
            default=0,
        )
        discovery = capability in {
            Capability.BRAVE_WEB_COVERAGE,
            Capability.FIRECRAWL_MAP,
        }
        pages = (
            self.config.research_policy.max_pdf_pages
            if capability is Capability.FIRECRAWL_PDF_CAPTURE
            else 1
        )
        if (
            not quota
            or not usage["calls_remaining"]
            or discovery
            and not usage["discovery_calls_remaining"]
            or not discovery
            and pages > usage["pages_remaining"]
        ):
            return {
                "status": "NOT_DISPATCHED",
                "capability": capability.value,
                "remaining": usage,
                "provider_calls_remaining": quota,
                "guidance": "Use an available capture capability on discovered URLs, then read retained evidence. "
                "If captures are unavailable, synthesize the required native result with named gaps; do not claim unsupported findings. "
                "Do not retry an exhausted capability; this result is not evidence.",
            }
        return await method(*args, **kwargs)

    def _research_toolset(self, tools):
        capabilities = {
            binding.config.intended_use.capability
            for binding in self.config.research_bindings
        }

        async def search_web(query: str, *, limit: int | None = None):
            """Discover URLs within the remaining search allocation; then capture sources."""
            return await self._scheduled_research(
                Capability.BRAVE_WEB_COVERAGE, tools.search_web, query, limit=limit
            )

        async def map_site(url: str, *, limit: int | None = None):
            return await self._scheduled_research(
                Capability.FIRECRAWL_MAP, tools.map_site, url, limit=limit
            )

        async def capture_page(url: str):
            """Capture a discovered page within remaining calls, pages and provider quota."""
            return await self._scheduled_research(
                Capability.FIRECRAWL_PAGE_CAPTURE, tools.capture_page, url
            )

        async def capture_pdf(url: str):
            return await self._scheduled_research(
                Capability.FIRECRAWL_PDF_CAPTURE, tools.capture_pdf, url
            )

        exposed: list[Any] = [tools.read_saved_evidence]
        for capability, method in (
            (Capability.BRAVE_WEB_COVERAGE, search_web),
            (Capability.FIRECRAWL_MAP, map_site),
            (Capability.FIRECRAWL_PAGE_CAPTURE, capture_page),
            (Capability.FIRECRAWL_PDF_CAPTURE, capture_pdf),
        ):
            if capability in capabilities:
                exposed.append(method)
        # A model may return several calls together; governed research admits
        # one call at a time under the approved provider concurrency limits.
        return FunctionToolset(
            tools=exposed, sequential=True, instructions=self._research_instructions
        )

    async def _run(self, operation, *, returned=False, revision_guidance=None):
        self._diagnostic_stage = "REFERENCE_RESOLUTION"
        try:
            return await self._run_inner(
                operation, returned=returned, revision_guidance=revision_guidance
            )
        except Exception as error:
            await record_diagnostic(
                self.runs, self.row["run_id"], self._diagnostic_stage, error
            )
            raise

    async def _run_inner(self, operation, *, returned=False, revision_guidance=None):
        row, context = self.row, self.context
        store = AgentRunRepository(context.engine)
        profile = await store.profile_projection(row)
        if profile is None:
            raise ExperimentError(409, "IDEA_INPUT_STALE")
        resolved = []
        for ref in row["input_refs"]:
            artifact = await store.artifact(row["experiment_id"], ref)
            if artifact is None:
                raise ExperimentError(409, "IDEA_INPUT_STALE")
            resolved.append(artifact)
        subject = next(
            (
                item
                for item in resolved
                if item["kind"] in {"IDEA_SEED", "IDEA_CANDIDATE", "IDEA_BRIEF"}
            ),
            None,
        )
        brief = next(
            (item for item in resolved if item["kind"] == "EXPERIMENT_BRIEF"), None
        )
        command = await IntakeRepository(context.engine).command(
            row["experiment_id"], row["command_key"]
        )
        payload = command["payload"] if command else {}
        input = IdeaAgentInput(
            operation=operation,
            operator_profile_ref=row["profile_id"],
            profile_context=profile_context_text(profile, row),
            approved_limits_ref=self.provisioned.attribution.config_version,
            idea_version_ref=subject["id"] if subject else None,
            idea_text=exact_idea_text(subject) if subject else None,
            prior_research_summary=return_context_text(subject, resolved)
            if returned
            else None,
            revision_guidance=(
                revision_guidance
                or payload.get("idea_seed")
                or subject["payload"].get("statement")
            )
            if operation is IdeaOperation.REFINE and subject
            else None,
            generation_guidance=(
                payload.get("generation_guidance")
                or brief["payload"].get("guidance")
                or None
            )
            if brief and operation is IdeaOperation.DISCOVER
            else None,
        )
        checkpoint = await self.steps.claim(
            run_id=row["run_id"],
            experiment_id=row["experiment_id"],
            step_key=self.step_key,
            ordinal=1_000_000,
            kind="ARTIFACT_SAVE",
            request_ref=row["run_id"],
            request_version=1,
            request_hash=sha256(input.model_dump_json()),
            config_ref=self.provisioned.attribution.config_version,
            config_version=1,
            config_hash=stable_config_hash(self.config),
        )
        if checkpoint["status"] != "CLAIMED":
            raise ExperimentError(409, "COMBINED_RESULT_REPLAY_UNAVAILABLE")
        await self.steps.bind(
            row["run_id"],
            self.step_key,
            operation_id=self.provisioned.attribution.operation_run_id,
            operation_workflow_id=self.provisioned.attribution.workflow_run_id,
        )
        tools = ResearchTools(
            row["experiment_id"],
            self.port,
            max_results=self.config.research_policy.max_results,
        )
        toolset = self._research_toolset(tools)
        try:
            self._diagnostic_stage = "AGENT_EXECUTION"
            async with asyncio.timeout(self.provisioned.run_timeout_seconds):
                result = await run_idea_agent(
                    input,
                    model=self.provisioned.model,
                    toolset=toolset,
                    usage_limits=self.provisioned.usage_limits,
                )
            self.native = result.output
            all_refs = (
                {ref for option in self.native.options for ref in option.source_refs}
                if isinstance(
                    self.native, (ResearchedCandidateSet, IncompleteDiscovery)
                )
                else set(self.native.source_refs)
            )
            self._diagnostic_stage = "REFERENCE_RESOLUTION"
            await self.port.resolve_references(tuple(sorted(all_refs)))
            receipts = self.provisioned.model.receipts
            if not receipts or any(
                receipt.state != CallState.FINAL for receipt in receipts
            ):
                raise ExperimentError(409, "COMBINED_USAGE_UNRESOLVED")
            self._diagnostic_stage = "ADVICE_MAPPING"
            output = mapped_advice(
                self.native,
                seed_kind=subject["kind"] if subject else None,
                returned=returned,
            )
            self.output_hash = (
                sha256(canonical_json(output.model_dump(mode="json")))
                if output
                else None
            )
            self._diagnostic_stage = "PUBLICATION"
            await self._publish(subject)
            await self.steps.finish(
                row["run_id"],
                self.step_key,
                status="SUCCEEDED" if output is not None else "BLOCKED",
                reason_code=None if output is not None else "RESEARCH_INCOMPLETE",
                output_hash=self.output_hash,
            )
            if output is None:
                raise ExperimentError(409, "RESEARCH_INCOMPLETE")
            return OpenAIExecution(
                Route.CHEAP, OpenAIRunOutcome.SUCCEEDED, receipts[-1], output
            )
        except BaseException:
            checkpoint = await self.steps.get(row["run_id"], self.step_key)
            if checkpoint["status"] == "CLAIMED":
                await asyncio.shield(
                    self.steps.finish(
                        row["run_id"],
                        self.step_key,
                        status="OUTCOME_UNKNOWN",
                        reason_code="COMBINED_RECONCILIATION_REQUIRED",
                    )
                )
            raise

    async def _publish(self, subject):
        assert self.native is not None
        row, context = self.row, self.context
        records = ProductRecordsRepository(context.engine)
        if isinstance(self.native, (ResearchedCandidateSet, IncompleteDiscovery)):
            subjects = []
            for index, option in enumerate(self.native.options):
                candidate_id = _id(row["run_id"], f"candidate-{index}")
                receipt = await records.append_artifact(
                    ArtifactDraft(
                        id=candidate_id,
                        logical_id=candidate_id,
                        version=1,
                        experiment_id=row["experiment_id"],
                        workflow_id=self.provisioned.attribution.workflow_run_id,
                        agent_id=self.provisioned.attribution.actor.agent_run_id,
                        operation_id=self.provisioned.attribution.operation_run_id,
                        kind=ArtifactKind.IDEA_CANDIDATE,
                        payload={
                            "title": option.title,
                            "hypothesis": option.problem,
                        },
                        created_by=context.operator_id,
                        created_at=row["created_at"],
                    ),
                    command_key=_id(row["run_id"], f"candidate-command-{index}"),
                )
                subjects.append(
                    (
                        ArtifactInput.from_receipt(receipt, role="RESEARCH_SUBJECT"),
                        option.findings,
                    )
                )
        else:
            subjects = [
                (
                    ArtifactInput(
                        artifact_id=subject["id"],
                        kind=ArtifactKind(subject["kind"]),
                        version=subject["version"],
                        content_hash=subject["content_hash"],
                        role="RESEARCH_SUBJECT",
                    ),
                    self.native.findings,
                )
            ]
        summary_id = uuid5(row["run_id"], "combined-case")
        gaps = (
            list(self.native.gaps)
            if isinstance(self.native, (IncompleteDiscovery, MarketResearchAssessment))
            else list(
                dict.fromkeys(
                    gap for option in self.native.options for gap in option.unknowns
                )
            )
        )
        summary = MarketResearchReportPayload(
            finding=(
                f"{self.native.status}: "
                + (
                    self.native.recommendation.value
                    if isinstance(self.native, MarketResearchAssessment)
                    else f"{len(self.native.options)} researched options"
                )
            ),
            limitations=[
                "Advisory research requires operator review; demand and commercial viability are not guaranteed.",
                *(
                    [
                        "Model-reported coverage (does not certify sufficiency): "
                        + ", ".join(topic.value for topic in self.native.coverage)
                    ]
                    if isinstance(self.native, MarketResearchAssessment)
                    else []
                ),
            ],
            unresolved_questions=gaps,
        )
        await records.append_artifact(
            ArtifactDraft(
                id=summary_id,
                logical_id=summary_id,
                version=1,
                experiment_id=row["experiment_id"],
                workflow_id=self.provisioned.attribution.workflow_run_id,
                agent_id=self.provisioned.attribution.actor.agent_run_id,
                operation_id=self.provisioned.attribution.operation_run_id,
                kind=ArtifactKind.MARKET_RESEARCH_REPORT,
                payload=summary.model_dump(mode="json"),
                created_by=context.operator_id,
                created_at=row["created_at"],
            ),
            inputs=tuple(
                ArtifactInput(
                    artifact_id=UUID(ref["artifact_id"]),
                    kind=ArtifactKind(ref["kind"]),
                    version=ref["version"],
                    content_hash=ref["content_hash"],
                    role=ref["role"],
                )
                for ref in row["input_refs"]
            ),
            command_key=uuid5(summary_id, "save"),
        )
        research = ResearchService(context)
        for subject_index, (subject_ref, findings) in enumerate(subjects):
            if isinstance(self.native, (ResearchedCandidateSet, IncompleteDiscovery)):
                for request in candidate_analysis_requests(
                    row["run_id"], subject_ref, self.native.options[subject_index]
                ):
                    await research.append_finding(row["experiment_id"], request)
            for index, finding in enumerate(findings):
                if (
                    finding.idea_version_ref is not None
                    and finding.idea_version_ref != subject_ref.artifact_id
                ):
                    raise ExperimentError(409, "RESEARCH_SUBJECT_NOT_BOUND")
                refs = await self.port.resolve_references(finding.source_refs)
                await research.append_finding(
                    row["experiment_id"],
                    AppendSourceFindingRequest(
                        run_id=row["run_id"],
                        step_key=uuid5(
                            row["run_id"], f"{subject_ref.artifact_id}/finding/{index}"
                        ),
                        subject=subject_ref,
                        dimension=_TOPIC_DIMENSION[finding.topic.value],
                        claim=finding.claim,
                        finding=finding.claim,
                        evidence_status="SUPPORTED"
                        if finding.basis is ResearchBasis.OBSERVED
                        else "INCONCLUSIVE",
                        limitations=[
                            *finding.limitations,
                            f"Model-reported basis: {finding.basis.value}; confidence: {finding.confidence.value}.",
                        ],
                        sources=refs,
                    ),
                )
            if isinstance(self.native, MarketResearchAssessment):
                firecrawl_grants = {
                    (binding.grant.grant_id, binding.grant.version)
                    for binding in self.config.research_bindings
                    if binding.config.intended_use.provider.value == "FIRECRAWL"
                }
                for index, price in enumerate(self.native.price_observations):
                    refs = (
                        ()
                        if price.kind is PriceKind.NOT_FOUND
                        else await self.port.resolve_references(price.source_refs)
                    )
                    if any(
                        ref.field != "TEXT"
                        or (ref.grant_id, ref.grant_version) not in firecrawl_grants
                        for ref in refs
                    ):
                        raise ExperimentError(409, "PRICE_SOURCE_NOT_BOUND")
                    for request in price_finding_requests(
                        row["run_id"], subject_ref, index, price, refs
                    ):
                        await research.append_finding(row["experiment_id"], request)
                for index, contradiction in enumerate(self.native.contradictions):
                    await research.append_finding(
                        row["experiment_id"],
                        AppendSourceFindingRequest(
                            run_id=row["run_id"],
                            step_key=uuid5(
                                row["run_id"],
                                f"{subject_ref.artifact_id}/contradiction/{index}",
                            ),
                            subject=subject_ref,
                            dimension="DELIVERY",
                            claim="Model-reported contradiction requiring review",
                            finding=contradiction,
                            evidence_status="INCONCLUSIVE",
                            limitations=[
                                "The assessment supplied no source mapping for this contradiction; it is not independently verified."
                            ],
                        ),
                    )
            report_id = uuid5(row["run_id"], f"{subject_ref.artifact_id}/case")
            gaps = (
                list(self.native.gaps)
                if isinstance(
                    self.native, (MarketResearchAssessment, IncompleteDiscovery)
                )
                else list(
                    next(
                        option.unknowns
                        for option in self.native.options
                        if option.findings == findings
                    )
                )
            )
            payload = MarketResearchReportPayload(
                finding=(
                    f"{self.native.status}: "
                    + (
                        self.native.recommendation.value + ". "
                        if isinstance(self.native, MarketResearchAssessment)
                        else ""
                    )
                    + " ".join(f.claim for f in findings)
                )[:4000],
                limitations=[
                    "Advisory research does not authorize acceptance or commercial action.",
                    *(
                        [
                            "Model-reported coverage (does not certify sufficiency): "
                            + ", ".join(topic.value for topic in self.native.coverage)
                        ]
                        if isinstance(self.native, MarketResearchAssessment)
                        else []
                    ),
                ],
                unresolved_questions=gaps,
            )
            await records.append_artifact(
                ArtifactDraft(
                    id=report_id,
                    logical_id=report_id,
                    version=1,
                    experiment_id=row["experiment_id"],
                    kind=ArtifactKind.MARKET_RESEARCH_REPORT,
                    payload=payload.model_dump(mode="json"),
                    created_by=context.operator_id,
                    created_at=row["created_at"],
                ),
                inputs=(subject_ref,),
                command_key=uuid5(report_id, "save"),
            )


def build_combined_idea_provider(config, secrets, settings):
    model_provider = build_live_combined_model_provider(
        config.model, secrets.for_consumer("openai-idea"), limits=config.limits
    )

    async def provision(engine, **arguments):
        store = AgentRunRepository(engine)
        row = await store.owned(arguments["run_id"], arguments["operator_id"])
        scopes = (
            (config.model.intended_use.account_handle, Capability.OPENAI_GENERATE),
            *(
                (
                    binding.config.intended_use.account_handle,
                    binding.config.intended_use.capability,
                )
                for binding in config.research_bindings
            ),
        )
        quotas = await GovernanceRepository(engine).quota_snapshot(scopes)
        # Starting fresh research requires a model request to choose tools and
        # another to synthesize their results. This snapshot is advisory;
        # every actual dispatch still rechecks admission atomically.
        if config.limits.model_request_limit < 2:
            raise ExperimentError(409, "MODEL_REQUEST_LIMIT_TOO_LOW")
        if quotas[0]["remaining_calls"] < 2:
            raise ExperimentError(409, "MODEL_ALLOWANCE_EXHAUSTED")
        # A known public URL can be captured directly. Exhausted search or an
        # optional capture route must not block an available capture tool.
        if not any(
            capability
            in {Capability.FIRECRAWL_PAGE_CAPTURE, Capability.FIRECRAWL_PDF_CAPTURE}
            and quota["remaining_calls"] >= 1
            for (_, capability), quota in zip(scopes[1:], quotas[1:], strict=True)
        ):
            raise ExperimentError(409, "CAPTURE_ALLOWANCE_EXHAUSTED")
        port = None

        @asynccontextmanager
        async def guard():
            if port is None:
                raise PermissionError("research scope missing")
            async with port.dispatch_guard():
                for ref in row["input_refs"]:
                    if await store.artifact(row["experiment_id"], ref) is None:
                        raise PermissionError("pinned input unavailable")
                profile = await OpenAIIdeaInputRepository(engine).operator_profile(
                    row["experiment_id"]
                )
                if (profile.profile_id, profile.version, profile.content_hash) != (
                    row["profile_id"],
                    row["profile_version"],
                    row["profile_hash"],
                ):
                    raise PermissionError("pinned profile changed")
                yield

        provisioned = await model_provider(engine, **arguments, dispatch_guard=guard)
        bindings = await provision_research_bindings(
            engine,
            config,
            provisioned.attribution,
            arguments["budget_usd"],
            row["started_at"],
        )
        port = GovernedLiveResearchPort(
            GovernanceRepository(engine),
            secrets.research_store(),
            run_id=row["run_id"],
            operator_id=row["operator_id"],
            attribution=provisioned.attribution,
            policy=config.research_policy,
            bindings=bindings,
        )
        context = ExperimentContext(engine, settings, row["operator_id"])
        return (
            CombinedIdeaRuntime(context, config, provisioned, port, row),
            provisioned.attribution,
            "OPENAI",
        )

    cast(Any, provision).config_fingerprint = stable_config_hash(config)
    return provision


async def provision_research_bindings(
    engine, config, attribution, budget_usd, admitted_at
):
    """Materialize approved templates within this exact immutable operation scope."""
    provisioner = GovernanceProvisioner(engine)
    bindings = {}
    now = datetime.now(UTC)
    expiry = min(config.model.expires_at, config.research_policy.expires_at)
    if config.model.approved_by != config.research_policy.approved_by or not (
        config.research_policy.effective_at <= now < expiry
    ):
        raise ExperimentError(409, "RESEARCH_CONFIG_INVALID")
    for template in config.research_bindings:
        capability = template.config.intended_use.capability
        if capability in bindings:
            raise ExperimentError(409, "RESEARCH_CONFIG_INVALID")
        exact = template.config.model_copy(
            update={
                "id": uuid5(attribution.operation_run_id, f"{capability}/config"),
                "version": attribution.config_version,
                "workflow_id": attribution.workflow_run_id,
                "adapter_version": uuid5(
                    attribution.operation_run_id, f"{capability}/adapter"
                ),
            }
        )
        await _ensure_exact_config(engine, exact)
        bindings[capability] = template.model_copy(update={"config": exact})
        for currency, limit in (
            ("USD", budget_usd),
            ("ILS", budget_usd * config.model.fx_rate),
        ):
            await provisioner.budgets(
                attribution,
                provider=exact.intended_use.provider,
                currencies=(currency,),
                limit=limit,
                effective_at=admitted_at,
                expires_at=expiry,
            )
    return bindings
