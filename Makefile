.PHONY: install check lint typecheck test build

install:
	uv sync --all-groups

lint:
	uv run ruff check src tests examples
	uv run ruff format --check src tests examples

typecheck:
	uv run mypy

test:
	uv run pytest -q

check: lint typecheck test

build:
	rm -rf dist && uv build
