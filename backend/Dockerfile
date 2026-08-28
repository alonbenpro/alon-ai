FROM ghcr.io/astral-sh/uv:0.11.26 AS uv

FROM python:3.13-slim-bookworm

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=uv /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 10001 alon_ai \
    && useradd --system --uid 10001 --gid alon_ai --home-dir /nonexistent --shell /usr/sbin/nologin alon_ai \
    && chown -R alon_ai:alon_ai /app

USER alon_ai
CMD ["uvicorn", "alon_ai.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
