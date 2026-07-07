#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run ruff check src tests
uv run pytest -q

cd "$ROOT/web"
pnpm install
pnpm build
