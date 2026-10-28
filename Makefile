.PHONY: setup install-dev install-hooks lock docs docs-build migrate migration

setup: install-dev install-hooks
	@echo "Developer environment is ready."

install-dev:
	uv sync --extra dev

install-hooks:
	uv run pre-commit install

lock:
	uv lock

migrate:
	uv run alembic upgrade head

migration:
	@test -n "$(m)" || (echo "Usage: make migration m='describe the change'" && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

docs:
	@cd website && (test -d node_modules || npm install) && npm start

docs-build:
	@cd website && (test -d node_modules || npm install) && npm run build
