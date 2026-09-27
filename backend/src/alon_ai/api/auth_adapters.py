"""Cookie handling for auth use cases."""

from fastapi import Response

from alon_ai.services.auth import COOKIE_NAME, SESSION_AGE


class AuthCookieAdapter:
    def __init__(self, response: Response) -> None:
        self.response = response

    def set(self, token: str, *, secure: bool) -> None:
        self.response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=int(SESSION_AGE.total_seconds()),
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
        self.response.headers["Cache-Control"] = "no-store"

    def delete(self) -> None:
        self.response.delete_cookie(COOKIE_NAME, path="/")
        self.response.headers["Cache-Control"] = "no-store"
