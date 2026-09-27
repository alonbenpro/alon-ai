"""Single-operator authentication; browser state never grants API authority."""

import hashlib
import hmac
import re
import secrets
from threading import BoundedSemaphore
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.config import Settings
from alon_ai.db.repositories.auth import (
    LOGIN_CAPACITY,
    SESSION_AGE,
    AuthRepository,
    LoginRateLimited,
)

COOKIE_NAME = "alon_ai_session"
__all__ = [
    "SESSION_AGE",
    "AuthService",
    "AuthUseCases",
    "LoginRateLimited",
    "hash_password",
]
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Create a verifier for trusted operator provisioning, never a browser response."""
    chosen_salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode(),
        salt=chosen_salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${chosen_salt.hex()}${derived.hex()}"


def _password_matches(password: str, verifier: str) -> bool:
    try:
        name, n, r, p, salt, expected = verifier.split("$")
        if (name, int(n), int(r), int(p)) != (
            "scrypt",
            _SCRYPT_N,
            _SCRYPT_R,
            _SCRYPT_P,
        ):
            return False
        salt_bytes = bytes.fromhex(salt)
        expected_bytes = bytes.fromhex(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 32:
            return False
        actual = hashlib.scrypt(
            password.encode(),
            salt=salt_bytes,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=32,
            maxmem=64 * 1024 * 1024,
        )
        return hmac.compare_digest(actual, expected_bytes)
    except (ValueError, UnicodeError):
        return False


class OperatorSession(BaseModel):
    id: UUID
    display_name: str


class SessionResponse(BaseModel):
    authenticated: bool = True
    operator: OperatorSession


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class AuthService:
    def __init__(self, engine: AsyncEngine, settings: Settings) -> None:
        self.engine = engine
        self._login_admissions = BoundedSemaphore(LOGIN_CAPACITY)
        self.repository = AuthRepository(engine)
        self.subject = settings.operator_auth_subject
        self.verifier = (
            settings.operator_password_hash.get_secret_value()
            if settings.operator_password_hash
            else None
        )
        self.key = (
            settings.session_signing_key.get_secret_value().encode()
            if settings.session_signing_key
            else None
        )
        self.secure_cookie = settings.frontend_origin.startswith("https://")
        self.configured = bool(
            self.subject and self.verifier and self.key and len(self.key) >= 32
        )

    def _sign(self, session_id: UUID) -> str:
        assert self.key is not None
        body = f"v1.{session_id}"
        signature = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def _parse(self, token: str | None) -> UUID | None:
        if not self.configured or not token or len(token) > 120:
            return None
        try:
            version, raw_id, signature = token.split(".")
            session_id = UUID(raw_id)
            if (
                version != "v1"
                or re.fullmatch(r"[0-9a-f]{64}", signature, re.ASCII) is None
            ):
                return None
            if not hmac.compare_digest(self._sign(session_id), token):
                return None
            return session_id
        except (ValueError, AttributeError, TypeError):
            return None

    async def login(self, password: str) -> tuple[str, OperatorSession] | None:
        if not self.configured or self.verifier is None or self.subject is None:
            return None
        # Bound local connection demand before entering SQLAlchemy's pool.
        if not self._login_admissions.acquire(blocking=False):
            raise LoginRateLimited
        try:
            return await self._login_admitted(password, self.verifier)
        finally:
            self._login_admissions.release()

    async def _login_admitted(
        self, password: str, verifier: str
    ) -> tuple[str, OperatorSession] | None:
        assert self.subject is not None
        result = await self.repository.login_admitted(
            self.subject, password, verifier, _password_matches
        )
        if result is None:
            return None
        session_id, operator_id, display_name = result
        return self._sign(session_id), OperatorSession(
            id=operator_id, display_name=display_name
        )

    async def resolve(self, token: str | None) -> OperatorSession | None:
        session_id = self._parse(token)
        if session_id is None or self.subject is None:
            return None
        row = await self.repository.resolve(session_id, self.subject)
        if row is None:
            return None
        return OperatorSession(id=row[0], display_name=row[1])

    async def logout(self, token: str | None) -> None:
        session_id = self._parse(token)
        if session_id is not None:
            await self.repository.logout(session_id)


class InvalidCredentials(Exception):
    """Login credentials do not identify the active operator."""


class SessionCookiePort(Protocol):
    def set(self, token: str, *, secure: bool) -> None: ...
    def delete(self) -> None: ...


class AuthUseCases:
    def __init__(
        self,
        auth: AuthService,
        cookies: SessionCookiePort,
        token: str | None,
        operator: OperatorSession | None,
    ) -> None:
        self.auth = auth
        self.cookies = cookies
        self.token = token
        self.operator = operator

    async def login(self, body: LoginRequest) -> SessionResponse:
        result = await self.auth.login(body.password)
        if result is None:
            raise InvalidCredentials
        token, operator = result
        self.cookies.set(token, secure=self.auth.secure_cookie)
        return SessionResponse(operator=operator)

    def session(self) -> SessionResponse:
        assert self.operator is not None
        return SessionResponse(operator=self.operator)

    async def logout(self) -> None:
        await self.auth.logout(self.token)
        self.cookies.delete()
