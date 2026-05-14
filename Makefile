PYTHON ?= .venv/bin/python
PIP ?= $(PYTHON) -m pip

.PHONY: venv install lint-fix lint clean

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install ruff mypy

lint-fix: install
	$(PYTHON) -m ruff check --fix app
	$(PYTHON) -m ruff format app

lint: install
	$(PYTHON) -m ruff check app
	$(PYTHON) -m ruff format --check app
	$(PYTHON) -m mypy app

clean:
	rm -rf .venv .mypy_cache .ruff_cache
