#!/bin/sh
set -eu
REMOTE=${DISTI_UPDATE_REMOTE:-origin}
BRANCH=${DISTI_UPDATE_BRANCH:-dev}
case "$BRANCH" in dev|qa|main) ;; *) echo "Unsupported update channel: $BRANCH" >&2; exit 2;; esac
git fetch --quiet "$REMOTE" "$BRANCH"
LOCAL=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse "$REMOTE/$BRANCH")
printf '{"channel":"%s","local":"%s","remote":"%s","update_available":%s}\n' \
  "$BRANCH" "$LOCAL" "$REMOTE_COMMIT" "$([ "$LOCAL" = "$REMOTE_COMMIT" ] && echo false || echo true)"
