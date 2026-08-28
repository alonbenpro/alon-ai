from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alon_ai.api.routes.health import router as health_router
from alon_ai.config import Settings, get_settings
from alon_ai.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    configured_settings = settings or get_settings()
    configure_logging(configured_settings)

    application = FastAPI(title="Alon AI API")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[configured_settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health_router, prefix="/health")
    application.state.settings = configured_settings
    return application


app = create_app()
