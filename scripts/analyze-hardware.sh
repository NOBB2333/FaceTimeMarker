#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${HARDWARE_PROFILE:-auto}"

if [[ "$#" -lt 1 ]]; then
  cat <<'EOF'
Usage:
  HARDWARE_PROFILE=auto|cpu|apple|nvidia|intel bash scripts/analyze-hardware.sh path/to/video.mp4 [facetimemarker analyze options]

Examples:
  bash scripts/analyze-cpu.sh video.mp4 --preset fast --no-cache
  bash scripts/analyze-apple.sh video.mp4 --preset balanced
  NO_CPU_FALLBACK=1 bash scripts/analyze-nvidia.sh video.mp4 --preset fast
EOF
  exit 2
fi

EXTRA_ARGS=()
if [[ "${NO_CPU_FALLBACK:-0}" == "1" || "${ALLOW_CPU_FALLBACK:-1}" == "0" ]]; then
  EXTRA_ARGS+=(--no-cpu-fallback)
fi

cd "$ROOT"
uv run facetimemarker analyze "$@" --hardware-profile "$PROFILE" "${EXTRA_ARGS[@]}"
