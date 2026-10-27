.PHONY: setup install-dev install-hooks lock docs docs-build

setup: install-dev install-hooks
	@echo "Developer environment is ready."

install-dev:
	uv sync --extra dev

install-hooks:
	uv run pre-commit install

lock:
	uv lock

docs:
	@cd website && (test -d node_modules || npm install) && npm start

docs-build:
	@cd website && (test -d node_modules || npm install) && npm run build
