#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

pick_python() {
  for candidate in python3.12 python3.11 python3.10 python3; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
      continue
    fi

    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
sys.exit(0 if (3, 9) <= sys.version_info[:2] <= (3, 13) else 1)
PY
    then
      echo "$candidate"
      return 0
    fi
  done

  echo "Could not find a supported Python version (3.10-3.13)." >&2
  exit 1
}

PYTHON_BIN="$(pick_python)"
VENV_DIR="$BACKEND_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" >/dev/null

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  (cd "$FRONTEND_DIR" && npm ci >/dev/null)
fi

cleanup() {
  trap - EXIT
  jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT INT TERM

(
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8001
) &

(
  cd "$FRONTEND_DIR"
  VITE_API_URL="http://127.0.0.1:8001" npm run dev -- --host 127.0.0.1 --port 5173
) &

wait
