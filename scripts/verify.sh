#!/usr/bin/env bash
set -euo pipefail
python -m py_compile backend/app/*.py
(cd backend && python -m pytest -q)
(cd frontend && npm run build)
