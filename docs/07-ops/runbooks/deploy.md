# Runbook — Deploy

**Time:** 3–5 min per service. **Risk:** low (atomic symlink swap, automated rollback).

```bash
SVC=platform          # platform | iam | shell
TAG=v1.4.0
```

---

## 1. Pre-flight

```bash
gh run list --branch main --limit 1                 # CI green on this commit
gh api repos/:owner/:repo/commits/$TAG/status | jq -r .state    # expect "success"
```

- [ ] CI green
- [ ] On staging ≥ 24 h (≥ 72 h if it touches auth)
- [ ] Migration timed on staging; duration recorded in the PR
- [ ] No destructive migration in the same release as the code that stops using the column
      (**expand → migrate → contract across two releases**)
- [ ] Auth-touching changes are behind a flag defaulting to **off**
- [ ] Someone else is reachable for 30 minutes

```bash
ssh fusion-vm
df -h /var/lib/postgresql /srv                      # need >15% free
systemctl is-active fusion-iam fusion-platform fusion fusion-sysadmin
```

---

## 2. Deploy

```bash
sudo -u fusion /srv/fusion/ops/deploy/deploy.sh "$SVC" "$TAG"
```

What it does, in order:

```
git worktree add /srv/fusion/$SVC/releases/<sha> $TAG
uv sync --frozen
psql -f ops/db/roles.sql                    # idempotent; new tables get grants
manage.py migrate --noinput                 # as platform_migrator (runtime role has no DDL)
manage.py seed_modules                      # module registry and nav from registry.py
manage.py check --deploy --fail-level WARNING
ln -sfn releases/<sha> current              # ATOMIC swap
systemctl reload fusion-$SVC                # graceful gunicorn re-exec, in-flight requests finish
systemctl restart fusion-$SVC-worker@* fusion-$SVC-beat
ops/deploy/smoke.sh $SVC || ops/deploy/rollback.sh $SVC     # auto-rollback
ops/deploy/prune.sh $SVC --keep 5
```

**If it stops at `migrate`:** the symlink has **not** moved, so the old code is still serving. Do not rerun
blindly — read the error. A partially-applied migration is a stop-and-escalate condition.

### Permissions — on the IAM host, after the swap

The platform declares which permissions exist and which designations may hold
them; the IAM stores that. A release that adds a permission is not finished
until the IAM has seeded it, and until then the endpoint guarding on it answers
403 and its nav item is missing:

```bash
cd /srv/fusion/sysadmin/current/Backend/backend
manage.py seed_iam_permissions --dry-run     # reads /srv/fusion/platform/current/registry/permissions.json
manage.py seed_iam_permissions
```

Always read the dry run first — it prints every grant it would revoke, and a
revoke is a live loss of access. The command refuses a manifest whose version it
does not recognise and one that lists no modules, so a truncated file cannot
wipe the table. Only rows for modules the manifest names are touched.

### Frontend

Nothing separate to do: `deploy.sh` runs `npm ci && npm run build` inside the release, and nginx serves
`current/client/dist`. The symlink swap publishes both halves at once, so the API and the bundle that calls
it are never a release apart.

No service restart — nginx serves the files. `index.html` is `no-store` and assets are `immutable`, so the
next page load picks up the new build without serving a stale shell against deleted chunks.

---

## 3. Verify

```bash
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh "$SVC"
```

`smoke.sh` covers all of it: the unit is running, the socket exists, `/healthz` and `/readyz` answer,
`/api/v1/me` refuses an anonymous caller, the SPA is served, assets are `immutable`, source maps are **not**
published, and `/api/schema` is reachable. It exits non-zero on any failure, which is what `deploy.sh` keys
its automatic rollback off.

Set `LEGACY_URL` and it also asserts the legacy monolith still responds — it shares this nginx and a new
`location` block can shadow `/`, which the platform's own checks would not notice:

```bash
LEGACY_URL=https://fusion.iiitdmj.ac.in/api/auth/me \
  sudo -u fusion /srv/fusion/platform/current/ops/deploy/smoke.sh platform
```

Then, for 10 minutes:

```bash
journalctl -u "fusion-$SVC" -f | grep -E '"level":"(error|critical)"'
```

Dashboards: error rate flat · p95 within budget · `outbox_lag_seconds` < 60 · `celery_queue_depth` draining.

Manual: log in at `/app/`, confirm the sidebar renders, open one page from the module you changed.

---

## 4. If something is wrong

```bash
sudo -u fusion /srv/fusion/ops/deploy/rollback.sh "$SVC"
```

→ [rollback.md](rollback.md). Do this early. A rollback costs 60 seconds; debugging in production costs more.

---

## Notes

- **`reload`, not `restart`**, for gunicorn — workers re-exec gracefully and in-flight requests finish.
- Celery workers **are** restarted, because a code change must not run under a stale worker. Tasks are
  `acks_late`, so in-flight work is redelivered rather than lost.
- `roles.sql` runs on every deploy so a new table cannot silently inherit broad access — CI already fails if a
  table has no explicit grant.
- 5 releases are kept. Rollback beyond that needs a fresh checkout.
- Deploying `iam` does **not** log anyone out: access tokens validate locally against cached JWKS, and nginx
  serves stale JWKS through a restart.
