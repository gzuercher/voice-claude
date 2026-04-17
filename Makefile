.PHONY: run test lint format check setup

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

run:
	.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000

test:
	.venv/bin/pytest -v

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

check: lint test

docker:
	docker compose up -d --build
