PYTHON ?= .venv/bin/python

.PHONY: venv install ruff ruff-check package

venv:
	python3 -m venv .venv

install:
	$(PYTHON) -m pip install -e '.[dev]'

ruff:
	$(PYTHON) -m ruff format
	$(PYTHON) -m ruff check --fix

ruff-check:
	$(PYTHON) -m ruff format --check
	$(PYTHON) -m ruff check

package:
	$(PYTHON) -m build
