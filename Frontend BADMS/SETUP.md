# Fusion System Administrator — Windows Setup Guide

Everything you need to get the project running locally on Windows from scratch.

---

## Prerequisites

Install the following before starting. Use the exact versions listed where specified.

| Tool | Version | Download |
|---|---|---|
| Python | 3.11 or 3.12 | https://www.python.org/downloads/ |
| Node.js | 18 LTS or 20 LTS | https://nodejs.org/ |
| PostgreSQL | 14 – 16 | https://www.postgresql.org/download/windows/ |
| Git | Latest | https://git-scm.com/download/win |

> **Important:** During Python installation check **"Add Python to PATH"**.  
> During PostgreSQL installation note the password you set for the `postgres` superuser — you will need it.

---

## 1. Clone the Repository

Open **Command Prompt** or **PowerShell**:

```cmd
git clone <your-repo-url>
cd Fusion_System_Administrator
```

---

## 2. PostgreSQL — Create the Database and User

Open the **psql** shell. You can find it in the Start Menu under **PostgreSQL → SQL Shell (psql)**.  
Press Enter to accept defaults for host/port/dbname, then enter your `postgres` password.  
Choose your own database username and a strong password instead of using a shared example value.

The tool uses **two databases** (see the two-database design in the README):
`fusionlab` holds the managed=False ERP tables, and `fusion_system_db` holds the tool's own
tables (operators/auth + backup logs).

```sql
CREATE USER <DB_USER> WITH PASSWORD '<DB_PASSWORD>';
CREATE DATABASE fusionlab OWNER <DB_USER>;
CREATE DATABASE fusion_system_db OWNER <DB_USER>;
GRANT ALL PRIVILEGES ON DATABASE fusionlab TO <DB_USER>;
GRANT ALL PRIVILEGES ON DATABASE fusion_system_db TO <DB_USER>;
\q
```

> For a realistic dev environment, restore a dump of the ERP database into `fusionlab`
> (its ERP tables are `managed=False` — this tool never creates them).

### Fix authentication method (required on most Windows installs) (Optional)

Find your `pg_hba.conf` file. It is usually at:

```
C:\Program Files\PostgreSQL\<version>\data\pg_hba.conf
```

Open it in Notepad as Administrator. Find the lines that look like:

```
host    all    all    127.0.0.1/32    scram-sha-256
host    all    all    ::1/128         scram-sha-256
```

Make sure they say `scram-sha-256` or `md5` — **not** `ident` or `peer`. If they say `ident`, change them to `md5`:

```
host    all    all    127.0.0.1/32    md5
host    all    all    ::1/128         md5
```

Restart PostgreSQL from **Services** (`Win + R` → `services.msc`) or run in PowerShell as Administrator:

```powershell
Restart-Service -Name postgresql*
```

---

## 3. Backend — Python Setup

All commands below are run from the repo root unless stated otherwise.

### 3.1 Create and activate a virtual environment

```cmd
cd Backend
python -m venv venv
venv\Scripts\activate
```

Your prompt should now start with `(venv)`.

### 3.2 Install Python dependencies

```cmd
pip install -r requirements.txt
pip install apscheduler django-apscheduler
```

### 3.3 Create the `.env` file

Create a single `.env` at the **repository root** (`Fusion_System_Administrator\.env`).
`settings.py` reads it automatically (falling back to `Backend\.env`). All config lives
here — you never edit `settings.py`. Minimal dev config (full reference in §10):

```
SECRET_KEY=dev-secret-change-me
DEBUG=True

# ERP database (default)
DB_NAME=fusionlab
DB_USER=<DB_USER>
DB_PASSWORD=<DB_PASSWORD>
DB_HOST=127.0.0.1
DB_PORT=5432

# Tool database (system_db)
SYSTEM_DB_NAME=fusion_system_db
SYSTEM_DB_USER=<DB_USER>
SYSTEM_DB_PASSWORD=<DB_PASSWORD>
SYSTEM_DB_HOST=127.0.0.1
SYSTEM_DB_PORT=5432

# Email
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
EMAIL_TEST_USER=your_gmail@gmail.com
EMAIL_TEST_MODE=1
```

> **Gmail App Password:** Go to your Google Account → Security → 2-Step Verification → App Passwords.  
> Generate one for "Mail" and paste it as `EMAIL_HOST_PASSWORD`.

### 3.4 Verify the configuration

`settings.py` builds both database connections from the `.env` values above — you do **not**
edit `settings.py`. Confirm everything is wired correctly:

```cmd
cd backend
python manage.py check
```

Expect `System check identified no issues`. A missing `SECRET_KEY`, database credentials, or
email variables will fail fast here with a clear message.

### 3.5 Run migrations

The tool's own tables live in `system_db` (`fusion_system_db`). The ERP tables are
`managed=False`, so migrations only ever build the `system_db` schema:

```cmd
cd backend
python manage.py migrate --database=system_db
```

Expected output ends with something like:

```
Applying django_apscheduler.0009_djangojobexecution_unique_job_executions... OK
```

### 3.6 Create an operator (admin login)

Operators are stored in `system_db`, separate from ERP users:

```cmd
python manage.py createsuperuser --database=system_db
```

Enter a username, email (optional), and password when prompted.  
This is the account you will use to log into the frontend.

### 3.7 Start the backend server

```cmd
python manage.py runserver
```

The backend is now running at **http://127.0.0.1:8000/**  
Leave this terminal open.

---

## 4. Frontend — Node.js Setup

Open a **second** Command Prompt or PowerShell window.

### 4.1 Navigate to the client folder

```cmd
cd Fusion_System_Administrator\client
```

### 4.2 Install dependencies

```cmd
npm install
```

### 4.3 Frontend configuration

No frontend `.env` is needed for local development — `npm run dev` proxies `/api` to the
backend at `http://localhost:8000` (see `client\vite.config.js`). The build's base path is
taken from `APP_BASE_PATH` in the root `.env` (used for sub-path hosting in production).

### 4.4 Start the frontend dev server

```cmd
npm run dev
```

The frontend is now running at **http://127.0.0.1:5173/**  
Open that URL in your browser.

---

## 5. Logging In

1. Go to **http://127.0.0.1:5173/**
2. You will be redirected to the login page.
3. Enter the **username** and **password** you created with `createsuperuser` in step 3.6.
4. Click **Login**.

---

## 6. Project Structure Overview

```
Fusion_System_Administrator/
├── .env                      ← single config file (repo root; git-ignored)
├── Backend/
│   ├── requirements.txt
│   └── backend/
│       ├── manage.py
│       ├── backups/          ← pg_dump files stored here (auto-created; per-DB subfolders)
│       ├── api/              ← Django app (modular, by domain):
│       │   ├── models/       ← erp.py · batches.py · backups.py
│       │   ├── serializers/  ← entities.py · directory.py
│       │   ├── services/     ← batches.py · users.py … (business logic)
│       │   ├── views/        ← directory · roles · users · schema · backups · batches
│       │   ├── urls/         ← per-domain modules + aggregator
│       │   ├── authentication.py · permissions.py · scheduler.py
│       │   └── tests/
│       └── backend/          ← Django project: settings, urls, wsgi, routers (SystemDBRouter)
└── client/
    └── src/
        ├── api/              ← Axios API clients
        ├── components/       ← AppLayout (AppShell), PageHeader, RequireAuth, …
        ├── context/          ← AuthContext, axiosInstance
        ├── pages/            ← Dashboard, UserDirectory, UpcomingBatches, RoleManagement, …
        └── theme.js          ← global Mantine theme
```

---

## 7. Useful Commands (Quick Reference)

### Backend

```cmd
:: Activate venv (run from Backend\)
venv\Scripts\activate

:: Start server
cd backend
python manage.py runserver

:: Make and apply migrations after model changes
python manage.py makemigrations
python manage.py migrate

:: Open Django shell
python manage.py shell

:: Create another admin user
python manage.py createsuperuser
```

### Frontend

```cmd
:: Start dev server
npm run dev

:: Build for production
npm run build

:: Lint
npm run lint
```

### PostgreSQL (psql)

```cmd
:: Connect to the database
psql -U fusion_admin -d fusionlab

:: List all tables
\dt

:: Quit
\q
```

---

## 8. Common Problems and Fixes

### `OperationalError: connection to server at "localhost" failed: FATAL: Ident authentication failed`

PostgreSQL is using `ident` auth. Fix `pg_hba.conf` as described in step 2 and restart the service.

### `django.db.utils.OperationalError: FATAL: password authentication failed for user "fusion_admin"`

The password in `settings.py` does not match what PostgreSQL has. Reset it:

```sql
-- in psql as postgres superuser
ALTER USER fusion_admin WITH PASSWORD 'hello123';
```

### `'venv\Scripts\activate' is not recognized`

You are not inside the `Backend\` folder, or the venv was not created there. Run:

```cmd
cd Fusion_System_Administrator\Backend
python -m venv venv
venv\Scripts\activate
```

### `npm : The term 'npm' is not recognized`

Node.js is not installed or not on PATH. Re-install from https://nodejs.org/ and restart your terminal.

### API calls fail / CORS error in browser console

The SPA calls a relative `/api`, which `npm run dev` proxies to `http://localhost:8000`
(same-origin — no CORS needed). Make sure the **backend is running on port 8000** and you're
using the Vite dev URL (`http://localhost:5173`), not opening the built files directly. If
you changed the proxy target in `client\vite.config.js`, restart the Vite dev server.

### Frontend shows blank page or login loop

Clear `localStorage` in your browser DevTools (`Application → Local Storage → Clear All`) and hard-refresh (`Ctrl + Shift + R`).

### Backup / restore fails with `pg_dump not found`

PostgreSQL's `bin\` folder is not on your PATH. Add it manually:

1. Find the path — usually `C:\Program Files\PostgreSQL\<version>\bin`
2. Open **System Properties → Advanced → Environment Variables**
3. Edit the `Path` variable under **System variables** and add the path above
4. Restart your terminal

---

## 9. Scheduled Backups

Backup schedules are managed from the **Backup → Schedules** page in the UI. No external cron daemon is needed — APScheduler runs inside the Django process and re-registers all active schedules on every server restart.

Backup dump files are stored in `Backend\backups\` and are automatically pruned according to your retention setting.

---

## 10. Environment Variables Reference

All configuration lives in **one git-ignored `.env` at the repository root**. `settings.py`
reads the root `.env` first and falls back to `Backend/.env`; the Vite build reads
`APP_BASE_PATH` from the same file. Real process environment variables override both.

| Variable | Required | Description | Example |
|---|---|---|---|
| `SECRET_KEY` | yes | Django secret key | `<random>` |
| `DEBUG` | no | `True` for dev; `False` enables Secure cookies + HTTPS headers | `True` |
| `ALLOWED_HOSTS` | prod | Comma-separated hosts | `fusion.iiitdmj.ac.in` |
| `APP_BASE_PATH` | prod | Sub-path the SPA is served under (also the Vite `base`) | `/sysadmin/` |
| `AUTH_COOKIE_PATH` | prod | Path scope for the auth cookie | `/sysadmin` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | yes | ERP database (`default`) | `fusionlab` / … |
| `SYSTEM_DB_NAME` / `SYSTEM_DB_USER` / `SYSTEM_DB_PASSWORD` / `SYSTEM_DB_HOST` / `SYSTEM_DB_PORT` | yes | Tool database (`system_db`) | `fusion_system_db` / … |
| `EMAIL_HOST_USER` | yes | Gmail address (SMTP) | `you@gmail.com` |
| `EMAIL_HOST_PASSWORD` | yes | Gmail App Password | `abcd efgh ijkl mnop` |
| `EMAIL_TEST_USER` | yes | Address for test emails / batch-mail test mode | `you@gmail.com` |
| `EMAIL_PORT` / `EMAIL_USE_TLS` | no | SMTP port / TLS | `587` / `True` |
| `EMAIL_TEST_MODE` / `EMAIL_TEST_COUNT` / `EMAIL_TEST_ARRAY` | no | Batch-mail test controls (`mail-batch`) | `1` / `1` / `"[]"` |
| `TOKEN_TTL_HOURS` | no | Auth-token lifetime | `12` |
| `REDIS_URL` | no | Shared login-throttle counter across workers | `redis://127.0.0.1:6379/0` |
| `BACKUP_ENCRYPTION_KEY` | no | Fernet key to encrypt backup dumps at rest | `<fernet key>` |

> **Note:** `reset_password` emails the real user regardless of `EMAIL_TEST_MODE`; the
> test-mode variables only affect the batch-mail (`mail-batch`) flow.

The frontend needs no `.env` of its own for local dev — `npm run dev` serves the SPA and
proxies `/api` to the backend at `http://localhost:8000` (see `client/vite.config.js`).
`APP_BASE_PATH` (root `.env`) controls the build's base path.
