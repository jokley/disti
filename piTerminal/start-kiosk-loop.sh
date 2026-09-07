#!/usr/bin/env bash
set -u
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd)
while true;do "$SCRIPT_DIR/start.sh";echo 'DISTI kiosk exited; retrying in 10 seconds' >&2;sleep 10;done
