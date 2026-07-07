#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
FaceTimeMarker dev scripts are split so each long-running process is explicit.

Terminal 1:
  bash scripts/dev-api.sh

Terminal 2:
  bash scripts/dev-web.sh

Build frontend once:
  bash scripts/build.sh

Hardware detection:
  bash scripts/hardware.sh

Analyze with an explicit hardware profile:
  bash scripts/analyze-cpu.sh path/to/video.mp4 --preset fast --no-cache
  bash scripts/analyze-apple.sh path/to/video.mp4 --preset fast
  bash scripts/analyze-nvidia.sh path/to/video.mp4 --preset fast
  bash scripts/analyze-intel.sh path/to/video.mp4 --preset fast

Benchmark with an explicit hardware profile:
  bash scripts/benchmark-cpu.sh path/to/video.mp4 --preset fast
  bash scripts/benchmark-apple.sh path/to/video.mp4 --preset fast
  NO_CPU_FALLBACK=1 bash scripts/benchmark-nvidia.sh path/to/video.mp4 --preset fast
  NO_CPU_FALLBACK=1 bash scripts/benchmark-intel.sh path/to/video.mp4 --preset fast

Environment overrides:
  HOST=127.0.0.1 API_PORT=8000 WEB_PORT=5173 VITE_API_TARGET=http://127.0.0.1:8000
  HARDWARE_PROFILE=auto|cpu|apple|nvidia|intel NO_CPU_FALLBACK=1
EOF
