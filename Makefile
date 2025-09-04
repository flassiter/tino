.PHONY: test coverage run lint format clean install dev-install build dist check help

# Default Python executable
PYTHON ?= python3

# Source and test directories
SRC_DIR = src/tino
TEST_DIR = tests

help:			## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test:			## Run tests with pytest
	$(PYTHON) -m pytest $(TEST_DIR) -v

test-fast:		## Run tests without verbose output
	$(PYTHON) -m pytest $(TEST_DIR) -q

coverage:		## Run tests with coverage report
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term --cov-report=xml

coverage-html:		## Generate HTML coverage report only
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

run:			## Run the tino application
	$(PYTHON) -m tino

lint:			## Run linting with ruff
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)

lint-fix:		## Run linting with automatic fixes
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR) --fix

format:			## Format code with black and ruff
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR) --fix

format-check:		## Check if code is properly formatted
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)

typecheck:		## Run type checking with mypy
	$(PYTHON) -m mypy $(SRC_DIR)

check:			## Run all checks (lint, format, typecheck)
	@echo "Running format check..."
	@$(MAKE) format-check
	@echo "Running lint check..."
	@$(MAKE) lint
	@echo "Running type check..."
	@$(MAKE) typecheck
	@echo "All checks passed!"

install:		## Install package in production mode
	$(PYTHON) -m pip install .

dev-install:		## Install package in development mode with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"

build:			## Build distribution packages
	$(PYTHON) -m pip install build
	$(PYTHON) -m build

dist:			## Create distribution package
	@$(MAKE) clean
	@$(MAKE) build
	@echo "Distribution packages created in dist/"

upload-test:		## Upload to test PyPI
	$(PYTHON) -m pip install twine
	$(PYTHON) -m twine upload --repository testpypi dist/*

upload:			## Upload to PyPI
	$(PYTHON) -m pip install twine
	$(PYTHON) -m twine upload dist/*

clean:			## Clean build artifacts and cache files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .coverage.*
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -name "*.log" -delete 2>/dev/null || true
	find . -name "*.tino.bak" -delete 2>/dev/null || true

clean-logs:		## Clean application log files
	find ~/.local/share/tino -name "*.log*" -delete 2>/dev/null || true
	find ~/.cache/tino -type f -delete 2>/dev/null || true
	@echo "Application logs cleaned"

# Development targets
dev-setup:		## Set up development environment
	$(PYTHON) -m pip install --upgrade pip setuptools wheel
	@$(MAKE) dev-install
	@echo "Development environment set up successfully"

test-all:		## Run comprehensive test suite
	@echo "Running unit tests..."
	@$(MAKE) test
	@echo "Running coverage analysis..."
	@$(MAKE) coverage
	@echo "Running code quality checks..."
	@$(MAKE) check
	@echo "All tests and checks completed successfully!"

# CI targets for automated testing
ci-test:		## Run tests for CI/CD
	$(PYTHON) -m pytest $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=xml --cov-report=term

ci-check:		## Run quality checks for CI/CD
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m mypy $(SRC_DIR)

# Profiling and benchmarking
profile:		## Profile the application startup
	$(PYTHON) -m cProfile -o profile_output.prof -m tino --help
	@echo "Profile saved to profile_output.prof"

benchmark:		## Run performance benchmarks (when available)
	@if [ -f "benchmarks/run_benchmarks.py" ]; then \
		$(PYTHON) benchmarks/run_benchmarks.py; \
	else \
		echo "Benchmarks not yet available"; \
	fi

# Documentation targets
docs:			## Generate documentation (when available)
	@echo "Documentation generation not yet implemented"

docs-serve:		## Serve documentation locally (when available)
	@echo "Documentation serving not yet implemented"

# Security and dependency checking
security-check:		## Run security checks with bandit
	$(PYTHON) -m pip install bandit[toml]
	$(PYTHON) -m bandit -r $(SRC_DIR) -f json -o security-report.json
	$(PYTHON) -m bandit -r $(SRC_DIR)

deps-check:		## Check for dependency vulnerabilities
	$(PYTHON) -m pip install safety
	$(PYTHON) -m safety check

deps-update:		## Update dependencies (update requirements manually)
	$(PYTHON) -m pip list --outdated
	@echo "Please update pyproject.toml dependencies manually"

# Demo and examples
demo:			## Run demo/example (when available)
	@if [ -f "examples/demo.py" ]; then \
		$(PYTHON) examples/demo.py; \
	else \
		@echo "Running basic tino demo:"; \
		echo "# Demo Document" | $(PYTHON) -m tino; \
	fi

# Database/registry management (for component registry testing)
registry-demo:		## Demonstrate component registry
	$(PYTHON) -c "from $(SRC_DIR).core.registry import ComponentRegistry; r = ComponentRegistry(); print(f'Registry created: {r}')"

# Release management
version:		## Show current version
	@$(PYTHON) -c "import sys; sys.path.insert(0, '$(SRC_DIR)'); from tino import __version__; print(__version__)"

release-check:		## Check if ready for release
	@echo "Checking release readiness..."
	@$(MAKE) clean
	@$(MAKE) test-all
	@$(MAKE) build
	@echo "Release checks completed successfully!"

# Platform-specific targets
windows-setup:		## Set up development on Windows
	python -m pip install --upgrade pip setuptools wheel
	python -m pip install -e ".[dev]"

linux-setup:		## Set up development on Linux
	python3 -m pip install --upgrade pip setuptools wheel
	python3 -m pip install -e ".[dev]"

# Quick development workflow
quick-check:		## Quick format and test for development
	@$(MAKE) format
	@$(MAKE) test-fast
	@echo "Quick check completed!"

# Show project info
info:			## Show project information
	@echo "Tino Editor Project Information"
	@echo "=============================="
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Project: $(shell pwd)"
	@echo "Source: $(SRC_DIR)"
	@echo "Tests: $(TEST_DIR)"
	@echo ""
	@echo "Available targets:"
	@$(MAKE) help