#!/usr/bin/env bash
#
# One-shot developer environment setup for the akselrod repo.
# Run this after cloning: it installs the package in editable mode with
# dev extras, registers a Jupyter kernel, and installs the nbstripout
# git filter so notebook outputs never make it into commits.
#
# Assumes you're already inside an activated virtualenv (.venv).

set -euo pipefail

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  echo "ERROR: no active virtualenv detected." >&2
  echo "  Run: python3 -m venv .venv && source .venv/bin/activate" >&2
  exit 1
fi

echo "==> Installing pd with dev extras..."
pip install -e '.[dev]'

echo "==> Registering Jupyter kernel 'pd'..."
python -m ipykernel install --user --name pd --display-name "Python 3 (pd)"

echo "==> Installing nbstripout as a git filter for this repo..."
nbstripout --install --attributes .gitattributes

echo
echo "Done. To start experimenting:"
echo "  jupyter lab notebooks/experiment_template.ipynb"
