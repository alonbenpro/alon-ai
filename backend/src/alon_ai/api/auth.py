"""Single-operator authentication; browser state never grants API authority."""

import asyncio
import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from alon_ai.config import Settings

COOKIE_NAME = "alon_ai_session"
SESSION_AGE = timedelta(hours=8)
_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_LOGIN_DELAY_THRESHOLD = 5
_LOGIN_DELAY_SECONDS = 2
_LOGIN_WINDOW = timedelta(minutes=15)


class LoginRateLimited(Exception):
    """Another password check is already in progress."""


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
        async with self.engine.begin() as connection:
            # Fail fast across API workers instead of queueing password work.
            acquired = (
                await connection.execute(
                    text("SELECT pg_try_advisory_xact_lock(590006)")
                )
            ).scalar_one()
            if not acquired:
                raise LoginRateLimited
            now = datetime.now(UTC)
            failures = (
                await connection.execute(
                    text("""SELECT count(*) FROM operator_login_failures
                        WHERE auth_subject=:subject AND attempted_at>=:since"""),
                    {"subject": self.subject, "since": now - _LOGIN_WINDOW},
                )
            ).scalar_one()
            if failures >= _LOGIN_DELAY_THRESHOLD:
                # Pace checks under the shared lock, but still evaluate correct
                # credentials: outsiders must not create a persistent lockout.
                await asyncio.sleep(_LOGIN_DELAY_SECONDS)
                now = datetime.now(UTC)
            valid_password = await asyncio.to_thread(
                _password_matches, password, self.verifier
            )
            if not valid_password:
                await connection.execute(
                    text("""INSERT INTO operator_login_failures(id,auth_subject,attempted_at)
                        VALUES (:id,:subject,:attempted_at)"""),
                    {"id": uuid4(), "subject": self.subject, "attempted_at": now},
                )
                return None
            row = (
                (
                    await connection.execute(
                        text("""SELECT id, display_name FROM record_operators
                        WHERE auth_subject=:subject AND status='ACTIVE'"""),
                        {"subject": self.subject},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            session_id = uuid4()
            await connection.execute(
                text("""INSERT INTO operator_sessions
                    (id,operator_id,issued_at,expires_at)
                    VALUES (:id,:operator_id,:issued_at,:expires_at)"""),
                {
                    "id": session_id,
                    "operator_id": row["id"],
                    "issued_at": now,
                    "expires_at": now + SESSION_AGE,
                },
            )
        return self._sign(session_id), OperatorSession(
            id=row["id"], display_name=row["display_name"]
        )

    async def resolve(self, token: str | None) -> OperatorSession | None:
        session_id = self._parse(token)
        if session_id is None:
            return None
        async with self.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("""SELECT o.id, o.display_name
                        FROM operator_sessions s
                        JOIN record_operators o ON o.id=s.operator_id
                        WHERE s.id=:id AND s.revoked_at IS NULL
                          AND s.expires_at>now() AND o.status='ACTIVE'
                          AND o.auth_subject=:subject"""),
                        {"id": session_id, "subject": self.subject},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        return OperatorSession(id=row["id"], display_name=row["display_name"])

    async def logout(self, token: str | None) -> None:
        session_id = self._parse(token)
        if session_id is None:
            return
        async with self.engine.begin() as connection:
            await connection.execute(
                text("""UPDATE operator_sessions SET revoked_at=now()
                    WHERE id=:id AND revoked_at IS NULL"""),
                {"id": session_id},
            )


router = APIRouter()


@router.post("/login", response_model=SessionResponse)
async def login(
    body: LoginRequest, request: Request, response: Response
) -> SessionResponse:
    auth: AuthService = request.app.state.auth
    try:
        result = await auth.login(body.password)
    except LoginRateLimited:
        raise HTTPException(
            status_code=429, detail="Login temporarily unavailable"
        ) from None
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid operator credentials")
    token, operator = result
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(SESSION_AGE.total_seconds()),
        httponly=True,
        secure=auth.secure_cookie,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(operator=operator)


@router.get("/session", response_model=SessionResponse)
async def session(request: Request) -> SessionResponse:
    return SessionResponse(operator=request.state.operator)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    auth: AuthService = request.app.state.auth
    await auth.logout(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"
