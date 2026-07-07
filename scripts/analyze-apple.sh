#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARDWARE_PROFILE=apple exec "$SCRIPT_DIR/analyze-hardware.sh" "$@"
