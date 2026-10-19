.PHONY: venv install lock ruff ruff-check ruff-unsafe-fix ty package pre-commit

venv:
	uv venv --python 3.12

install:
	uv sync --locked

lock:
	uv lock

ruff:
	uv run --locked ruff format
	uv run --locked ruff check --fix

ruff-check:
	uv run --locked ruff format --check
	uv run --locked ruff check

ruff-unsafe-fix:
	uv run --locked ruff check --fix --unsafe-fixes

ty:
	uv run --locked ty check

package:
	uv build

pre-commit:
	uv run --locked pre-commit install
