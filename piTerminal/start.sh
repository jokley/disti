#!/usr/bin/env bash
set -Eeuo pipefail
[[ -r /etc/disti-kiosk.conf ]] && source /etc/disti-kiosk.conf
KIOSK_URL="${KIOSK_URL:-http://127.0.0.1/}";KIOSK_HEALTH_URL="${KIOSK_HEALTH_URL:-http://127.0.0.1/}";KIOSK_WAIT_TIMEOUT_SEC="${KIOSK_WAIT_TIMEOUT_SEC:-300}"
[[ -n ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]]||{ echo 'No graphical session' >&2;exit 1;}
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/disti-kiosk.lock";flock -n 9||{ echo 'DISTI kiosk already running';exit 0;}
BROWSER=$(command -v chromium||command -v chromium-browser||true);[[ -n $BROWSER ]]||{ echo 'Chromium not found' >&2;exit 1;}
deadline=$((SECONDS+KIOSK_WAIT_TIMEOUT_SEC));until curl --fail --silent --max-time 5 "$KIOSK_HEALTH_URL" >/dev/null;do ((SECONDS<deadline))||{ echo 'DISTI UI readiness timeout' >&2;exit 1;};sleep 2;done
exec "$BROWSER" --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --no-first-run "$KIOSK_URL"
