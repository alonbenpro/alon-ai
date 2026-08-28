.PHONY: setup generate format lint typecheck test build containers dev down

setup:
	cd backend && uv sync --locked --all-extras --dev
	npm --prefix frontend ci

generate:
	npm --prefix frontend run api:generate

format:
	cd backend && uv run ruff format .
	npm --prefix frontend run lint -- --fix

lint:
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	npm --prefix frontend run lint

typecheck:
	cd backend && uv run pyright
	npm --prefix frontend run typecheck

test:
	cd backend && uv run pytest tests/unit -q
	npm --prefix frontend test -- --run

build:
	cd backend && uv build
	npm --prefix frontend run build

containers:
	docker compose --env-file .env.example -f infra/compose.yaml config
	docker build -f backend/Dockerfile -t alon-ai-backend:local backend
	docker build -f frontend/Dockerfile -t alon-ai-frontend:local frontend

dev:
	docker compose --env-file .env.example -f infra/compose.yaml up --build

down:
	docker compose --env-file .env.example -f infra/compose.yaml down
