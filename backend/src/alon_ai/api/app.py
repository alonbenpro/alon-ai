from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alon_ai.api.auth import router as auth_router
from alon_ai.api.middleware.request_logging import RequestLoggingMiddleware
from alon_ai.api.routes.experiments import router as experiments_router
from alon_ai.api.routes.health import router as health_router
from alon_ai.api.routes.operator import router as operator_router
from alon_ai.bootstrap import api_resource_scope
from alon_ai.config import Settings, get_settings
from alon_ai.logging import configure_logging
from alon_ai.services.auth import (
    COOKIE_NAME,
    AuthService,
    InvalidCredentials,
    LoginRateLimited,
)
from alon_ai.services.experiments import ExperimentError
from alon_ai.services.health import ReadinessUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with api_resource_scope(app.state.settings) as resources:
        app.state.engine = resources.engine
        app.state.auth = resources.auth
        app.state.database_health = resources.database_health
        app.state.idea_runtime_provider = resources.idea_runtime_provider
        app.state.operator_service = resources.operator_service
        app.state.operator_stream_factory = resources.operator_stream_factory
        app.state.experiment_service_factory = resources.experiment_service_factory
        app.state.auth_use_case_factory = resources.auth_use_case_factory
        yield


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()
    configure_logging(configured_settings)

    application = FastAPI(title="Alon AI API", lifespan=lifespan)
    application.add_middleware(RequestLoggingMiddleware)

    @application.exception_handler(LoginRateLimited)
    async def login_rate_limited(request: Request, error: LoginRateLimited):
        return JSONResponse(
            status_code=429, content={"detail": "Login temporarily unavailable"}
        )

    @application.exception_handler(InvalidCredentials)
    async def invalid_credentials(request: Request, error: InvalidCredentials):
        return JSONResponse(
            status_code=401, content={"detail": "Invalid operator credentials"}
        )

    @application.exception_handler(ExperimentError)
    async def experiment_error(request: Request, error: ExperimentError):
        return JSONResponse(
            status_code=error.status_code, content={"detail": error.detail}
        )

    @application.exception_handler(ReadinessUnavailable)
    async def readiness_unavailable(request: Request, error: ReadinessUnavailable):
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "down"},
        )

    @application.exception_handler(RequestValidationError)
    async def redact_login_validation(request: Request, error: RequestValidationError):
        if request.url.path == "/auth/login":
            return JSONResponse(
                status_code=422,
                content={"detail": "Invalid login request"},
                headers={"Cache-Control": "no-store"},
            )
        return await request_validation_exception_handler(request, error)

    @application.middleware("http")
    async def require_private_session(request: Request, call_next):
        path = request.url.path
        public = path in {
            "/health/live",
            "/health/ready",
            "/auth/login",
            "/auth/logout",
        }
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin != configured_settings.frontend_origin
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin denied"},
                headers={"Cache-Control": "no-store"},
            )
        if not public and request.method != "OPTIONS":
            auth: AuthService = request.app.state.auth
            operator = await auth.resolve(request.cookies.get(COOKIE_NAME))
            if operator is None:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Operator session required"},
                    headers={"Cache-Control": "no-store"},
                )
            request.state.operator = operator
        response = await call_next(request)
        if not public or path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[configured_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/health")
    application.include_router(auth_router, prefix="/auth")
    application.include_router(operator_router, prefix="/operator")
    application.include_router(experiments_router, prefix="/operator")
    application.state.settings = configured_settings
    return application


app = create_app()
