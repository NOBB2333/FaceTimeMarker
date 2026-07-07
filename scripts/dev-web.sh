#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"
API_TARGET="${VITE_API_TARGET:-http://127.0.0.1:${API_PORT:-8000}}"

cd "$ROOT/web"

echo "WEB: http://${HOST}:${WEB_PORT}"
echo "API_TARGET: ${API_TARGET}"
echo "Stop: Ctrl+C"
VITE_API_TARGET="$API_TARGET" pnpm exec vite --host "$HOST" --port "$WEB_PORT"
