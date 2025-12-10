.PHONY: install dev test clean build ui venv lint

PYTHON := python3
VENV := .venv
PDM := pdm

venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Activate with: source $(VENV)/bin/activate"

install:
	$(PDM) install

dev:
	$(PDM) install -G dev

test:
	$(PDM) run pytest -v

test-cov:
	$(PDM) run pytest --cov=fileskadis --cov-report=term-missing

lint:
	$(PDM) run ruff check src tests
	$(PDM) run ruff format --check src tests

format:
	$(PDM) run ruff check --fix src tests
	$(PDM) run ruff format src tests

ui:
	$(PDM) run fileskadis-ui

build:
	$(PDM) build

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

