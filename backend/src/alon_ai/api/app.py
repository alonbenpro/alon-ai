from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alon_ai.accounting.models import AccountingDenied
from alon_ai.api.auth import COOKIE_NAME, AuthService
from alon_ai.api.auth import router as auth_router
from alon_ai.api.live_idea_runtime import (
    build_live_idea_runtime_provider,
    load_live_idea_runtime_config,
    load_live_secret_store,
)
from alon_ai.api.middleware.request_logging import RequestLoggingMiddleware
from alon_ai.api.routes.experiments import router as experiments_router
from alon_ai.api.routes.health import router as health_router
from alon_ai.api.routes.operator import router as operator_router
from alon_ai.config import Settings, get_settings
from alon_ai.db.engine import DatabaseHealthChecker, create_engine
from alon_ai.logging import configure_logging
from alon_ai.security.secrets import SecretStoreError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.auth = AuthService(engine, settings)
    if settings.environment == "production" and not app.state.auth.configured:
        await engine.dispose()
        raise RuntimeError("Operator authentication is not configured")
    app.state.database_health = DatabaseHealthChecker(engine)
    app.state.idea_runtime_provider = None
    try:
        if settings.provider_mode == "live":
            config_path = settings.l07_live_config_path
            secret_root = settings.l07_secret_root
            key_file = settings.l07_secret_key_file
            key_version = settings.l07_secret_key_version
            if any(
                value is not None
                for value in (config_path, secret_root, key_file, key_version)
            ):
                if (
                    config_path is None
                    or secret_root is None
                    or key_file is None
                    or key_version != "v1"
                    or config_path != key_file.parent / "live-idea.json"
                    or secret_root != key_file.parent / "secrets"
                ):
                    raise RuntimeError("L07 live runtime configuration invalid")
                try:
                    config = load_live_idea_runtime_config(config_path)
                    secrets = load_live_secret_store(
                        key_file.parent, allowed_handle=config.secret_handle
                    )
                    secrets.get(config.secret_handle)
                    app.state.idea_runtime_provider = build_live_idea_runtime_provider(
                        config, secrets
                    )
                except (AccountingDenied, SecretStoreError):
                    raise RuntimeError(
                        "L07 live runtime configuration invalid"
                    ) from None
        yield
    finally:
        await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()
    configure_logging(configured_settings)

    application = FastAPI(title="Alon AI API", lifespan=lifespan)
    application.add_middleware(RequestLoggingMiddleware)

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
