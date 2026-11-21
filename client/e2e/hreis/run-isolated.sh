#!/usr/bin/env bash
set -euo pipefail
# IAM must already be running on 8001 against the synthetic fusion-dev.dump.
repo="$(cd "$(dirname "$0")/../../.." && pwd)"
container="${E2E_DB_CONTAINER:-fusion-integrated-db-1}"
runner_user="${E2E_RUNNER_USER:-$(stat -c '%U' "$repo/.venv")}"
export DB_NAME="hreis_e2e_$(date +%s)_$$"
export HREIS_E2E_SYNTHETIC=1
export DJANGO_SETTINGS_MODULE=config.settings.dev
export E2E_IAM_DIR="$(cd "${E2E_IAM_DIR:-$repo/../Fusion_System_Administrator}" && pwd)"
export DB_PASSWORD="$(docker exec "$container" printenv POSTGRES_PASSWORD)"
export DB_USER="${DB_USER:-fusion_admin}"
backend_pid=""
iam_token_name=""
created=0
output="${E2E_EVIDENCE_DIR:-$(mktemp -d /tmp/hreis-e2e-evidence.XXXXXX)}"
mkdir -p "$output"
as_runner() { if [[ $(id -u) == 0 ]]; then runuser -u "$runner_user" -- "$@"; else "$@"; fi; }
iam_command() {
  (cd "$E2E_IAM_DIR/Backend/backend"
   as_runner env -u DJANGO_SETTINGS_MODULE -u DB_NAME -u DB_PASSWORD -u DB_USER -u DB_HOST -u DB_PORT \
     "$E2E_IAM_DIR/Backend/venv/bin/python" manage.py "$@")
}
cleanup() {
  if [[ -n "$backend_pid" ]]; then kill -TERM -- "-$backend_pid" 2>/dev/null || true; wait "$backend_pid" 2>/dev/null || true; fi
  if [[ "$created" == 1 ]]; then
    docker exec "$container" dropdb -U "$DB_USER" "$DB_NAME"
    echo "Discarded disposable database $DB_NAME"
  fi
  if [[ -n "$iam_token_name" ]]; then
    iam_command service_token --revoke "$iam_token_name"
  fi
}
trap cleanup EXIT
cd "$repo"
if ss -lnt | grep -qE ':8002 |:5173 '; then
  echo "Stop the platform and Vite before running isolated browser tests."
  exit 2
fi
if [[ -z "${IAM_SERVICE_TOKEN:-}" ]]; then
  if [[ "${HREIS_E2E_IAM_SYNTHETIC:-}" != 1 ]]; then
    echo "Provide IAM_SERVICE_TOKEN, or explicitly opt in to a temporary token on synthetic IAM with HREIS_E2E_IAM_SYNTHETIC=1."
    exit 2
  fi
  iam_token_name="hreis-e2e-$DB_NAME"
  token_output="$(iam_command service_token --issue "$iam_token_name")"
  IAM_SERVICE_TOKEN="$(printf '%s\n' "$token_output" | sed -n 's/^[[:space:]]*IAM_SERVICE_TOKEN=//p')"
  unset token_output
  export IAM_SERVICE_TOKEN
  [[ "$IAM_SERVICE_TOKEN" == fsvc_* ]] || { echo "Temporary IAM credential unavailable"; exit 2; }
fi
docker exec "$container" createdb -U "$DB_USER" "$DB_NAME"
created=1
as_runner .venv/bin/python manage.py migrate --noinput > "$output/migrations.log"
as_runner .venv/bin/python manage.py migrate hreis zero --noinput >> "$output/migrations.log"
as_runner .venv/bin/python manage.py migrate --noinput >> "$output/migrations.log"
as_runner .venv/bin/python manage.py seed_modules > "$output/readiness.log"
if as_runner .venv/bin/python manage.py hreis_readiness >> "$output/readiness.log" 2>&1; then
  echo "Empty installation unexpectedly ready"; exit 3
fi
# Register the platform; fixture policies are loaded by Playwright after IAM IDs resolve.
setsid bash -c 'if [[ $(id -u) == 0 ]]; then exec runuser -u "$1" -- .venv/bin/python manage.py runserver 127.0.0.1:8002 --noreload; else exec .venv/bin/python manage.py runserver 127.0.0.1:8002 --noreload; fi' bash "$runner_user" > "$output/backend.log" 2>&1 &
backend_pid=$!
for attempt in $(seq 1 40); do
  code="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8002/api/v1/me || true)"
  [[ "$code" == 401 ]] && break
  sleep 1
done
[[ "$code" == 401 ]] || { echo "Backend unavailable; inspect $output/backend.log"; exit 4; }
cd client
as_runner npm run e2e -- "$@"
cd "$repo"
as_runner .venv/bin/python manage.py hreis_readiness
echo "Browser evidence: $output"
