# Deployment

The System Administrator runs **beside the main Fusion app on the same domain**, behind
an nginx reverse proxy, at a sub-path — in production: **`https://fusion.iiitdmj.ac.in/sysadmin/`**.
It needs no change to the main Fusion app.

Two moving parts:

- **Backend** — a Django/DRF app served by **gunicorn on `127.0.0.1:8001`**, managed by the
  **systemd unit `fusion-sysadmin`**. It talks to two Postgres databases (see below).
- **Frontend** — a **static Vite build** (`client/dist/`) served by nginx under `/sysadmin/`.

The mount path is a single knob — the Vite `base` (`APP_BASE_PATH`). The React Router
`basename`, the API base URL, and the auth-cookie path all derive from it.

---

## Production topology (fusion-vm)

```
https://fusion.iiitdmj.ac.in/sysadmin/        -> client/dist  (nginx static)
https://fusion.iiitdmj.ac.in/sysadmin/api/    -> 127.0.0.1:8001  (gunicorn, systemd: fusion-sysadmin)

Databases (Postgres):
  fusion_newui_prod   default    -> managed=False ERP tables (shared with main Fusion)
  fusion_system_db    system_db  -> this tool's own tables (operators/auth, backup logs)
```

- Repo checkout: `~/Fusion_System_Administrator`  ·  venv: `~/Fusion_System_Administrator/venv`
- Single root `.env` at `~/Fusion_System_Administrator/.env` (git-ignored — never edit tracked source on the server).
- Prod tracks the **`theDRB123/Fusion_System_Administrator`** remote via `git pull origin main`.

---

## Updating an existing deployment (the common case)

Run on the prod server. The golden rule:

> **Backend code changed → restart `fusion-sysadmin`. Frontend code changed → rebuild `client/dist`.**
> A `git pull` alone changes neither the running gunicorn nor the served static bundle.

```bash
cd ~/Fusion_System_Administrator

# 0. Note the current commit for rollback
git rev-parse HEAD

# 1. Pull (ensure the commit is on the branch prod tracks — see "Fork sync" below)
git pull origin main
# If it complains about local edits to settings.py / vite.config.js (old hard-coded
# config), discard them — all config now lives in the root .env:
#   git checkout -- Backend/backend/backend/settings.py client/vite.config.js

# 2. Backend — ONLY if backend files changed
source venv/bin/activate
cd Backend/backend
python manage.py check                 # expect "0 issues"
#   NO ERP migrations: the batch/ERP models are managed=False over existing tables.
#   If the tool's OWN tables changed: python manage.py migrate --database=system_db
sudo systemctl restart fusion-sysadmin
cd ../..

# 3. Frontend — ONLY if client files changed
cd client
npm ci
npm run build                          # reads APP_BASE_PATH=/sysadmin/ from the root .env
# If nginx serves a COPIED dist path (not client/dist directly), sync it:
#   rsync -a --delete dist/ /var/www/fusion-admin/dist/
cd ..
```

Then **hard-refresh** the browser (Ctrl/Cmd+Shift+R) — the old `index.html` may be cached.

**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://fusion.iiitdmj.ac.in/sysadmin/login   # 200
sudo systemctl status fusion-sysadmin --no-pager
```
If an API call fails after a backend change, check the log: `sudo journalctl -u fusion-sysadmin -n 80 --no-pager`.

### Fork sync
Pushes go to the `vikrantwiz02` fork; prod pulls from `theDRB123`. A commit is only
deployable once it's on **`theDRB123/main`** — merge/sync it there first (the usual PR),
or pull the fork directly on prod:
`git pull https://github.com/vikrantwiz02/Fusion_System_Administrator.git main`.

### Rollback
```bash
cd ~/Fusion_System_Administrator
git reset --hard <the HEAD you noted in step 0>
sudo systemctl restart fusion-sysadmin          # if backend was affected
cd client && npm ci && npm run build            # if frontend was affected (+ rsync)
```

---

## First-time setup

### 1. Databases
Both databases must exist on the Postgres server, owned by the app DB user:
```sql
CREATE DATABASE fusion_newui_prod OWNER fusion_admin;   -- or reuse the main Fusion ERP DB
CREATE DATABASE fusion_system_db  OWNER fusion_admin;
```
`fusion_newui_prod` holds the ERP tables (`managed=False` — shared with main Fusion, not
created by this tool). `fusion_system_db` holds this tool's own tables.

### 2. Root `.env`
Single `.env` at the repository root (git-ignored). `settings.py` reads it (root first,
then `Backend/.env`); the Vite build reads `APP_BASE_PATH` from it too. Real process env
vars still override.

```ini
DEBUG=False
SECRET_KEY=<strong random secret>
ALLOWED_HOSTS=fusion.iiitdmj.ac.in
APP_BASE_PATH=/sysadmin/          # sub-path the SPA is served under (also used by the build)
AUTH_COOKIE_PATH=/sysadmin        # scope the auth cookie to the mount path

# Main ERP database (managed=False models read/write here)
DB_NAME=fusion_newui_prod
DB_USER=fusion_admin
DB_PASSWORD=...
DB_HOST=127.0.0.1
DB_PORT=5432

# This tool's own database (operators/auth + backup/restore/schedule/health logs)
SYSTEM_DB_NAME=fusion_system_db
SYSTEM_DB_USER=fusion_admin
SYSTEM_DB_PASSWORD=...
SYSTEM_DB_HOST=127.0.0.1
SYSTEM_DB_PORT=5432

# Email (used by reset-password and batch mailing) — required
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_TEST_USER=...

# Optional
# TOKEN_TTL_HOURS=12
# REDIS_URL=redis://127.0.0.1:6379/0     # shared login-throttle across gunicorn workers
# BACKUP_ENCRYPTION_KEY=<Fernet key>     # encrypt backup dumps at rest
```
`DEBUG=False` auto-enables `Secure` cookies + HTTPS security headers. The SPA and API are
same-origin, so no CORS config is needed.

### 3. Backend
```bash
cd Backend/backend
python manage.py migrate --database=system_db          # build system_db schema (tool tables)
python manage.py createsuperuser --database=system_db  # create an operator account
```
Run it under systemd — `/etc/systemd/system/fusion-sysadmin.service`:
```ini
[Unit]
Description=Fusion System Administrator (Django/gunicorn)
After=network.target postgresql.service

[Service]
User=fusion
Group=fusion
WorkingDirectory=/home/fusion/Fusion_System_Administrator/Backend/backend
ExecStart=/home/fusion/Fusion_System_Administrator/venv/bin/gunicorn backend.wsgi:application --bind 127.0.0.1:8001 --workers 3
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fusion-sysadmin
```
Requirements on the box: `pg_dump`/`pg_restore` on `PATH` (backup/restore), and both
databases present.

### 3b. The identity sync — install the timer, it is not built in

Nothing in this service schedules `sync_identity`; the APScheduler here runs backups
only. Without a timer the projection freezes, and the symptom is not an error — it is
a designation assigned this morning that never reaches any service.

```bash
sudo cp Backend/ops/systemd/fusion-iam-*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fusion-iam-sync.timer fusion-iam-freshness.timer
systemctl list-timers 'fusion-iam-*'
```

- **`fusion-iam-sync.timer`** — every 10 minutes, `Persistent=true` so it catches up
  after downtime rather than leaving an hour-old projection.
- **`fusion-iam-freshness.timer`** — every 15 minutes, runs
  `sync_identity --status --max-age 1800`, which **exits 1** past the limit. Point the
  monitor at `systemctl is-failed fusion-iam-freshness`: a dead sync timer is silent
  otherwise, and silence is the failure mode that costs you a day.

A run that would deactivate more than 2% of the people it just read is **refused**,
because a truncated ERP read looks exactly like a mass resignation. The unit fails,
the next tick retries, and nobody is locked out. If the departure is genuine, run it
once by hand with `--force-deactivate`.

Two things do not need the timer, by design: a **password** changed in the ERP works
at the next login (the hash check falls back to a live read and repairs the copy), and
a **designation** is re-read on login as well. The timer is what keeps everyone else's
rows current between logins.

### 4. Frontend build
```bash
cd client
npm ci
npm run build                 # emits client/dist/ referencing /sysadmin/assets/…
```

### 5. nginx — add to the existing `fusion.iiitdmj.ac.in` server block
```nginx
# System Administrator — API
location /sysadmin/api/ {
    proxy_pass http://127.0.0.1:8001/api/;      # strips the /sysadmin prefix
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# System Administrator — SPA (static build)
location /sysadmin/ {
    alias /home/fusion/Fusion_System_Administrator/client/dist/;
    try_files $uri $uri/ /sysadmin/index.html;
}
# ...existing main Fusion locations (/, /accounts/, /admin/, /api, ...) unchanged
```
Live at **`https://fusion.iiitdmj.ac.in/sysadmin/login`**.

---

## Notes

- **Same-origin is required for the auth cookie.** The httpOnly `auth_token` cookie is only
  sent when the SPA and API share an origin — the nginx layout above guarantees that. Don't
  split them across hosts/ports.
- **Operators are separate from ERP users.** Admin login authenticates against
  `fusion_system_db` (operators you create), not the ERP `auth_user`. See `backend/routers.py`.
- **`reset_password` emails the real user** and stores only the password hash — never plaintext.
- **Upcoming Batches writes the shared ERP DB** (`fusion_newui_prod`): batches/students
  created there are the same records the main Fusion uses.
- **To use a different mount path**, change `APP_BASE_PATH`, `AUTH_COOKIE_PATH`, and the two
  nginx `location` blocks consistently.
