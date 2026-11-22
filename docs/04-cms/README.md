# Complaint Management System

CMS is integrated as a Django domain module and a native client module. The
backend owns complaint, attachment metadata, progress/history, feedback,
announcement, notification-trigger, audit, reopening, and CMS-role-assignment
records. Institutional user identities remain IAM IDs; CMS does not add a user
table or cross-module foreign keys. See [requirement-traceability.md](requirement-traceability.md)
for the UC/BR/WF and CFR/AFR mapping.

## Local development

Prerequisites: Python 3.12, `uv`, Node.js/npm, and Docker Compose. The existing
Compose file starts PostgreSQL and two Redis instances. Fusion IAM remains a
separate service; authenticated UI flows require it on `http://127.0.0.1:8001`.

From the repository root in PowerShell:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[dev]"
Copy-Item .env.example .env
# Set DB_PASSWORD in .env to a local development password before Compose.
docker compose up -d
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_modules
```

Then start the backend and client in separate terminals:

```powershell
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8002
```

```powershell
Set-Location client
npm ci
npm run dev
```

The browser client is at `http://localhost:5173`; the API is at
`http://127.0.0.1:8002/api/v1/cms/`. There are no CMS-created login accounts:
user sign-in and role/permission grants come from Fusion IAM. Register the
generated CMS permission manifest in IAM and grant the documented CMS roles
there. CMS operational appointments (one current handler and one current
supervisor) are separately managed in the CMS Roles view by a system admin.

The background SLA processor can be run once with:

```powershell
.venv\Scripts\python.exe manage.py process_cms_sla
```

For periodic processing, start Celery worker and beat in separate terminals
while the Redis broker from Compose is running:

```powershell
.venv\Scripts\celery.exe -A config.celery:app worker -l info
```

```powershell
.venv\Scripts\celery.exe -A config.celery:app beat -l info
```

Set `CMS_SLA_HOURS_LOW`, `CMS_SLA_HOURS_MEDIUM`, `CMS_SLA_HOURS_HIGH`, and
`CMS_SLA_REMINDER_HOURS` in `.env` to institution-approved values before
enabling periodic processing. Durations are intentionally not prescribed by
the specification. CMS records notification trigger events; email delivery is
the responsibility of the platform notification service.

## Configuration choices

- `CMS_ATTACHMENT_MAX_BYTES`, `CMS_ATTACHMENT_MAX_COUNT`, and
  `CMS_ATTACHMENT_ALLOWED_EXTENSIONS` configure upload constraints. Files are
  stored outside the repository under `CMS_UPLOAD_ROOT`; download routes check
  ownership/permissions.
- `CMS_CLOSURE_VERIFIER` selects `complainant` or `supervisor` closure.
- `CMS_REOPENED_STATUS` selects `submitted` or `in_progress` for an approved
  reopening. The source specification does not define that exact state.
- `ISS-CMS-007` leaves the transition into `in_progress` unspecified;
  handling setup/progress do not silently add that transition.
- `ISS-CMS-009` does not fully define assignment target semantics. Current
  setup associates the authenticated handler as operational owner.
- `ISS-CMS-010` leaves closure without verification unspecified; no such path
  is inferred.

## Checks and production build

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe -m pytest modules\cms\tests -q
Set-Location client
npm run typecheck
npm test
npm run build
```

The repository's standard settings target PostgreSQL. A successful SQLite
test-settings run is useful for fast logic tests but does not validate the
PostgreSQL migration chain. On a machine with Docker/PostgreSQL, use the Compose
steps above and apply the real migrations before considering local deployment
verified.
