# Fusion System Administrator

A standalone admin console for the **Fusion ERP** at PDPM IIITDM Jabalpur. It manages ERP
data (users, roles/module-access, upcoming batches, archives) and operates the tool's own
subsystems (operator auth, database backup/restore/scheduling/health) — hosted alongside
the main Fusion app at **`/sysadmin/`**.

- **Backend:** Django 5 / Django REST Framework, PostgreSQL, gunicorn.
- **Frontend:** React 18 + Vite, Mantine v7 (AppShell layout, theme, dashboard).
- **Auth:** httpOnly cookie token; operators are a **separate** account set from ERP users.

## Two-database design

| Alias | Database | Contents |
|---|---|---|
| `default` | `fusionlab` (dev) / `fusion_newui_prod` (prod) | Managed=False **ERP** tables, shared with main Fusion (users, designations, batches, students). |
| `system_db` | `fusion_system_db` | This tool's **own** tables: operator auth/sessions/tokens and backup/restore/schedule/health logs. |

Routing is handled by `Backend/backend/backend/routers.py` (`SystemDBRouter`). Keeping the
tool's data in `system_db` means a `fusion_newui_prod` restore can't wipe the operators or
the log of restores, and operators stay independent of the 3000+ ERP users.

## Backend architecture

Modular Django app (`Backend/backend/api/`), organized by domain:

```
api/
  models/       erp.py · batches.py · backups.py            (+ __init__ re-exports)
  serializers/  entities.py · directory.py
  services/     batches.py (allocation/validation/excel) · users.py · ...
  views/        directory · roles · users · schema · backups · batches   (thin)
  urls/         per-domain modules + __init__ aggregator
  authentication.py · permissions.py · scheduler.py
```

Views are thin (parse request → call a service → return response); business logic lives in
`services/`. Security policy is centralized in `permissions.py` (`ReadOnly = IsAuthenticated`,
`Privileged = IsAdminUser`); every mutating/privileged endpoint is staff-only.

## Features

- **User Directory** — search students / faculty / staff with filters.
- **Upcoming Batches** — admit and manage UG / PG / PhD batches: batch table with seats,
  Excel bulk upload + manual entry, per-batch student roster. (Writes the shared ERP DB.)
- **User Management** — add faculty/staff, reset passwords (emails the user, stores only the
  hash), bulk import/export.
- **Role Management** — create roles, manage module access, edit a user's designations.
- **Archive Management** — archive students and faculty.
- **Backup Management** — on-demand and scheduled dual-database backups (per-DB subfolders,
  human-readable filenames, optional at-rest encryption), restore, and DB health checks.

## Docs

- [SETUP.md](SETUP.md) — local development setup.
- [DEPLOYMENT.md](DEPLOYMENT.md) — production deployment & update runbook.
- [api-documentation.md](api-documentation.md) — REST API reference.

## Quick start (development)

```bash
# Backend
cd Backend/backend
python -m venv ../venv && source ../venv/bin/activate
pip install -r ../requirements.txt
python manage.py migrate --database=system_db          # build the tool's own tables
python manage.py createsuperuser --database=system_db  # create an operator
python manage.py runserver

# Frontend (new terminal)
cd client
npm install
npm run dev
```

Config lives in a single git-ignored `.env` at the repo root (falls back to `Backend/.env`).
See [SETUP.md](SETUP.md) for the full walkthrough and environment-variable reference.

## Password emailing (batch)

`POST /api/users/mail-batch/` (client: User Management → Mail Batch) generates/updates
passwords for a batch year and emails them to each user; only the password **hash** is
stored. Failed sends are logged to `Backend/backend/failed_emails/failed_emails.txt`.
Email behaviour is controlled by the `EMAIL_*` variables in `.env` (see SETUP.md).
