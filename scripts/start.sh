#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
test -f frontend/dist/index.html || { printf 'Compile o frontend primeiro.\n'; exit 1; }
exec .venv/bin/python -m backend.cli serve
