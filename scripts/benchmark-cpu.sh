#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARDWARE_PROFILE=cpu exec "$SCRIPT_DIR/benchmark-hardware.sh" "$@"
