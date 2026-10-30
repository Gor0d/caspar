#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
(cd frontend && npm ci --no-audit --no-fund && npm run build)
.venv/bin/python -m backend.cli init
printf 'CASPAR instalado. Execute: sh scripts/start.sh\n'
