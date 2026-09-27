"""Resolve configured use-case services and authenticated HTTP identity."""

from fastapi import Request, Response

from alon_ai.api.auth_adapters import AuthCookieAdapter
from alon_ai.api.operator_stream import OperatorStreamAdapter
from alon_ai.services.auth import COOKIE_NAME, AuthUseCases
from alon_ai.services.experiments import ExperimentService
from alon_ai.services.health import HealthService
from alon_ai.services.ideas import IdeaService
from alon_ai.services.intake import IntakeService
from alon_ai.services.operator import OperatorService
from alon_ai.services.research import ResearchService


def get_health_service(request: Request) -> HealthService:
    return HealthService(request.app.state.database_health)


def get_operator_service(request: Request) -> OperatorService:
    return request.app.state.operator_service


def get_operator_stream_service(request: Request) -> OperatorStreamAdapter:
    return request.app.state.operator_stream_factory.for_request(
        request.cookies.get(COOKIE_NAME),
        request.app.state.auth.resolve,
        request.is_disconnected,
    )


def get_experiment_service(request: Request) -> ExperimentService:
    return request.app.state.experiment_service_factory.for_operator(
        request.state.operator.id
    )


def get_intake_service(request: Request) -> IntakeService:
    return request.app.state.experiment_service_factory.intake_for_operator(
        request.state.operator.id
    )


def get_idea_service(request: Request) -> IdeaService:
    return request.app.state.experiment_service_factory.idea_for_operator(
        request.state.operator.id
    )


def get_research_service(request: Request) -> ResearchService:
    return request.app.state.experiment_service_factory.research_for_operator(
        request.state.operator.id
    )


def get_auth_service(request: Request, response: Response) -> AuthUseCases:
    return request.app.state.auth_use_case_factory.for_http(
        AuthCookieAdapter(response),
        request.cookies.get(COOKIE_NAME),
        getattr(request.state, "operator", None),
    )
