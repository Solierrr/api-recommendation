ifeq ($(OS),Windows_NT)
ORG_SCRIPTS_DIR ?= $(USERPROFILE)/.local/share/solierrr-infra-scripts
ORG_SCRIPTS_POWERSHELL ?= powershell
else
ORG_SCRIPTS_DIR ?= $(HOME)/.local/share/solierrr-infra-scripts
ORG_SCRIPTS_POWERSHELL ?= pwsh
endif
ORG_SCRIPTS_REPO ?= https://github.com/Solierrr/infra-scripts.git
EXTRACT_ENV := $(ORG_SCRIPTS_DIR)/scripts/extract-env.ps1
SERVICE ?=
ENV ?=
OUT ?= .env


PYTHON ?= python
VENV ?= .venv
VENV_BIN ?= $(VENV)/Scripts
APP_MODULE ?= app.main:app
HOST ?= 127.0.0.1
PORT ?= 8000

.DEFAULT_GOAL := help

.PHONY: help tools-check env setup run test lint check vault-config vault-auth extract-env

help: ## Show the available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\\n\\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\\n", $$1, $$2}' $(MAKEFILE_LIST)



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

vault-config: ## Clone or update the shared infra-scripts toolkit
	$(ORG_SCRIPTS_POWERSHELL) -NoProfile -ExecutionPolicy Bypass -File scripts/make-vault.ps1 -Action config -ScriptsDir "$(ORG_SCRIPTS_DIR)" -Repo "$(ORG_SCRIPTS_REPO)" -ExtractEnvPath "$(EXTRACT_ENV)"

vault-auth: vault-config ## Check that the Infisical CLI is installed and authenticated
	$(ORG_SCRIPTS_POWERSHELL) -NoProfile -ExecutionPolicy Bypass -File scripts/make-vault.ps1 -Action auth

extract-env: vault-auth ## Generate a local environment file; prompts for missing service/environment
	$(ORG_SCRIPTS_POWERSHELL) -NoProfile -ExecutionPolicy Bypass -File scripts/make-vault.ps1 -Action extract-env -ExtractEnvPath "$(EXTRACT_ENV)" -Service "$(SERVICE)" -Environment "$(ENV)" -OutputPath "$(OUT)"

tools-check: vault-config ## Alias for vault-config

env: extract-env ## Alias for extract-env
