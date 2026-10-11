---
owner: ops
status: authoritative
last-reviewed: 2026-08-01
extends: Fusion_System_Administrator/DEPLOYMENT.md
---

# Deployment Topology

One VM, `fusion-vm`, behind one nginx. This **extends** the proven setup documented in
`Fusion_System_Administrator/DEPLOYMENT.md` — the `fusion-sysadmin.service` unit and its nginx block are the
pattern the new services follow. Existing mounts are untouched.

Note the monolith repo itself carries **no** nginx, gunicorn or systemd artifacts, and its
`docker-entrypoint.sh` runs `manage.py runserver`. The real production configuration lives only in the sibling
repo. This document is where it now lives for the new services.

---

## Layout

```
https://fusion.iiitdmj.ac.in
├── /app/                    → shell static (React)                        NEW
├── /app/api/iam/            → unix:/run/fusion/iam.sock                  NEW
├── /app/api/platform/       → unix:/run/fusion/platform.sock             NEW
├── /app/api/sysops/         → 127.0.0.1:8001                             (existing console)
├── /.well-known/jwks.json   → iam.sock, nginx-cached 10 min              NEW
├── /_protected/             → internal; X-Accel-Redirect target          NEW
├── /sysadmin/               → console client/dist                        unchanged
├── /sysadmin/api/           → 127.0.0.1:8001                             unchanged
└── /                        → 127.0.0.1:8000  (legacy monolith)          unchanged
```

New services listen on **unix sockets**, not TCP ports. Only nginx is exposed, and there is no port for a
misconfigured firewall to leave open.

```
/srv/fusion/
├── iam/{current -> releases/<sha>, releases/, venv/}
├── platform/{current -> releases/<sha>, releases/, venv/}
└── shell/{current -> releases/<sha>, releases/}
/var/lib/fusion/platform/media/         uploads (UUID-keyed)
/run/fusion/                            sockets (systemd RuntimeDirectory)
/etc/fusion/{iam.env, platform.env}     0640 root:fusion
/etc/fusion/credentials/                LoadCredential source, 0400 root
```

`current` is a symlink. Deploy swaps it atomically; rollback swaps it back.

---

## nginx

```nginx
proxy_cache_path /var/cache/nginx/jwks levels=1 keys_zone=jwks:1m max_size=10m inactive=60m;

server {
    listen 443 ssl http2;
    server_name fusion.iiitdmj.ac.in;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options    "nosniff" always;
    add_header X-Frame-Options           "DENY" always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy        "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;

    client_max_body_size 1m;                      # default; multipart routes raise it

    # ── New unified shell ────────────────────────────────────────────────
    location /app/ {
        alias /srv/fusion/shell/current/;
        try_files $uri $uri/ /app/index.html;     # SPA fallback
        location ~* /app/assets/ {                # hashed filenames
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    location = /app/index.html {
        alias /srv/fusion/shell/current/index.html;
        add_header Cache-Control "no-store";      # never cache the entry point
    }

    location /app/api/iam/      { proxy_pass http://unix:/run/fusion/iam.sock:/api/;
                                  include proxy_params; }
    location /app/api/platform/ { proxy_pass http://unix:/run/fusion/platform.sock:/api/;
                                  include proxy_params;
                                  client_max_body_size 6m; }     # document upload cap
    location /app/api/sysops/   { proxy_pass http://127.0.0.1:8001/api/;
                                  include proxy_params; }

    location = /.well-known/jwks.json {
        proxy_pass http://unix:/run/fusion/iam.sock:/api/v1/.well-known/jwks.json;
        include proxy_params;
        proxy_cache jwks;
        proxy_cache_valid 200 10m;
        proxy_cache_use_stale error timeout updating;   # serve stale rather than break auth
    }

    location /_protected/ {                        # X-Accel-Redirect only
        internal;
        alias /var/lib/fusion/platform/media/;
        add_header Content-Disposition "attachment" always;
        add_header X-Content-Type-Options "nosniff" always;
    }

    # ── Existing, unchanged ──────────────────────────────────────────────
    location /sysadmin/api/ { proxy_pass http://127.0.0.1:8001/api/; include proxy_params; }
    location /sysadmin/     { alias /home/fusion/Fusion_System_Administrator/client/dist/;
                              try_files $uri $uri/ /sysadmin/index.html; }
    location /              { proxy_pass http://127.0.0.1:8000; include proxy_params; }
}
```

`proxy_params`:

```nginx
proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID      $request_id;      # picked up by RequestIDMiddleware
proxy_read_timeout 60s;
```

Three details that matter:

- **`index.html` is `no-store`, assets are `immutable`.** Caching the entry point is how users get a stale
  shell that loads chunks the server has already deleted.
- **`proxy_cache_use_stale` on JWKS.** If IAM is briefly down, validators keep working from stale keys rather
  than failing every request — which is the whole point of local validation.
- **`X-Request-ID` from nginx** ties an access-log line to application logs to a Sentry event to the id shown
  on the user's error toast.

---

## systemd

Modelled on the working `fusion-sysadmin.service`, with hardening added.

```ini
# /etc/systemd/system/fusion-platform.service
[Unit]
Description=Fusion Platform (Django/gunicorn)
After=network.target postgresql.service redis-broker.service
Wants=pgbouncer.service

[Service]
Type=notify
User=fusion
Group=fusion
WorkingDirectory=/srv/fusion/platform/current
EnvironmentFile=/etc/fusion/platform.env
Environment=DJANGO_SETTINGS_MODULE=config.settings.prod
LoadCredential=service_key:/etc/fusion/credentials/platform_service_key.pem

ExecStart=/srv/fusion/platform/venv/bin/gunicorn config.wsgi:application \
  --bind unix:/run/fusion/platform.sock \
  --workers 5 --worker-class gthread --threads 4 \
  --max-requests 1000 --max-requests-jitter 100 \
  --timeout 60 --graceful-timeout 30 --keep-alive 5 \
  --access-logfile - \
  --access-logformat '%({X-Request-ID}i)s %(m)s %(U)s %(s)s %(M)sms'

Restart=on-failure
RestartSec=3
RuntimeDirectory=fusion
RuntimeDirectoryMode=0755

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
ReadWritePaths=/var/lib/fusion /run/fusion
MemoryMax=1500M

[Install]
WantedBy=multi-user.target
```

`--max-requests 1000` with jitter recycles workers, which bounds any slow memory growth without anyone
investigating it. `MemoryMax` means a runaway request kills one worker rather than the VM.

`fusion-iam.service` is identical with 3 workers and its own socket, env file and signing key.

### Celery — one templated unit

```ini
# /etc/systemd/system/fusion-platform-worker@.service
[Service]
ExecStart=/srv/fusion/platform/venv/bin/celery -A config worker \
  --queues=%i --hostname=%i@%%h --loglevel=INFO \
  --concurrency=${CONCURRENCY} --prefetch-multiplier=${PREFETCH}
```

```
systemctl enable --now fusion-platform-worker@default        # concurrency 4, prefetch 4
systemctl enable --now fusion-platform-worker@notifications  # concurrency 4, prefetch 4
systemctl enable --now fusion-platform-worker@reports        # concurrency 2, prefetch 1
systemctl enable --now fusion-platform-worker@ingest         # concurrency 1, prefetch 1  ← deliberate
systemctl enable --now fusion-platform-beat                  # exactly ONE host
systemctl enable --now fusion-iam-worker@iam                 # concurrency 2
```

The units are real files rather than snippets: `ops/systemd/fusion-platform-beat.service` and
`ops/systemd/fusion-platform-worker@.service`. Install and enable them with
[runbooks/enable-scheduled-work.md](runbooks/enable-scheduled-work.md), which covers the pre-flight
check that matters most — turning on the drain sends every pending outbox row at once, and on a
seeded or restored database those rows may name real students.

Beat runs on **exactly one host**. Two of them double every tick — two drains of the same outbox,
two stats rebuilds. The schedule itself lives in `modules/<name>/schedule.py` and is merged by
`config/celery.py`, so a module that is not installed contributes no timers.

`ingest` at concurrency 1 with prefetch 1 is a capacity decision, not a default: a 300-student declaration is
roughly 1,500 ERP queries, and serializing it keeps the ERP's pool comfortable even when two batches are
declared minutes apart ([performance-and-capacity.md](../06-crosscutting/performance-and-capacity.md#celery)).

---

## Data services

### PostgreSQL 16

Own disk, own volume. `fusion_system_db` (schemas `iam`, `public`), `fusion_nonacad`,
`fusion_newui_prod`.

Roles from `ops/db/roles.sql`, idempotent, applied on every deploy:
`iam_app` · `iam_erp_projector` · `platform_app` · `platform_migrator` · `platform_erp_ro` · `sysops_app`
([ADR-0012](../01-architecture/adr/0012-postgres-roles-and-least-privilege.md)).

Settings, `statement_timeout` and autovacuum tuning in
[performance-and-capacity.md](../06-crosscutting/performance-and-capacity.md#postgres).

**WAL archiving on**, off-box nightly base backups.

### PgBouncer

`pool_mode=transaction`, `default_pool_size=25`, `max_client_conn=500`. Applications **must** set
`CONN_MAX_AGE=0` and `DISABLE_SERVER_SIDE_CURSORS=True`; a startup assertion refuses to boot otherwise.

### Redis ×2 — the distinction is load-bearing

```
/etc/redis/redis-cache.conf    port 6379   maxmemory 512mb   maxmemory-policy allkeys-lru
/etc/redis/redis-broker.conf   port 6380   maxmemory 512mb   maxmemory-policy noeviction   ← critical
```

An LRU-evicting broker **silently drops queued Celery tasks** — no error, no trace. A startup assertion reads
`CONFIG GET maxmemory-policy` and refuses to start if the broker is not `noeviction`.

Both bind `127.0.0.1` with `requirepass`.

### ClamAV

`clamd` local socket, `freshclam` daily. Uploads are scanned in a Celery task and `scan_status = pending`
**blocks download** until it completes.

---

## Deploy

```bash
# ops/deploy/deploy.sh <service> <tag>
set -euo pipefail
SHA=$(git rev-parse --short "$TAG")
REL=/srv/fusion/$SVC/releases/$SHA

git worktree add "$REL" "$TAG"
uv sync --frozen --project "$REL"
psql -f "$REL/ops/db/roles.sql"                       # idempotent
"$REL/../venv/bin/python" manage.py migrate --noinput  # as platform_migrator
"$REL/../venv/bin/python" manage.py check --deploy --fail-level WARNING
ln -sfn "$REL" /srv/fusion/$SVC/current                # atomic
systemctl reload "fusion-$SVC"                         # graceful worker re-exec
systemctl restart "fusion-$SVC-worker@*" "fusion-$SVC-beat"
ops/deploy/smoke.sh "$SVC" || ops/deploy/rollback.sh "$SVC"
ops/deploy/prune.sh "$SVC" --keep 5
```

Frontend: `pnpm install --frozen-lockfile && pnpm turbo build`, then the same symlink swap.

**Expand → migrate → contract, across two releases.** Never ship a destructive migration in the same release as
the code that stops using the column. `django-migration-linter` blocks unsafe operations in CI, and this is the
operational half of the same rule.

`systemctl reload` re-execs gunicorn workers gracefully — in-flight requests finish.

Runbooks: [deploy.md](runbooks/deploy.md) · [rollback.md](runbooks/rollback.md).

---

## Smoke test

```bash
curl -fsS localhost/app/api/iam/v1/healthz
curl -fsS localhost/app/api/iam/v1/readyz            # DB + Redis + JWKS
curl -fsS localhost/app/api/platform/v1/healthz
curl -fsS localhost/app/api/platform/v1/readyz
curl -fsS https://fusion.iiitdmj.ac.in/.well-known/jwks.json | jq -e '.keys | length >= 1'
curl -fsS https://fusion.iiitdmj.ac.in/app/ | grep -q '<div id="root">'
curl -fsS https://fusion.iiitdmj.ac.in/api/auth/me -o /dev/null -w '%{http_code}' | grep -q 401  # legacy alive
```

The last line matters: every deploy verifies the **legacy monolith still responds**. It shares the nginx
configuration, and a mistake in a new `location` block can shadow `/`.

---

## Firewall

| Port | Exposure |
|---|---|
| 443 | public |
| 80 | public (redirect only) |
| 22 | restricted to the institute network |
| 5432, 6432, 6379, 6380, 8000, 8001 | **`127.0.0.1` only** |
| unix sockets | `fusion:fusion`, mode 0660 |

---

## Backups

| What | Frequency | Retention | Off-box |
|---|---|---|---|
| `pg_basebackup` + WAL | nightly + continuous | 30 days | ✔ |
| `pg_dump` per database | nightly | 14 days | ✔ |
| `/var/lib/fusion/platform/media` | nightly `rsync` | 30 days | ✔ |
| `/etc/fusion/` | on change | — | ✔ (encrypted) |

**Restore order matters** — the ERP first, because IAM holds `erp_user_id` references into it:

```
1. fusion_newui_prod      (the reference target)
2. fusion_system_db       (IAM + console)
3. fusion_nonacad         (platform)
4. manage.py reconcile_erp_projection --mode=enforce
5. manage.py verify_snapshots --full
```

A restored backup contains **full PII**; restore hosts are treated as production
([data-retention-and-privacy.md](../06-crosscutting/data-retention-and-privacy.md)).

**A restore must be performed for real, on a scratch host, in Phase 1**, with the elapsed time written into
[restore-from-backup.md](runbooks/restore-from-backup.md). An untested restore procedure is not a backup
strategy.

---

## The honest limitation

**Everything is on one VM.** No HA, no failover. Accepted deliberately — cost and operational capacity for a
team with no SRE function ([threat-model.md](../06-crosscutting/threat-model.md) A3).

Mitigations are procedural rather than architectural: Postgres on its own disk, WAL archiving, off-box
backups, a tested restore runbook, `MemoryMax` and worker recycling so one bad request cannot take the box
down, and a disk alert at 85% — the one failure mode that corrupts rather than degrades.

Scaling path, in order, none requiring an application rewrite: raise gunicorn workers → move Postgres to its
own host → add a read replica behind `@use_replica` → move Celery to a second host.
