"""Construct application dependencies at process and workflow boundaries."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.api.operator_stream import OperatorStreamFactory
from alon_ai.config import Settings, get_settings
from alon_ai.db.engine import DatabaseHealthChecker, create_engine
from alon_ai.db.repositories.operator_activity import OperatorActivityRepository
from alon_ai.provider_usage.recorded_idea import provision_recorded_seeded_runtime
from alon_ai.services.agent_run_service import AgentRunService
from alon_ai.services.auth import (
    AuthService,
    AuthUseCases,
    OperatorSession,
    SessionCookiePort,
)
from alon_ai.services.experiments import ExperimentContext, ExperimentService
from alon_ai.services.ideas import IdeaService
from alon_ai.services.operator import OperatorService
from alon_ai.services.research import ResearchService


async def recorded_runtime_provisioner(*args, **kwargs):
    """Resolve the configured recorded provider when an Idea command starts."""
    return await provision_recorded_seeded_runtime(*args, **kwargs)


def load_idea_runtime_provider(settings: Settings):
    """Load the same governed live provider for API and Idea worker processes."""
    if settings.provider_mode != "live":
        return None
    import os
    import stat

    from alon_ai.services.combined_idea import (
        build_combined_idea_provider,
    )
    from alon_ai.services.combined_idea_provision import (
        load_combined_idea_runtime_config,
        load_combined_secret_store,
    )

    config_path = settings.r01a_live_config_path
    if config_path is None:
        return None
    try:
        info = config_path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 262144
        ):
            raise ValueError("private configuration required")
        config = load_combined_idea_runtime_config(config_path)
        secrets = load_combined_secret_store(config_path.parent, config)
        return build_combined_idea_provider(config, secrets, settings)
    except Exception:  # noqa: BLE001 - never expose configuration or key details
        raise RuntimeError("R01A live runtime configuration invalid") from None


@asynccontextmanager
async def workflow_engine_scope() -> AsyncIterator[AsyncEngine]:
    """Give each durable step its own engine and dispose it when the step exits."""
    engine = create_engine(get_settings())
    try:
        yield engine
    finally:
        await engine.dispose()


@dataclass(frozen=True)
class ExperimentServiceFactory:
    engine: AsyncEngine
    settings: Settings
    idea_runtime_provider: object | None
    recorded_runtime_provisioner: object

    def _context(self, operator_id: UUID) -> ExperimentContext:
        return ExperimentContext(
            engine=self.engine,
            settings=self.settings,
            operator_id=operator_id,
            idea_runtime_provider=self.idea_runtime_provider,
            recorded_runtime_provisioner=self.recorded_runtime_provisioner,
        )

    def for_operator(self, operator_id: UUID) -> ExperimentService:
        return ExperimentService(self._context(operator_id))

    def intake_for_operator(self, operator_id: UUID):
        from alon_ai.services.intake import IntakeService

        return IntakeService(self._context(operator_id))

    def idea_for_operator(self, operator_id: UUID) -> IdeaService:
        return IdeaService(self._context(operator_id))

    def agent_runs_for_operator(self, operator_id: UUID) -> AgentRunService:
        return AgentRunService(self._context(operator_id))

    def research_for_operator(self, operator_id: UUID) -> ResearchService:
        return ResearchService(self._context(operator_id))


@dataclass(frozen=True)
class AuthUseCaseFactory:
    auth: AuthService

    def for_http(
        self,
        cookies: SessionCookiePort,
        token: str | None,
        operator: OperatorSession | None,
    ) -> AuthUseCases:
        return AuthUseCases(self.auth, cookies, token, operator)


@dataclass(frozen=True)
class APIResources:
    engine: AsyncEngine
    auth: AuthService
    database_health: DatabaseHealthChecker
    idea_runtime_provider: object | None
    operator_service: OperatorService
    operator_stream_factory: OperatorStreamFactory
    experiment_service_factory: ExperimentServiceFactory
    auth_use_case_factory: AuthUseCaseFactory


@asynccontextmanager
async def api_resource_scope(settings: Settings) -> AsyncIterator[APIResources]:
    """Construct and release the API's configured dependencies."""
    engine = create_engine(settings)
    auth = AuthService(engine, settings)
    if settings.environment == "production" and not auth.configured:
        await engine.dispose()
        raise RuntimeError("Operator authentication is not configured")
    try:
        provider = load_idea_runtime_provider(settings)
        database_health = DatabaseHealthChecker(engine)
        operator_service = OperatorService(OperatorActivityRepository(engine))
        yield APIResources(
            engine=engine,
            auth=auth,
            database_health=database_health,
            idea_runtime_provider=provider,
            operator_service=operator_service,
            operator_stream_factory=OperatorStreamFactory(operator_service),
            experiment_service_factory=ExperimentServiceFactory(
                engine, settings, provider, recorded_runtime_provisioner
            ),
            auth_use_case_factory=AuthUseCaseFactory(auth),
        )
    finally:
        await engine.dispose()
