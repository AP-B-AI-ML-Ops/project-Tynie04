.PHONY: post-create init env sync lint format type-check test pre-commit-install \
        gitignore freeze dev-tools up down build logs ps clean

# Devcontainer setup

post-create: init sync pre-commit-install

init:
	@echo "Initializing Python environment..."
	@(uv python install ${PYTHON_VERSION} && \
	if [ ! -f pyproject.toml ]; then \
		if [ "${UV_INIT_BARE}" = "true" ]; then \
			uv init --bare --python ${PYTHON_VERSION}; \
		else \
			uv init --python ${PYTHON_VERSION}; \
		fi; \
	fi) > /tmp/init.log 2>&1
	@echo "Initialization complete (log: /tmp/init.log)"

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		printf "\n"; \
		printf "WARNING: .env was created from .env.example\n"; \
	fi

sync:
	@echo "Syncing dependencies..."
	@uv sync > /tmp/uv-sync.log 2>&1
	@echo "Dependency sync complete (log: /tmp/uv-sync.log)"

pre-commit-install:
	@echo "Installing pre-commit hooks..."
	@uv run pre-commit install > /tmp/pre-commit-install.log 2>&1
	@echo "Pre-commit hooks installed (log: /tmp/pre-commit-install.log)"

dev-tools:
	@echo "Installing dev tools..."
	@uv add --dev ruff mypy pytest pytest-cov pre-commit > /tmp/dev-tools.log 2>&1
	@echo "Dev tools installed (log: /tmp/dev-tools.log)"

# Code quality

lint:
	@uv run ruff check .

lint-fix:
	@uv run ruff check --fix .

format:
	@uv run ruff format .

format-check:
	@uv run ruff format --check .

type-check:
	@uv run mypy src/

test:
	@uv run pytest tests/

test-cov:
	@uv run pytest tests/ --cov=src --cov-report=term-missing

pre-commit-run:
	@uv run pre-commit run --all-files

# Utilities

gitignore:
	@if [ -f .gitignore ]; then \
		echo ".gitignore already exists, skipping"; \
	else \
		( \
			curl -fsSL https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore -o .gitignore; \
			echo ".gitignore created"; \
		) > /tmp/gitignore.log 2>&1; \
		echo ".gitignore download complete (log: /tmp/gitignore.log)"; \
	fi

freeze:
	@echo "Freezing dependencies..."
	@echo "# Generated on $$(date)" > /tmp/requirements.txt
	@uv pip freeze >> /tmp/requirements.txt
	@echo "Dependencies frozen to /tmp/requirements.txt"

# Docker Compose (full stack)

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans
