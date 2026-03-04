PYTHON ?= python

.PHONY: install format lint typecheck test docker-build docker-up docker-down

install:
	uv sync

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

test:
	uv run pytest

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down

