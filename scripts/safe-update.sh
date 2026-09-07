#!/bin/sh
# Branch-aware, fast-forward-only update with automatic application rollback.
set -eu
REMOTE=${DISTI_UPDATE_REMOTE:-origin}
BRANCH=${DISTI_UPDATE_BRANCH:-dev}
HEALTH_URL=${DISTI_UPDATE_HEALTH_URL:-http://localhost:5000/health}
STATE_DIR=${DISTI_UPDATE_STATE_DIR:-.disti-update}
case "$BRANCH" in dev|qa|main) ;; *) echo "Unsupported update channel: $BRANCH" >&2; exit 2;; esac
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "Refusing update: tracked working tree changes" >&2; exit 3; }
mkdir -p "$STATE_DIR"
PREVIOUS=$(git rev-parse HEAD)
git fetch "$REMOTE" "$BRANCH"
TARGET=$(git rev-parse "$REMOTE/$BRANCH")
[ "$PREVIOUS" != "$TARGET" ] || { echo "Already current ($PREVIOUS)"; exit 0; }
git merge-base --is-ancestor "$PREVIOUS" "$TARGET" || { echo "Refusing non-fast-forward update" >&2; exit 4; }
printf '%s\n' "$PREVIOUS" > "$STATE_DIR/previous-commit"
git checkout --detach "$TARGET"
if docker compose build && docker compose up -d --remove-orphans && \
   docker compose exec -T backend python migrate.py && \
   i=0; then
  while [ "$i" -lt 12 ]; do wget -q -O /dev/null "$HEALTH_URL" && exit 0; i=$((i+1)); sleep 5; done
fi
echo "Update health check failed; rolling back to $PREVIOUS" >&2
git checkout --detach "$PREVIOUS"
docker compose build
docker compose up -d --remove-orphans
exit 5
