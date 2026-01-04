#!/bin/bash
set -e

echo "Running Ruff linter..."
ruff check .

echo "Running Ruff formatter check..."
ruff format --check .

echo "Running Mypy type checker..."
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
mypy src/

echo "Running Bandit security scan..."
bandit -r src/

echo "Running tests with coverage..."
pytest

echo "✅ All checks passed!"