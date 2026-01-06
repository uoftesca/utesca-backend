# CI/CD Pipeline Documentation

## Overview

The UTESCA Backend uses GitHub Actions for continuous integration and continuous deployment (CI/CD). The pipeline automatically runs on every pull request and push to the `main` branch.

## Pipeline Jobs

The CI pipeline consists of four parallel jobs:

### 1. **Lint Job** (Ruff)
- Checks code style and formatting
- Ensures consistency across the codebase
- Runs: `ruff check .` and `ruff format --check .`
- Configuration: `[tool.ruff]` section in `pyproject.toml`

### 2. **Type Check Job** (Mypy)
- Validates type hints and type safety
- Catches potential type-related bugs
- Runs: `mypy src/` with `PYTHONPATH="${PWD}/src"`
- Configuration: `[tool.mypy]` section in `pyproject.toml`
- All mypy settings (namespace packages, error codes, exclusions) are configured in `pyproject.toml` for consistency

### 3. **Security Scan Job** (Bandit)
- Scans for common security vulnerabilities
- Identifies potential security issues in the code
- Runs: `bandit -r src/`

### 4. **Test Job** (Pytest)
- Runs all unit and integration tests
- Generates code coverage reports
- Uploads coverage artifacts
- Runs: `pytest --cov=src --cov-report=term --cov-report=xml --cov-report=html`
- Configuration: `[tool.pytest.ini_options]` section in `pyproject.toml`

## Running CI Checks Locally

To run all CI checks locally before pushing:

```bash
./scripts/run_ci_locally.sh
```

This script runs all four jobs sequentially and will fail if any check doesn't pass.

### Running Individual Checks

You can also run individual checks:

```bash
# Linting
ruff check .
ruff format --check .

# Type checking
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
mypy src/

# Security scan
bandit -r src/

# Tests
pytest --cov=src --cov-report=term
```

## Configuration Management

All tool configurations are centralized in `pyproject.toml` for consistency:

- **Mypy**: `[tool.mypy]` - Type checking rules, namespace packages, error codes
- **Ruff**: `[tool.ruff]` and `[tool.ruff.lint]` - Linting and formatting rules
- **Pytest**: `[tool.pytest.ini_options]` - Test discovery and execution options

This single-file configuration approach ensures that CI and local development environments use identical settings.

## Environment Variables

The **Test Job** requires the following secrets to be configured in GitHub:

- `SUPABASE_URL` - Supabase database URL
- `SUPABASE_KEY` - Supabase anon/public key
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (admin access)

These are automatically injected during CI runs and loaded from `.env` file during local development.
