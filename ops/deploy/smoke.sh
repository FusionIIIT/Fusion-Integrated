#!/usr/bin/env bash
# Is the release actually serving? Run after every deploy, and any time you
# want an answer that is not "the unit is active".
#
#   ops/deploy/smoke.sh platform
set -euo pipefail

SVC="${1:-platform}"
HOST="${SMOKE_HOST:-https://fusion.iiitdmj.ac.in}"
CURL=(curl -fsS --max-time 10)

fails=0
check() {
    local label="$1"; shift
    if "$@" >/dev/null 2>&1; then
        printf '  ok    %s\n' "$label"
    else
        printf '  FAIL  %s\n' "$label"
        fails=$((fails + 1))
    fi
}

status() {
    local want="$1" url="$2"
    local got
    got="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url")"
    [ "$got" = "$want" ]
}

printf 'smoke: %s\n' "$HOST"

check "unit is running"        systemctl is-active --quiet "fusion-$SVC"
check "socket exists"          test -S "/run/fusion/$SVC.sock"
check "/healthz"               "${CURL[@]}" "$HOST/healthz"
check "/readyz (db + cache)"   "${CURL[@]}" "$HOST/readyz"
check "/me refuses anonymous"  status 401 "$HOST/api/v1/me"
check "SPA is served"          bash -c "curl -fsS --max-time 10 '$HOST/' | grep -q 'id=\"root\"'"
check "assets are immutable"   bash -c "curl -fsSI --max-time 10 \"\$(curl -fsS '$HOST/' | grep -o '/assets/[^\"]*\.js' | head -1 | sed \"s|^|$HOST|\")\" | grep -qi 'cache-control: public, immutable'"
check "source maps are hidden" status 404 "$HOST/assets/index.js.map"
check "schema is reachable"    "${CURL[@]}" "$HOST/api/schema"

# A new location block that shadows / would take the ERP down with it, and the
# platform's own checks would still pass.
if [ -n "${LEGACY_URL:-}" ]; then
    check "legacy ERP still answers" status 401 "$LEGACY_URL"
fi

if [ "$fails" -ne 0 ]; then
    printf '\n%d check(s) failed\n' "$fails" >&2
    exit 1
fi
printf '\nall checks passed\n'
