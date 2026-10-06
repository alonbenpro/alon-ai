"""Persisted research projections use exact subjects and never invent evidence."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_product_records import artifact, roots

from alon_ai.config import Settings
from alon_ai.db.repositories.agent_runs import AgentRunRepository
from alon_ai.db.repositories.experiments import ExperimentError
from alon_ai.db.tables import records
from alon_ai.services.experiments import ExperimentContext
from alon_ai.services.research import ResearchService
from alon_ai.services.schemas.records import ArtifactInput, ArtifactKind
from alon_ai.services.schemas.research import AppendSourceFindingRequest

pytestmark = pytest.mark.integration


async def setup_case(engine):
    repo, profile, experiment, _workflow, _agent = await roots(engine)
    draft = artifact(
        experiment,
        ArtifactKind.IDEA_SEED,
        {
            "origin": "USER_SUPPLIED",
            "statement": "Administrative service hypothesis",
        },
    )
    seed = await repo.append_artifact(draft, command_key=uuid4())
    ref = ArtifactInput.from_receipt(seed, role="SEED")
    run_id = uuid4()
    await AgentRunRepository(engine).admit(
        {
            "run_id": run_id,
            "command_key": uuid4(),
            "experiment_id": experiment,
            "operator_id": profile.operator_id,
            "task_kind": "IDEA_REFINEMENT",
            "request_hash": "a" * 64,
            "input_refs": [ref.model_dump(mode="json")],
            "profile_id": profile.id,
            "profile_version": 1,
            "profile_hash": "b" * 64,
            "provider_mode": "fake",
            "dbos_workflow_id": f"idea-{run_id}",
            "application_version": "test",
        }
    )
    await AgentRunRepository(engine).start(run_id)
    context = ExperimentContext(engine, Settings(_env_file=None), profile.operator_id)
    return ResearchService(context), repo, experiment, ref, run_id


def finding(subject, run_id, **updates):
    return AppendSourceFindingRequest(
        subject=subject,
        run_id=run_id,
        step_key=UUID(int=312),
        dimension="CUSTOMER_PAIN",
        claim="Pain remains a hypothesis.",
        finding="Available evidence is insufficient.",
        evidence_status="INCONCLUSIVE",
        limitations=["No retained source supports the hypothesis."],
        **updates,
    )


async def test_read_only_empty_case_has_gaps_and_no_invented_findings(
    governance_engine,
):
    service, _, experiment, _, _ = await setup_case(governance_engine)
    async with governance_engine.connect() as conn:
        before = await conn.scalar(select(func.count()).select_from(records.artifacts))
    case = await service.get_case(experiment)
    assert case.progress == "NOT_STARTED"
    assert case.finding_count == 0
    assert case.subjects[0].mode == "SUPPLIED"
    assert case.subjects[0].findings == []
    assert "DEMAND" in case.subjects[0].gaps
    async with governance_engine.connect() as conn:
        assert (
            await conn.scalar(select(func.count()).select_from(records.artifacts))
            == before
        )


async def test_incremental_finding_replays_exactly_and_remains_version_bound(
    governance_engine,
):
    service, repo, experiment, subject, run_id = await setup_case(governance_engine)
    request = finding(subject, run_id)
    saved = await service.append_finding(experiment, request)
    assert await service.append_finding(experiment, request) == saved
    case = await service.get_case(experiment)
    assert case.progress == "PARTIAL"
    assert case.finding_count == 1
    assert case.subjects[0].findings[0].observation.evidence_status == "INCONCLUSIVE"
    assert "CUSTOMER_PAIN" in case.subjects[0].gaps
    async with governance_engine.connect() as conn:
        original = (
            (
                await conn.execute(
                    select(records.artifacts).where(
                        records.artifacts.c.id == subject.artifact_id,
                    )
                )
            )
            .mappings()
            .one()
        )
    await repo.append_artifact(
        artifact(
            experiment,
            ArtifactKind.IDEA_SEED,
            {
                "origin": "USER_SUPPLIED",
                "statement": "Revised hypothesis",
            },
            logical_id=original["logical_id"],
            version=2,
        ),
        inputs=(subject.model_copy(update={"role": "SUPERSEDES"}),),
        command_key=uuid4(),
    )
    refreshed = await service.get_case(experiment)
    prior = next(
        s for s in refreshed.subjects if s.subject.artifact_id == subject.artifact_id
    )
    assert not prior.current
    assert prior.findings[0].artifact.artifact_id == saved.artifact.artifact_id
    assert next(s for s in refreshed.subjects if s.current).findings == []


async def test_finding_rejects_other_subject_other_operator_and_cancelled_run(
    governance_engine,
):
    service, repo, experiment, subject, run_id = await setup_case(governance_engine)
    unbound = await repo.append_artifact(
        artifact(
            experiment,
            ArtifactKind.IDEA_CANDIDATE,
            {
                "title": "Unrelated candidate",
                "hypothesis": "Not a run input",
            },
        ),
        command_key=uuid4(),
    )
    with pytest.raises(ExperimentError, match="RESEARCH_SUBJECT_NOT_BOUND"):
        await service.append_finding(
            experiment,
            finding(ArtifactInput.from_receipt(unbound, role="CANDIDATE"), run_id),
        )
    other = ResearchService(
        ExperimentContext(governance_engine, Settings(_env_file=None), uuid4())
    )
    with pytest.raises(ExperimentError, match="EXPERIMENT_NOT_FOUND"):
        await other.get_case(experiment)
    await AgentRunRepository(governance_engine).cancel(run_id, UUID(int=1), uuid4())
    with pytest.raises(ExperimentError, match="RESEARCH_RUN_NOT_ACTIVE"):
        await service.append_finding(experiment, finding(subject, run_id))
    assert (await service.get_case(experiment)).finding_count == 0


async def test_conflicting_replay_cannot_replace_saved_finding(governance_engine):
    service, _, experiment, subject, run_id = await setup_case(governance_engine)
    request = finding(subject, run_id)
    await service.append_finding(experiment, request)
    with pytest.raises(ExperimentError, match="COMMAND_CONFLICT"):
        await service.append_finding(
            experiment, request.model_copy(update={"finding": "Changed result"})
        )
    assert (await service.get_case(experiment)).subjects[0].findings[
        0
    ].observation.finding == "Available evidence is insufficient."


async def test_saved_finding_replays_after_run_completion(governance_engine):
    service, _, experiment, subject, run_id = await setup_case(governance_engine)
    request = finding(subject, run_id)
    saved = await service.append_finding(experiment, request)
    await AgentRunRepository(governance_engine).finish(run_id, "SUCCEEDED")
    assert await service.append_finding(experiment, request) == saved


async def test_candidate_selection_preserves_separate_case_identities(
    governance_engine,
):
    repo, profile, experiment, workflow, agent = await roots(governance_engine)
    candidates = []
    for title in ("First candidate", "Second candidate"):
        candidates.append(
            await repo.append_artifact(
                artifact(
                    experiment,
                    ArtifactKind.IDEA_CANDIDATE,
                    {"title": title, "hypothesis": "An unverified hypothesis"},
                    workflow_id=workflow,
                    agent_id=agent,
                ),
                command_key=uuid4(),
            )
        )
    service = ResearchService(
        ExperimentContext(
            governance_engine, Settings(_env_file=None), profile.operator_id
        )
    )
    initial = await service.get_case(experiment)
    assert [subject.mode for subject in initial.subjects] == ["CANDIDATE", "CANDIDATE"]
    await repo.select_idea_candidate(
        experiment,
        ArtifactInput.from_receipt(candidates[0], role="CANDIDATE"),
        selected_by=profile.operator_id,
        reason="Operator chose a research direction",
        command_key=uuid4(),
    )
    selected = await service.get_case(experiment)
    assert {s.subject.artifact_id: s.mode for s in selected.subjects} == {
        candidates[0].artifact_id: "SELECTED",
        candidates[1].artifact_id: "CANDIDATE",
    }
    assert selected.finding_count == 0
    assert all(len(s.gaps) == 8 for s in selected.subjects)


async def test_safe_reference_projection_never_claims_source_content_is_licensed(
    governance_engine,
):
    from datetime import UTC, datetime

    from alon_ai.db.repositories.accounting import GovernanceProvisioner
    from alon_ai.provider_usage.schemas.accounting import EvidenceRecord
    from alon_ai.services.schemas.records import SourceReference

    service, _, experiment, subject, run_id = await setup_case(governance_engine)
    proof = uuid4()
    await GovernanceProvisioner(governance_engine).evidence(
        EvidenceRecord(
            id=proof,
            kind="CONTROL",
            mode="SYNTHETIC",
            registered_by=UUID(int=1),
            registered_at=datetime.now(UTC),
        )
    )
    saved = await service.append_finding(
        experiment,
        finding(
            subject,
            run_id,
            sources=(SourceReference.governance_evidence(proof),),
        ),
    )
    assert saved.sources[0].reference.evidence_id == proof
    assert saved.sources[0].availability == "REFERENCE_ONLY"
    assert saved.sources[0].url is None and saved.sources[0].title is None
    assert saved.sources[0].provider is None


async def retained_capture(
    engine, *, capability=None, fields=None, url="https://example.com/research"
):
    """Synthetic governed retention only; no transport or remote provider is invoked."""
    from test_governance import register, reserve, seed

    from alon_ai.db.tables import accounting as gov
    from alon_ai.integrations.schemas.provider import Capability, ContentField
    from alon_ai.policies.provider_rights import RuntimeContent
    from alon_ai.services.schemas.records import SourceReference

    capability = capability or Capability.FIRECRAWL_PAGE_CAPTURE
    fields = fields or frozenset(
        {ContentField.URL, ContentField.TITLE, ContentField.TEXT}
    )
    governance, admin, attr, config, old_grant, now = await seed(
        engine, capability=capability
    )
    use = config.intended_use.model_copy(update={"required_fields": fields})
    grant = old_grant.model_copy(
        update={
            "grant_id": uuid4(),
            "storage_fields": fields,
            "supersedes_id": old_grant.grant_id,
            "supporting_evidence_ref": uuid4(),
        }
    )
    await register(admin, grant.supporting_evidence_ref, "GRANT", now)
    await admin.grant(grant)
    config = config.model_copy(update={"id": uuid4(), "intended_use": use})
    await admin.config(config)
    call = await reserve(governance, attr, config)
    await governance.dispatch(call.call_id)
    await governance.retain_content(
        call.call_id,
        RuntimeContent(
            {
                ContentField.URL: (url,),
                ContentField.TITLE: ("Original page title",),
                ContentField.TEXT: ("PRIVATE BODY MUST NOT APPEAR",),
            },
            grant=grant,
            intended_use=use,
            observed_at=now,
        ),
    )
    async with engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(gov.retained).where(
                        gov.retained.c.call_id == call.call_id,
                        gov.retained.c.field == "TEXT",
                    )
                )
            )
            .mappings()
            .one()
        )
    ref = SourceReference.retained_content(
        retained_id=row["id"],
        call_id=call.call_id,
        grant_id=grant.grant_id,
        grant_version=grant.version,
        field="TEXT",
        expires_at=row["expires_at"],
    )
    return attr, ref, admin, grant, now


async def test_firecrawl_source_link_is_current_licensed_and_revocation_removes_it(
    governance_engine,
    monkeypatch,
):
    from test_governance import add_event

    from alon_ai.db.repositories.idea_research import IdeaResearchRepository
    from alon_ai.policies.provider_rights import GrantEvent, GrantEventKind

    attr, reference, admin, grant, now = await retained_capture(governance_engine)
    repository = IdeaResearchRepository(governance_engine, clock=lambda: now)
    import socket

    import httpx
    from sqlalchemy import event

    original_lookup = socket.getaddrinfo

    def local_database_lookup(host, *args, **kwargs):
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise AssertionError("Source projection must not resolve remote hosts")
        return original_lookup(host, *args, **kwargs)

    def no_http_client(*args, **kwargs):
        raise AssertionError("Source projection must not create a network client")

    monkeypatch.setattr(socket, "getaddrinfo", local_database_lookup)
    monkeypatch.setattr(httpx, "AsyncClient", no_http_client)
    statements = []

    def record_sql(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(governance_engine.sync_engine, "before_cursor_execute", record_sql)
    try:
        view = await repository.source_view(attr.experiment_id, reference)
    finally:
        event.remove(governance_engine.sync_engine, "before_cursor_execute", record_sql)
    assert statements and all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    assert view.availability == "CURRENT_SOURCE"
    assert view.provider == "FIRECRAWL"
    assert view.url == "https://example.com/research"
    assert view.title == "Original page title"
    assert view.available_until == reference.expires_at
    assert "PRIVATE BODY" not in view.model_dump_json()
    await add_event(
        admin,
        GrantEvent(
            event_id=uuid4(),
            grant_id=grant.grant_id,
            grant_version=grant.version,
            kind=GrantEventKind.REVOKED,
            effective_at=now,
            actor_id=uuid4(),
            evidence_ref=uuid4(),
        ),
    )
    revoked = await repository.source_view(attr.experiment_id, reference)
    assert revoked.availability == "REFERENCE_ONLY"
    assert revoked.url is None and revoked.title is None


@pytest.mark.parametrize(
    "reason",
    [
        "expired",
        "wrong_experiment",
        "forged_ref",
        "brave",
        "unsafe_url",
        "text_only",
        "disabled",
        "superseded",
    ],
)
async def test_unlicensed_or_unsafe_source_never_produces_link(
    governance_engine, reason
):
    from datetime import timedelta

    from sqlalchemy import update

    from alon_ai.db.repositories.idea_research import IdeaResearchRepository
    from alon_ai.db.tables import accounting as gov
    from alon_ai.integrations.schemas.provider import Capability, ContentField

    attr, reference, admin, grant, now = await retained_capture(
        governance_engine,
        capability=Capability.BRAVE_WEB_COVERAGE if reason == "brave" else None,
        fields=frozenset({ContentField.TEXT}) if reason == "text_only" else None,
        url="https://127.0.0.1/secret"
        if reason == "unsafe_url"
        else "https://example.com/research",
    )
    if reason == "superseded":
        await admin.grant(
            grant.model_copy(
                update={"grant_id": uuid4(), "supersedes_id": grant.grant_id}
            )
        )
    if reason == "disabled":
        async with governance_engine.begin() as connection:
            await connection.execute(update(gov.authorities).values(enabled=False))
    repository = IdeaResearchRepository(
        governance_engine,
        clock=lambda: now + timedelta(seconds=61) if reason == "expired" else now,
    )
    view = await repository.source_view(
        uuid4() if reason == "wrong_experiment" else attr.experiment_id,
        reference.model_copy(update={"retained_id": uuid4()})
        if reason == "forged_ref"
        else reference,
    )
    assert view.availability == "REFERENCE_ONLY"
    assert view.url is None and view.title is None and view.available_until is None


async def test_licensed_url_without_title_still_identifies_original_source(
    governance_engine,
):
    from alon_ai.db.repositories.idea_research import IdeaResearchRepository
    from alon_ai.integrations.schemas.provider import ContentField

    attr, reference, _, _, now = await retained_capture(
        governance_engine,
        fields=frozenset({ContentField.URL, ContentField.TEXT}),
    )
    view = await IdeaResearchRepository(
        governance_engine, clock=lambda: now
    ).source_view(attr.experiment_id, reference)
    assert view.url == "https://example.com/research"
    assert view.availability == "CURRENT_SOURCE" and view.provider == "FIRECRAWL"
    assert view.title is None


async def test_case_get_exposes_original_source_without_storing_it_in_artifact(
    governance_engine,
):
    from sqlalchemy import insert

    from alon_ai.db.repositories.idea_research import IdeaResearchRepository
    from alon_ai.db.tables import accounting as gov
    from alon_ai.services.schemas.records import (
        ProductAgent,
        ProductExperiment,
        ProductWorkflow,
    )

    attr, reference, _, _, now = await retained_capture(governance_engine)
    repo, profile, _, _, _ = await roots(governance_engine)
    agent_id = uuid4()
    async with governance_engine.begin() as connection:
        await connection.execute(
            insert(gov.agents).values(id=agent_id, workflow_id=attr.workflow_run_id)
        )
    await repo.bind_roots(
        ProductExperiment(
            id=attr.experiment_id,
            operator_profile_id=profile.id,
            operator_profile_version=profile.version,
            name="Source projection",
            created_at=now,
        ),
        ProductWorkflow(
            id=attr.workflow_run_id,
            experiment_id=attr.experiment_id,
            role="IDEA_TO_RESEARCH",
            created_at=now,
        ),
        ProductAgent(
            id=agent_id,
            workflow_id=attr.workflow_run_id,
            role="MARKET_RESEARCH",
            created_at=now,
        ),
        command_key=uuid4(),
    )
    seed = await repo.append_artifact(
        artifact(
            attr.experiment_id,
            ArtifactKind.IDEA_SEED,
            {"origin": "USER_SUPPLIED", "statement": "Investigate demand"},
        ),
        command_key=uuid4(),
    )
    payload = (
        finding(ArtifactInput.from_receipt(seed, role="SEED"), uuid4())
        .payload()
        .model_dump(mode="json")
    )
    receipt = await repo.append_artifact(
        artifact(attr.experiment_id, ArtifactKind.RESEARCH_EVIDENCE, payload),
        inputs=(ArtifactInput.from_receipt(seed, role="RESEARCH_SUBJECT"),),
        sources=(reference,),
        command_key=uuid4(),
    )
    case = await IdeaResearchRepository(governance_engine, clock=lambda: now).get_case(
        attr.experiment_id, profile.operator_id
    )
    assert case.subjects[0].findings[0].sources[0].url == "https://example.com/research"
    assert "PRIVATE BODY" not in case.model_dump_json()
    async with governance_engine.connect() as connection:
        saved = await connection.scalar(
            select(records.artifacts.c.payload).where(
                records.artifacts.c.id == receipt.artifact_id
            )
        )
    assert saved == payload
    assert "https://example.com/research" not in str(saved)
