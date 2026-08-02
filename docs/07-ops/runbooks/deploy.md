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
manage.py check --deploy --fail-level WARNING
ln -sfn releases/<sha> current              # ATOMIC swap
systemctl reload fusion-$SVC                # graceful gunicorn re-exec, in-flight requests finish
systemctl restart fusion-$SVC-worker@* fusion-$SVC-beat
ops/deploy/smoke.sh $SVC || ops/deploy/rollback.sh $SVC     # auto-rollback
ops/deploy/prune.sh $SVC --keep 5
```

**If it stops at `migrate`:** the symlink has **not** moved, so the old code is still serving. Do not rerun
blindly — read the error. A partially-applied migration is a stop-and-escalate condition.

### Frontend

```bash
cd /srv/fusion/shell/releases/<sha>
pnpm install --frozen-lockfile && pnpm turbo build
ln -sfn /srv/fusion/shell/releases/<sha> /srv/fusion/shell/current
```

No service restart — nginx serves the files. `index.html` is `no-store` and assets are `immutable`, so the
next page load picks up the new build without serving a stale shell against deleted chunks.

---

## 3. Verify

```bash
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh "$SVC"
```

```bash
curl -fsS localhost/app/api/iam/v1/readyz              # DB + Redis + JWKS
curl -fsS localhost/app/api/platform/v1/readyz
curl -fsS https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq -e '.keys|length>=1'
curl -fsS https://fusion.iiitdmj.ac.in/app/ | grep -q '<div id="root">'

# The legacy monolith still responds. It shares this nginx config and a new
# location block can shadow "/". Check this on EVERY deploy.
curl -s -o /dev/null -w '%{http_code}\n' https://fusion.iiitdmj.ac.in/api/auth/me   # expect 401
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
