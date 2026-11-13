.PHONY: check e2e format

# Fast checks, run on every change and in CI.
check:
	uv run ruff format --check .
	uv run ruff check .
	uv run python templates/check-docs.py
	uv run pytest tests --ignore=tests/e2e --cov --cov-fail-under=85

# End-to-end tests: hooks and scripts against a temporary git repository.
e2e:
	uv run pytest tests/e2e

format:
	uv run ruff format .
	uv run ruff check --fix .
