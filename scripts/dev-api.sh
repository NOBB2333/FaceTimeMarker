#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"

cd "$ROOT"

echo "API: http://${HOST}:${API_PORT}"
echo "Stop: Ctrl+C"
uv run facetimemarker serve --host "$HOST" --port "$API_PORT"
