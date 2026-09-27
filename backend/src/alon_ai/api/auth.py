"""HTTP authentication handlers; session authority lives in services.auth."""

from typing import Annotated

from fastapi import APIRouter, Depends

from alon_ai.api.dependencies import get_auth_service
from alon_ai.api.schemas.auth import LoginRequest, SessionResponse
from alon_ai.services.auth import AuthUseCases

router = APIRouter()
AuthServiceDependency = Annotated[AuthUseCases, Depends(get_auth_service)]


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest, service: AuthServiceDependency) -> SessionResponse:
    return await service.login(body)


@router.get("/session", response_model=SessionResponse)
async def session(service: AuthServiceDependency) -> SessionResponse:
    return service.session()


@router.post("/logout", status_code=204)
async def logout(service: AuthServiceDependency) -> None:
    return await service.logout()
