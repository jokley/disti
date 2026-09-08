#!/usr/bin/env bash
set -Eeuo pipefail
DISTI_USER="${DISTI_USER:-pi}"; DEPLOY_BRANCH=main; COMPOSE_PROFILE=raspberry; REPLACE_CONFIG=false
CONFIG_FILE=/etc/disti-update.conf; RUNTIME_SCRIPT=/usr/local/sbin/disti-update
log(){ printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"; }; fail(){ log "ERROR: $*" >&2; exit 1; }
usage(){ echo "Usage: sudo $0 [--branch qa|main] [--compose-profile base|raspberry] [--replace-config]"; }
while (($#)); do case "$1" in --branch) DEPLOY_BRANCH="${2:?}";shift 2;; --compose-profile) COMPOSE_PROFILE="${2:?}";shift 2;; --replace-config) REPLACE_CONFIG=true;shift;; -h|--help) usage;exit;; *) fail "Unknown argument: $1";; esac; done
[[ $EUID -eq 0 ]] || fail "Run with sudo"; case "$DEPLOY_BRANCH" in qa|main);;*) fail "Branch must be qa or main";;esac; case "$COMPOSE_PROFILE" in base|raspberry);;*) fail "Compose profile must be base or raspberry";;esac
id "$DISTI_USER" >/dev/null 2>&1 || fail "User does not exist: $DISTI_USER"
GROUP=$(id -gn "$DISTI_USER"); HOME_DIR=$(getent passwd "$DISTI_USER"|cut -d: -f6); SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")"&&pwd); REPO_DIR=$(cd "$SCRIPT_DIR/.."&&pwd)
for f in "$SCRIPT_DIR/rollout/disti-update" "$SCRIPT_DIR/rollout/disti-update.service" "$SCRIPT_DIR/rollout/disti-update.timer"; do [[ -f $f ]]||fail "Missing $f";done
for c in git docker curl flock;do command -v "$c" >/dev/null||fail "Missing command: $c";done; docker compose version >/dev/null||fail "Compose v2 unavailable"
chown -R "$DISTI_USER:$GROUP" "$REPO_DIR"
install -o root -g root -m0755 "$SCRIPT_DIR/rollout/disti-update" "$RUNTIME_SCRIPT"
install -o root -g root -m0644 "$SCRIPT_DIR/rollout/disti-update.service" /etc/systemd/system/disti-update.service
install -o root -g root -m0644 "$SCRIPT_DIR/rollout/disti-update.timer" /etc/systemd/system/disti-update.timer
sed -i -e "s/^User=.*/User=$DISTI_USER/" -e "s/^Group=.*/Group=$GROUP/" /etc/systemd/system/disti-update.service
if [[ ! -e "$REPO_DIR/disti.env" ]]; then
  [[ -f "$REPO_DIR/disti.env.example" ]] || fail "Missing disti.env.example"
  install -o "$DISTI_USER" -g "$GROUP" -m0600 "$REPO_DIR/disti.env.example" "$REPO_DIR/disti.env"
  log "Created $REPO_DIR/disti.env; replace placeholder credentials before starting DISTI"
else
  log "Preserving $REPO_DIR/disti.env"
fi
if [[ ! -e $CONFIG_FILE || $REPLACE_CONFIG == true ]];then cat >"$CONFIG_FILE" <<CFG
DISTI_DIR="$REPO_DIR"
DEPLOY_BRANCH="$DEPLOY_BRANCH"
COMPOSE_PROFILE="$COMPOSE_PROFILE"
HEALTH_URL="http://127.0.0.1:5000/healthz"
HEALTH_RETRIES="12"
HEALTH_SLEEP_SEC="10"
COMPOSE_WAIT_TIMEOUT_SEC="180"
DISTI_ENV_FILE="$REPO_DIR/disti.env"
CFG
chmod 0644 "$CONFIG_FILE";chown root:root "$CONFIG_FILE";else log "Preserving $CONFIG_FILE";fi
[[ "$REPO_DIR" == "$HOME_DIR"* ]]||log "WARNING: repository is outside $DISTI_USER home"
systemctl daemon-reload;systemctl enable --now disti-update.timer;log "DISTI rollout installed"
