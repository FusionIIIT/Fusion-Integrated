#!/bin/bash
# Assignment 6B (Phase 2) task runner.
# Runs the local model (qwen3.5:4b via Aider) on task files in phase2/tasks/, one at a time,
# and commits each result separately on branch elm-phase2-qwen. It never runs shell commands
# taken from a task: a task only supplies prompt text, files to edit/read, a time limit, and
# optionally fixed tool commands (makemigrations, permission manifest, ruff format/--fix, OpenAPI schema).
# Start: bash ~/elm_specs_md/pilot_kit/phase2/worker.sh      Stop: touch ~/elm_specs_md/pilot_kit/phase2/STOP
set -u

P2="$(cd "$(dirname "$0")" && pwd)"
KIT="$(dirname "$P2")"
REPO="${REPO_OVERRIDE:-$HOME/ELM_MODEL_1}"
BASE="elm-model1-qwen3.5-4b"
BRANCH="elm-phase2-qwen"
MODEL="${MODEL_OVERRIDE:-qwen3.5:4b}"
AIDER_MODEL="${AIDER_MODEL:-ollama_chat/$MODEL}"
AIDER_BIN="${AIDER_BIN:-$(command -v aider || echo /opt/homebrew/bin/aider)}"
# v2: also the import-linter contracts and the two files Fusion's own tools regenerate
# (make permissions -> the catalog doc, make schema -> the OpenAPI file).
ALLOWED='^(modules/leave/|client/src/modules/leave/|config/settings/base\.py$|config/urls\.py$|client/src/app/registry\.ts$|registry/permissions\.json$|docs/02-iam/permission-catalog\.generated\.md$|openapi/fusion-integrated\.v1\.yaml$|\.importlinter$|pilot/)'

mkdir -p "$P2/tasks" "$P2/results" "$P2/logs"
exec > >(tee -a "$P2/logs/worker.log") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
rm -f "$P2/STOP"

cd "$REPO" || { say "missing $REPO"; exit 1; }
[ -z "$(ls .git/*.lock 2>/dev/null)" ] || { say "a git lock file exists in $REPO/.git; stop other git commands first"; exit 1; }

# --- preserve Phase 1 exactly, work on a separate branch -------------------------------
git rev-parse -q --verify refs/tags/phase1-qwen-original >/dev/null || git tag phase1-qwen-original "$BASE"
if git rev-parse -q --verify "refs/heads/$BRANCH" >/dev/null; then git checkout -q "$BRANCH"
else git checkout -q -b "$BRANCH" "$BASE"; fi
grep -qxF '.aider*' .git/info/exclude 2>/dev/null || echo '.aider*' >> .git/info/exclude
[ -z "$(git status --porcelain -- . ':!pilot')" ] || { git status --short; say "working tree not clean (outside pilot/); stopping"; exit 1; }
say "Phase 2 runner on $BRANCH (Phase 1 preserved as tag phase1-qwen-original = $(git rev-parse --short phase1-qwen-original)) | model $AIDER_MODEL"

EVID="pilot/phase2"
mkdir -p "$EVID/prompts"
export DJANGO_SETTINGS_MODULE=config.settings.dev

field() { sed -n "s/^$2: *//p" "$1" | head -1; }   # header field from a task file

safe_path() {  # repo-relative, no parent references, no absolute paths
  case "$1" in /*|*..*|"") return 1 ;; esac
  return 0
}

enforce_scope() {
  git status --porcelain -z -uall | while IFS= read -r -d '' entry; do
    st="${entry:0:2}"; p="${entry:3}"
    case "$st" in R*|C*) IFS= read -r -d '' _src ;; esac
    if ! printf '%s' "$p" | grep -qE "$ALLOWED"; then
      say "[scope] reverting a change outside the ELM scope: $p"
      printf '%s\n' "$p" >> "$EVID/out_of_scope_changes.txt"
      if git cat-file -e "HEAD:$p" 2>/dev/null; then git checkout -q HEAD -- "$p"
      else git rm -q --cached --ignore-unmatch -- "$p" >/dev/null 2>&1; rm -rf -- "./$p"; fi
    fi
  done
}

run_aider() {  # $1 limit seconds, $2 edit format, rest: aider args
  local limit="$1" fmt="$2"; shift 2
  "$AIDER_BIN" --model "$AIDER_MODEL" --edit-format "$fmt" \
    --map-tokens 1024 --timeout 3600 \
    --yes-always --stream --no-pretty --no-fancy-input \
    --no-gitignore --no-auto-commits --no-dirty-commits --no-auto-lint --no-auto-test \
    --no-check-update --analytics-disable --no-show-release-notes --no-show-model-warnings \
    --no-suggest-shell-commands --no-detect-urls --no-restore-chat-history \
    --aiderignore "$KIT/aiderignore" \
    --chat-history-file "$EVID/aider.chat.history.md" \
    --input-history-file "$EVID/aider.input.history" \
    --llm-history-file "$EVID/llm.history.txt" \
    "$@" < /dev/null &
  local pid=$!
  ( sleep "$limit" && { echo "[watchdog] task exceeded ${limit}s; stopping aider"; : > "$P2/.watchdog"
      pkill -INT -P "$pid" 2>/dev/null; sleep 10; pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null; } ) &
  local wd=$!
  wait "$pid"; local rc=$?
  pkill -P "$wd" 2>/dev/null; kill "$wd" 2>/dev/null; wait "$wd" 2>/dev/null
  if [ -f "$P2/.watchdog" ]; then rm -f "$P2/.watchdog"; rc=124; fi
  return $rc
}

run_task() {
  local t="$1" id title fmt edit read limit post body args f r rc t0 secs sha
  id="$(basename "$t" .md)"
  title="$(field "$t" TITLE)"; fmt="$(field "$t" FORMAT)"; edit="$(field "$t" EDIT)"
  read="$(field "$t" READ)"; limit="$(field "$t" LIMIT)"; post="$(field "$t" POST)"
  case "$fmt" in whole|diff) ;; *) fmt=diff ;; esac
  case "$limit" in ''|*[!0-9]*) limit=900 ;; esac
  body="$EVID/prompts/$id.md"
  sed '1,/^---$/d' "$t" > "$body"
  args=""
  for f in $edit; do
    if ! safe_path "$f" || ! printf '%s' "$f" | grep -qE "$ALLOWED"; then
      say "[$id] refusing edit path outside scope: $f"; echo "{\"id\":\"$id\",\"error\":\"edit path outside scope: $f\"}" > "$P2/results/$id.json"; return
    fi
    mkdir -p "$(dirname "$f")"; args="$args --file $f"
  done
  for r in $read; do
    case "$r" in
      kit:*) r="$KIT/${r#kit:}"; case "$r" in *..*) continue ;; esac ;;
      *) safe_path "$r" || continue ;;
    esac
    [ -f "$r" ] && args="$args --read $r" || say "[$id] read file missing: $r"
  done
  say "=== [$id] $title (format $fmt, limit ${limit}s)"
  t0=$(date +%s)
  # shellcheck disable=SC2086
  run_aider "$limit" "$fmt" $args --message-file "$body"; rc=$?
  secs=$(( $(date +%s) - t0 ))
  enforce_scope
  for p in $post; do
    case "$p" in
      makemigrations) .venv/bin/python manage.py makemigrations leave > "$EVID/$id.makemigrations.txt" 2>&1; say "[$id] makemigrations exit $?" ;;
      permissions) .venv/bin/python manage.py permission_manifest > "$EVID/$id.permissions.txt" 2>&1; say "[$id] permission_manifest exit $?" ;;
      ruff) { .venv/bin/ruff format modules/leave; .venv/bin/ruff check --fix modules/leave; } > "$EVID/$id.ruff-fix.txt" 2>&1; say "[$id] ruff format + ruff check --fix (safe fixes only) exit $?" ;;
      schema) .venv/bin/python manage.py spectacular --fail-on-warn --file openapi/fusion-integrated.v1.yaml > "$EVID/$id.schema.txt" 2>&1; say "[$id] spectacular exit $?" ;;
    esac
  done
  enforce_scope
  local touched=0
  for f in $edit; do git status --porcelain -- "$f" | grep -q . && touched=1; done
  [ -n "$edit" ] && [ "$touched" = 0 ] && say "[$id] WARNING: none of the EDIT files changed"
  git add -A . >/dev/null 2>&1
  if git diff --cached --quiet; then sha=""; say "[$id] no changes"
  else
    git commit -q -m "Phase 2 $id: $title" -m "Code changes generated by $MODEL via Aider (local Ollama) from prompt $EVID/prompts/$id.md; committed unedited.${post:+ Post-steps run by the task runner (tools, not the model): $post.}"
    sha="$(git rev-parse --short HEAD)"
  fi
  printf '{"id":"%s","exit":%s,"seconds":%s,"commit":"%s","changed":"%s"}\n' "$id" "$rc" "$secs" "$sha" \
    "$( [ -n "$sha" ] && git show --stat --format= HEAD | tail -1 | sed 's/"//g')" > "$P2/results/$id.json"
  say "=== [$id] done: exit $rc, ${secs}s, commit ${sha:-none}"
}

while true; do
  [ -f "$P2/STOP" ] && { say "STOP file found; runner exiting"; rm -f "$P2/STOP"; break; }
  next=""
  for t in $(ls "$P2/tasks"/*.md 2>/dev/null | sort); do
    [ -f "$P2/results/$(basename "$t" .md).json" ] || { next="$t"; break; }
  done
  if [ -z "$next" ]; then sleep 15; continue; fi
  run_task "$next"
done
