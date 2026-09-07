#!/usr/bin/env bash
set -Eeuo pipefail
CONFIG_FILE="${DISTI_UPDATE_CONFIG:-/etc/disti-update.conf}"
[[ -r "$CONFIG_FILE" ]] || { echo "Missing $CONFIG_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$CONFIG_FILE"
case "${DEPLOY_BRANCH:-}" in qa|main);; *) echo "Unsupported DEPLOY_BRANCH (allowed: qa, main)" >&2; exit 2;; esac
cd "${DISTI_DIR:?DISTI_DIR missing}"
git fetch --quiet --prune origin "+refs/heads/${DEPLOY_BRANCH}:refs/remotes/origin/${DEPLOY_BRANCH}"
LOCAL=$(git rev-parse HEAD); REMOTE=$(git rev-parse "origin/$DEPLOY_BRANCH")
printf '{"channel":"%s","local":"%s","remote":"%s","update_available":%s}\n' "$DEPLOY_BRANCH" "$LOCAL" "$REMOTE" "$([[ "$LOCAL" == "$REMOTE" ]] && echo false || echo true)"
