#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x .venv/bin/python ]; then
  exec .venv/bin/python -m singbox_gui "$@"
fi

export PYTHONPATH="$PWD/src"
exec python3 -m singbox_gui "$@"
