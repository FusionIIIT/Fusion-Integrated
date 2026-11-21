#!/usr/bin/env bash
# Remove old release directories, keeping the newest N.
#
#   ops/deploy/prune.sh platform --keep 5
#
# Never removes the live release or the rollback target, whatever --keep says.
set -euo pipefail

SVC="${1:?usage: prune.sh <service> [--keep N]}"
KEEP=5
[ "${2:-}" = "--keep" ] && KEEP="${3:?--keep needs a number}"

ROOT="${FUSION_ROOT:-/srv/fusion/$SVC}"
REPO="${FUSION_REPO:-$ROOT/repo}"
[ -d "$ROOT/releases" ] || { printf 'nothing to prune\n'; exit 0; }

CURRENT="$(readlink -f "$ROOT/current" 2>/dev/null || true)"
PREVIOUS=""
[ -f "$ROOT/previous" ] && PREVIOUS="$(readlink -f "$(cat "$ROOT/previous")" 2>/dev/null || true)"

# ls -dt sorts newest first on both GNU and BSD; find -printf is GNU only.
releases=()
while IFS= read -r line; do releases+=("${line%/}"); done < <(ls -dt "$ROOT"/releases/*/ 2>/dev/null)

kept=0
for rel in "${releases[@]}"; do
    real="$(readlink -f "$rel")"
    if [ "$real" = "$CURRENT" ] || [ "$real" = "$PREVIOUS" ] || [ "$kept" -lt "$KEEP" ]; then
        kept=$((kept + 1))
        continue
    fi
    printf 'removing %s\n' "$rel"
    # A worktree must be removed through git, or .git/worktrees keeps the entry.
    if [ -d "$REPO/.git" ] && git -C "$REPO" worktree list --porcelain | grep -qx "worktree $real"; then
        git -C "$REPO" worktree remove --force "$rel"
    else
        rm -rf "$rel"
    fi
done

[ -d "$REPO/.git" ] && git -C "$REPO" worktree prune
printf 'kept %d release(s)\n' "$kept"
