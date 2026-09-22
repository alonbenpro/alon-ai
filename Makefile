.PHONY: setup roadmap generate format lint typecheck test test-integration build containers dev down database migrate api worker frontend

COMPOSE ?= docker compose
COMPOSE_ARGS ?= --env-file .env.example -f infra/compose.yaml

setup:
	cd backend && uv sync --locked --all-extras --dev
	npm --prefix frontend ci

roadmap:
	python3 scripts/validate_roadmap.py --check

generate:
	npm --prefix frontend run api:generate

format:
	cd backend && uv run ruff format .
	npm --prefix frontend run lint -- --fix

lint: roadmap
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	npm --prefix frontend run lint

typecheck:
	cd backend && uv run pyright
	npm --prefix frontend run typecheck

test: roadmap
	cd backend && uv run pytest tests/unit -q
	npm --prefix frontend test -- --run

test-integration:
	cd backend && uv run --locked pytest tests/integration -q

build:
	cd backend && uv build
	npm --prefix frontend run build

containers:
	$(COMPOSE) $(COMPOSE_ARGS) config --quiet
	$(COMPOSE) $(COMPOSE_ARGS) build api worker frontend

database:
	$(COMPOSE) $(COMPOSE_ARGS) up --detach --wait postgres

migrate:
	cd backend && uv run --locked alembic upgrade head

dbos-migrate:
	cd backend && uv run --locked dbos migrate --sys-db-url "$${ALON_AI_DBOS_SYSTEM_DATABASE_URL:?set ALON_AI_DBOS_SYSTEM_DATABASE_URL}" --schema dbos

api:
	cd backend && uv run --locked uvicorn alon_ai.api.app:app --host 127.0.0.1 --port 8000 --no-access-log

worker:
	cd backend && uv run --locked python -m alon_ai.worker.main

frontend:
	npm --prefix frontend run dev -- --hostname 127.0.0.1

dev: database
	$(COMPOSE) $(COMPOSE_ARGS) run --build --rm api alembic upgrade head
	$(COMPOSE) $(COMPOSE_ARGS) run --build --rm worker dbos migrate --sys-db-url postgresql://alon_ai:alon_ai@postgres:5432/alon_ai --schema dbos
	$(COMPOSE) $(COMPOSE_ARGS) up --build

down:
	$(COMPOSE) $(COMPOSE_ARGS) down
