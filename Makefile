# Keyword Finder - Makefile
# Comandos comunes para desarrollo y despliegue

.PHONY: help install dev-install test lint format clean build docs serve

# Variables
PYTHON := python
PIP := pip
PACKAGE_NAME := keyword_finder

# Colores para output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
help: ## Show this help message
	@echo "$(GREEN)Keyword Finder - Development Commands$(NC)"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Installation
install: ## Install package in development mode
	@echo "$(GREEN)Installing $(PACKAGE_NAME)...$(NC)"
	$(PIP) install -e .

dev-install: ## Install with development dependencies
	@echo "$(GREEN)Installing $(PACKAGE_NAME) with dev dependencies...$(NC)"
	$(PIP) install -e ".[dev]"

# Quality checks
lint: ## Run linting (ruff)
	@echo "$(GREEN)Running linter...$(NC)"
	ruff check src/ scripts/ tests/

format: ## Format code (black)
	@echo "$(GREEN)Formatting code...$(NC)"
	black src/ scripts/ tests/

type-check: ## Run type checking (mypy)
	@echo "$(GREEN)Running type checker...$(NC)"
	mypy src/$(PACKAGE_NAME)/

quality: lint format type-check ## Run all quality checks

# Testing
test: ## Run tests
	@echo "$(GREEN)Running tests...$(NC)"
	pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest tests/ --cov=src/$(PACKAGE_NAME)/ --cov-report=html --cov-report=term

# Running
demo: ## Run demo
	@echo "$(GREEN)Running demo...$(NC)"
	$(PYTHON) scripts/demo.py

workflow: ## Run automated workflow
	@echo "$(GREEN)Running automated workflow...$(NC)"
	$(PYTHON) -c "import asyncio; from src.keyword_finder.workflows.automated_workflow import run_automated_workflow; asyncio.run(run_automated_workflow(['marketing digital']))"

interactive: ## Run interactive workflow
	@echo "$(GREEN)Running interactive workflow...$(NC)"
	$(PYTHON) src/keyword_finder/workflows/ejemplo_workflow.py

# Building
build: ## Build package
	@echo "$(GREEN)Building package...$(NC)"
	$(PYTHON) -m build

# Documentation
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	mkdocs build

docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation...$(NC)"
	mkdocs serve

# Cleaning
clean: ## Clean build artifacts and cache
	@echo "$(GREEN)Cleaning...$(NC)"
	rm -rf build/ dist/ *.egg-info/
	rm -rf __pycache__/ .pytest_cache/ .mypy_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean ## Clean everything including logs and exports
	@echo "$(YELLOW)Cleaning logs and exports...$(NC)"
	rm -rf logs/ exports/ cache/
	rm -f *.log *.db

# Docker (if needed in future)
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(PACKAGE_NAME) .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run --rm $(PACKAGE_NAME)

# CI/CD simulation
ci: quality test build ## Run CI pipeline locally

# Development helpers
deps-update: ## Update dependencies
	@echo "$(GREEN)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"

deps-freeze: ## Freeze current dependencies
	@echo "$(GREEN)Freezing dependencies...$(NC)"
	$(PIP) freeze > requirements-frozen.txt

# Info
info: ## Show project information
	@echo "$(GREEN)Project Information$(NC)"
	@echo "==================="
	@echo "Name: $(PACKAGE_NAME)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version)"
	@echo "Location: $(shell pwd)"

# Phony targets
.PHONY: help install dev-install test lint format type-check quality test-cov demo workflow interactive build docs docs-serve clean clean-all docker-build docker-run ci deps-update deps-freeze info