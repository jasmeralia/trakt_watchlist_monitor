VENV   := .venv
PIP    := $(VENV)/bin/pip
RUFF   := $(VENV)/bin/ruff
MYPY   := $(VENV)/bin/mypy
PYLINT := $(VENV)/bin/pylint
PYTEST := $(VENV)/bin/pytest

.PHONY: venv lintfix lint test clean

.venv/bin/activate: requirements.txt requirements-dev.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt

venv: .venv/bin/activate

lintfix: .venv/bin/activate
	$(RUFF) check --fix app/ tests/
	$(RUFF) format app/ tests/

lint: .venv/bin/activate
	$(RUFF) check app/ tests/
	$(MYPY) app/
	$(PYLINT) app/
	@if find . -maxdepth 3 -name "*.sh" | grep -q .; then \
	  find . -maxdepth 3 -name "*.sh" -exec shellcheck {} +; \
	fi
	@if [ -f Dockerfile ]; then hadolint Dockerfile; fi

test: .venv/bin/activate
	$(PYTEST) tests/ -v --tb=short

clean:
	rm -rf $(VENV) __pycache__ .mypy_cache .pytest_cache .ruff_cache
