#!/usr/bin/env bash
# Manual compatibility entrypoint; production timers execute the installed copy.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../piTerminal/rollout/disti-update" "$@"
