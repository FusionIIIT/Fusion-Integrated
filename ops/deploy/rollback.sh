#!/usr/bin/env bash
# Point `current` back at the previous release and restart.
#
#   ops/deploy/rollback.sh platform            the release recorded by deploy.sh
#   ops/deploy/rollback.sh platform <sha>      a specific one
#
# Code only. A migration is NOT undone, which is why expand-migrate-contract
# spans two releases: the previous code must still run against the new schema.
set -euo pipefail

SVC="${1:?usage: rollback.sh <service> [sha]}"
WANT="${2:-}"
ROOT="${FUSION_ROOT:-/srv/fusion/$SVC}"

die() { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }

# ln -sfn on an existing symlink is unlink-then-create, so there is a window
# where `current` does not exist. rename(2) has no window.
swap_symlink() {
    ln -sfn "$1" "$2.new"
    "${PYTHON:-python3}" -c 'import os,sys; os.replace(sys.argv[1], sys.argv[2])' \
        "$2.new" "$2"
}

if [ -n "$WANT" ]; then
    TARGET="$ROOT/releases/$WANT"
else
    [ -f "$ROOT/previous" ] || die "no $ROOT/previous; pass a sha explicitly"
    TARGET="$(cat "$ROOT/previous")"
fi

[ -d "$TARGET" ] || die "$TARGET does not exist"
[ -f "$TARGET/manage.py" ] || die "$TARGET does not look like a release"

CURRENT="$(readlink -f "$ROOT/current" 2>/dev/null || true)"
[ "$CURRENT" = "$(readlink -f "$TARGET")" ] && die "already on $TARGET"

printf '==> rolling back to %s\n' "$TARGET"
swap_symlink "$TARGET" "$ROOT/current"
[ -n "$CURRENT" ] && printf '%s\n' "$CURRENT" > "$ROOT/previous"

systemctl reload "fusion-$SVC" || systemctl restart "fusion-$SVC"
systemctl restart "fusion-$SVC-worker@default" "fusion-$SVC-worker@notifications" \
                  "fusion-$SVC-worker@reports" 2>/dev/null || true
systemctl is-enabled "fusion-$SVC-beat" >/dev/null 2>&1 \
    && systemctl restart "fusion-$SVC-beat"

printf '==> on %s\n' "$(readlink -f "$ROOT/current")"
printf 'Migrations were not reverted. Check that this code runs against the current schema.\n'
