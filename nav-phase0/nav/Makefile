.DEFAULT_GOAL := help
API := apps/api

help: ## List targets
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-14s %s\n", $$1, $$2}'

up: ## Start the whole stack
	docker compose up --build

down: ## Stop the stack
	docker compose down

reset: ## Stop the stack and delete all data
	docker compose down -v

logs: ## Follow API and worker logs
	docker compose logs -f api worker

migrate: ## Apply migrations inside the api container
	docker compose exec api alembic upgrade head

revision: ## Create a migration from the ORM models (m="message")
	docker compose exec api alembic revision --autogenerate -m "$(m)"

test: ## Backend tests
	cd $(API) && python -m pytest

lint: ## Lint and type-check both apps
	cd $(API) && ruff check . && ruff format --check . && mypy app
	npm run lint && npm run typecheck

check: lint test ## Everything CI runs, locally

.PHONY: help up down reset logs migrate revision test lint check
