#!/usr/bin/env bash
# Deploy a tag. Nothing user-facing changes until every check has passed.
#
#   ops/deploy/deploy.sh platform v1.4.0
#
# The symlink swap is the commit point: before it the old release is still
# serving, after it the new one is. Anything that fails before the swap leaves
# production untouched.
set -euo pipefail

SVC="${1:?usage: deploy.sh <service> <tag>}"
TAG="${2:?usage: deploy.sh <service> <tag>}"

ROOT="${FUSION_ROOT:-/srv/fusion/$SVC}"
VENV="$ROOT/venv"
REPO="${FUSION_REPO:-$ROOT/repo}"
KEEP="${KEEP_RELEASES:-5}"
MIGRATOR_ENV="/etc/fusion/$SVC-migrator.env"

# ln -sfn on an existing symlink is unlink-then-create, so there is a window
# where `current` does not exist. rename(2) has no window.
swap_symlink() {
    ln -sfn "$1" "$2.new"
    "${PYTHON:-python3}" -c 'import os,sys; os.replace(sys.argv[1], sys.argv[2])' \
        "$2.new" "$2"
}

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

[ -d "$REPO/.git" ] || die "no git repository at $REPO (set FUSION_REPO)"
[ -x "$VENV/bin/python" ] || die "no virtualenv at $VENV"
[ -f "/etc/fusion/$SVC.env" ] || die "missing /etc/fusion/$SVC.env"

git -C "$REPO" fetch --tags --prune
SHA="$(git -C "$REPO" rev-parse --short "$TAG^{commit}")" || die "unknown tag $TAG"
REL="$ROOT/releases/$SHA"

PREVIOUS=""
if [ -L "$ROOT/current" ]; then
    PREVIOUS="$(readlink -f "$ROOT/current")"
fi

log "release $SHA from $TAG"
if [ -d "$REL" ]; then
    log "release directory already exists; reusing it"
else
    git -C "$REPO" worktree add --detach "$REL" "$TAG"
fi

log "dependencies"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -e "$REL"

log "client"
if [ -f "$REL/client/package-lock.json" ]; then
    (cd "$REL/client" && npm ci --silent && npm run build --silent)
    [ -f "$REL/client/dist/index.html" ] || die "client build produced no index.html"
fi

log "database roles"
psql -v ON_ERROR_STOP=1 -d "${DB_NAME:-fusion_integrated}" -f "$REL/ops/db/roles.sql"

log "migrations"
# As platform_migrator: the running service has no DDL, so it cannot run these.
if [ -f "$MIGRATOR_ENV" ]; then
    ( set -a; . "/etc/fusion/$SVC.env"; . "$MIGRATOR_ENV"; set +a
      cd "$REL" && "$VENV/bin/python" manage.py migrate --noinput )
else
    printf 'WARNING: %s absent; migrating as the service role.\n' "$MIGRATOR_ENV"
    ( set -a; . "/etc/fusion/$SVC.env"; set +a
      cd "$REL" && "$VENV/bin/python" manage.py migrate --noinput )
fi

log "registry and checks"
( set -a; . "/etc/fusion/$SVC.env"; set +a
  cd "$REL"
  "$VENV/bin/python" manage.py seed_modules
  "$VENV/bin/python" manage.py permission_manifest --check
  "$VENV/bin/python" manage.py check --deploy --fail-level WARNING )

log "swap"
PYTHON="$VENV/bin/python" swap_symlink "$REL" "$ROOT/current"
[ -n "$PREVIOUS" ] && printf '%s\n' "$PREVIOUS" > "$ROOT/previous"

log "restart"
systemctl reload "fusion-$SVC" || systemctl restart "fusion-$SVC"
systemctl restart "fusion-$SVC-worker@default" "fusion-$SVC-worker@notifications" \
                  "fusion-$SVC-worker@reports" 2>/dev/null || true
systemctl is-enabled "fusion-$SVC-beat" >/dev/null 2>&1 \
    && systemctl restart "fusion-$SVC-beat"

log "smoke"
if ! "$REL/ops/deploy/smoke.sh" "$SVC"; then
    printf '\nsmoke test failed — rolling back\n' >&2
    "$REL/ops/deploy/rollback.sh" "$SVC"
    die "rolled back to the previous release"
fi

"$REL/ops/deploy/prune.sh" "$SVC" --keep "$KEEP"

log "deployed $SHA"
printf '\nPermissions are stored by the IAM, not here. If this release added one:\n'
printf '  on the IAM host: manage.py seed_iam_permissions --dry-run\n\n'
