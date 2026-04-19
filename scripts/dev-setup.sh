#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
pip install -e ".[dev]"
pre-commit install
echo "Done. Try: pytest -q && ruff check . && mypy autokalshi"
