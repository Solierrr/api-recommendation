SHELL := /bin/sh

ORG_SCRIPTS_DIR ?= $(HOME)/.local/share/solierrr-infra-scripts
ORG_SCRIPTS_POWERSHELL ?= powershell
EXTRACT_ENV := $(ORG_SCRIPTS_DIR)/scripts/extract-env.ps1
SERVICE := api-recommendation
ENV ?= local
OUT ?= .env
PYTHON ?= python
VENV ?= .venv
VENV_BIN ?= $(VENV)/Scripts
APP_MODULE ?= app.main:app
HOST ?= 127.0.0.1
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: help tools-check env setup run test lint check

help: ## Show the available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\\n\\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\\n", $$1, $$2}' $(MAKEFILE_LIST)

tools-check: ## Verify that the shared organization scripts are installed
	@test -f "$(EXTRACT_ENV)" || { echo "error: infra-scripts was not found at $(ORG_SCRIPTS_DIR)"; exit 1; }

env: tools-check ## Generate .env from Infisical (ENV=local OUT=.env)
	$(ORG_SCRIPTS_POWERSHELL) -NoProfile -ExecutionPolicy Bypass -File "$(EXTRACT_ENV)" -Service "$(SERVICE)" -Environment "$(ENV)" -OutputPath "$(OUT)"

setup: ## Create the virtualenv and install runtime and development dependencies
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/python -m pip install -r requirements.txt -r requirements-dev.txt

run: ## Start the FastAPI development server
	$(VENV_BIN)/python -m uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

test: ## Run tests with coverage
	$(VENV_BIN)/python -m pytest --cov=app --cov-report=term-missing

lint: ## Run Ruff static analysis
	$(VENV_BIN)/python -m ruff check app tests scripts

check: test lint ## Run the local validation suite
