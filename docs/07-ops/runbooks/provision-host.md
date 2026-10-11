---
owner: platform-lead
status: current
last-reviewed: 2026-08-03
---

# Runbook — provisioning the host, once

Everything [deploy.md](deploy.md) assumes exists. Run this once per host, in
order. **Time:** about an hour, most of it waiting on packages.

Nothing here is idempotent by accident — each step says whether it is safe to
repeat.

---

## 1. Packages and user

```bash
apt update
apt install -y python3.12 python3.12-venv postgresql-16 redis-server nginx \
               nodejs npm git curl
curl -LsSf https://astral.sh/uv/install.sh | sh          # for the venv

adduser --system --group --home /srv/fusion --shell /usr/sbin/nologin fusion
usermod -aG fusion www-data                              # nginx reads the socket
```

`www-data` in the `fusion` group is what makes `RuntimeDirectoryMode=0750` work:
the socket stays unreadable to everyone else.

## 2. Directories

```bash
install -d -o fusion -g fusion -m 0755 /srv/fusion/platform/releases
install -d -o fusion -g fusion -m 0750 /var/lib/fusion/platform/media
install -d -o root   -g fusion -m 0750 /etc/fusion

sudo -u fusion git clone https://github.com/FusionIIIT/Fusion-Integrated.git \
     /srv/fusion/platform/repo
sudo -u fusion uv venv --python 3.12 /srv/fusion/platform/venv
```

`media` is outside the release tree deliberately — a deploy replaces the tree,
and `check_upload_root` refuses to boot if it is inside `BASE_DIR`.

## 3. Two Redis instances

The distinction is load-bearing: an LRU-evicting broker silently drops queued
Celery tasks, which presents as work quietly not happening.

```bash
sed -e 's/^port 6379/port 6379/' -e 's/^# maxmemory .*/maxmemory 512mb/' \
    -e 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' \
    /etc/redis/redis.conf > /etc/redis/redis-cache.conf

sed -e 's/^port 6379/port 6380/' -e 's/^# maxmemory .*/maxmemory 512mb/' \
    -e 's/^# maxmemory-policy .*/maxmemory-policy noeviction/' \
    /etc/redis/redis.conf > /etc/redis/redis-broker.conf

systemctl enable --now redis-server@cache redis-server@broker
redis-cli -p 6380 config get maxmemory-policy      # MUST say noeviction
```

Both bind `127.0.0.1`. Set `requirepass` in each file and put the URLs in the
environment file below.

## 4. Database and roles

```bash
sudo -u postgres createdb fusion_integrated
sudo -u postgres psql -d fusion_integrated \
     -f /srv/fusion/platform/repo/ops/db/roles.sql

sudo -u postgres psql -c "ALTER ROLE platform_app      LOGIN PASSWORD '...';"
sudo -u postgres psql -c "ALTER ROLE platform_migrator LOGIN PASSWORD '...';"
```

`roles.sql` is idempotent and `deploy.sh` re-runs it, so a migration that adds a
table gets its grants without a manual step. The two passwords are set once,
here, and never appear in the repository.

## 5. Environment files

```bash
install -o root -g fusion -m 0640 /dev/null /etc/fusion/platform.env
install -o root -g fusion -m 0640 /dev/null /etc/fusion/platform-migrator.env
```

`/etc/fusion/platform.env` — the running service, as `platform_app`:

```
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=          # python -c 'import secrets;print(secrets.token_urlsafe(64))'
DJANGO_ALLOWED_HOSTS=fusion.iiitdmj.ac.in
DJANGO_CORS_ALLOWED_ORIGINS=https://fusion.iiitdmj.ac.in

DB_NAME=fusion_integrated
DB_USER=platform_app
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=0           # MUST stay 0 if PgBouncer is ever put in front

REDIS_CACHE_URL=redis://:PASS@127.0.0.1:6379/1
REDIS_BROKER_URL=redis://:PASS@127.0.0.1:6380/0

IAM_BASE_URL=http://127.0.0.1:8001
IAM_SERVICE_TOKEN=          # on the IAM: manage.py service_token --issue fusion-integrated
IAM_AUTH_COOKIE_NAME=fusion_session

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=        # a Gmail app password, never an account password

PLACEMENT_UPLOAD_ROOT=/var/lib/fusion/platform/media
PLACEMENT_UPLOAD_INTERNAL_PREFIX=/_protected/
```

`/etc/fusion/platform-migrator.env` — DDL only, read by `deploy.sh` for the
migrate step and by nothing else:

```
DB_USER=platform_migrator
DB_PASSWORD=
```

`IAM_AUTH_COOKIE_NAME` is **not** the default here. The sysadmin console sets a
cookie called `auth_token` at path `/`; on one hostname the two overwrite each
other and each login appears to sign the other out.

`prod.py` requires `DJANGO_SECRET_KEY`, `DB_PASSWORD`, `IAM_SERVICE_TOKEN`,
`PLACEMENT_UPLOAD_ROOT`, `REDIS_CACHE_URL` and `REDIS_BROKER_URL`. A missing one
is a failed boot, not a degraded service.

## 6. Units and nginx

```bash
cd /srv/fusion/platform/repo
cp ops/systemd/fusion-platform.service        /etc/systemd/system/
cp ops/systemd/fusion-platform-worker@.service /etc/systemd/system/
cp ops/systemd/fusion-platform-beat.service   /etc/systemd/system/
systemctl daemon-reload

cp ops/nginx/fusion-platform.conf /etc/nginx/sites-available/
ln -sfn ../sites-available/fusion-platform.conf /etc/nginx/sites-enabled/
certbot --nginx -d fusion.iiitdmj.ac.in
nginx -t && systemctl reload nginx
```

Do **not** enable beat yet. Turning on the drain sends every pending outbox row
at once, and on a restored database those rows name real students — see
[enable-scheduled-work.md](enable-scheduled-work.md), which is the next runbook
after this one.

## 7. First deploy

```bash
sudo -u fusion FUSION_REPO=/srv/fusion/platform/repo \
     /srv/fusion/platform/repo/ops/deploy/deploy.sh platform v1.0.0
```

There is no `current` symlink yet, so nothing is rolled back if this fails —
read the error and fix it. Every subsequent deploy has a previous release to
fall back to.

Then, on the IAM host, seed the permissions this release declares:

```bash
cd /srv/fusion/sysadmin/current/Backend/backend
manage.py seed_iam_permissions --dry-run
manage.py seed_iam_permissions
```

## 8. Verify

```bash
systemctl enable --now fusion-platform
sudo -u fusion /srv/fusion/platform/current/ops/deploy/smoke.sh platform
```

Nine checks, all of which must pass. Then log in as a placement officer and open
one page from the module you care about — the smoke test proves the plumbing, not
that a human can use it.

---

## Firewall

| Port | Exposure |
|---|---|
| 443, 80 | public (80 redirects) |
| 22 | institute network only |
| 5432, 6379, 6380, 8001 | `127.0.0.1` only |
| `/run/fusion/platform.sock` | `fusion:fusion`, mode 0750 |
