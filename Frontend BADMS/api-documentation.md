# Fusion System Administrator — API Reference

## Introduction

This document describes the HTTP API exposed by the Fusion System Administrator
backend. The backend is a Django REST Framework (DRF) application. Every route
below is mounted under the `/api/` prefix (the project `urls.py` includes
`api.urls` at `api/`, and adds `login`/`logout` directly under `api/`).

Unless noted otherwise, request and response bodies are JSON. Endpoints that
return files (CSV exports, sample templates) respond with `text/csv`.

---

## Authentication

Authentication uses DRF token authentication via a custom
`api.authentication.CookieTokenAuthentication` class (configured as the only
`DEFAULT_AUTHENTICATION_CLASSES` entry in `settings.REST_FRAMEWORK`).

- **Cookie (browser / SPA):** `POST /api/login/` sets an **httpOnly** cookie
  named `auth_token` containing the token key. Because it is httpOnly, the SPA
  never reads the token from JavaScript; the browser sends it automatically on
  same-site requests (`SameSite=Lax`, `Secure` whenever `DEBUG` is off).
- **Header (API clients / scripts / tests):** send
  `Authorization: Token <key>` (the key is also returned in the login response
  body). The cookie is tried first; the header is the fallback.
- **Token expiry:** tokens expire after `TOKEN_TTL_HOURS` (default **12h**).
  An expired token is deleted and rejected; each login rotates the token
  (the previous one is deleted and a fresh one issued).

**Permissions**

- The default permission class is `IsAuthenticated` — every endpoint requires a
  valid token unless it explicitly opts out (only `POST /api/login/` is public,
  plus the plain-Django `GET /api/download-sample-csv/` template view).
- **Privileged (staff operator, `IsAdminUser`) endpoints** — the caller's
  operator account must have `is_staff = True`:
  - `POST /api/users/reset_password/`
  - `GET  /api/update-globals-db/`
  - `POST /api/upcoming-batches/create/`
  - `DELETE|POST /api/upcoming-batches/<id>/delete/`
  - `POST /api/upcoming-batches/save-students/`
  - `POST /api/upcoming-batches/add-student/`
  - `DELETE /api/backups/<uuid>/delete/`
  - `POST /api/backups/<uuid>/restore/`
  - `DELETE /api/schedules/<uuid>/delete/`

> **Two-database design.** Operators (the accounts that log into this admin
> tool) live in a separate `system_db` database, distinct from the ERP users
> (students / faculty / staff) that most of these endpoints read and write in
> the managed Fusion ERP database. An operator is not an ERP user.

---

## Auth

### `POST /api/login/`
Obtain an auth token. Public (no auth required); rate-limited to **5 requests/min**.

Request body:
```json
{ "username": "operator1", "password": "••••••••" }
```
Response `200 OK` (also sets the `auth_token` httpOnly cookie):
```json
{ "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" }
```

### `POST /api/logout/`
Revoke the caller's token and clear the auth cookie. Requires authentication.

Response `200 OK`:
```json
{ "message": "Logged out." }
```

---

## Directory

Read-only ERP directory lookups. All require authentication.

### `GET /api/departments/`
List all departments (ordered by id).

Response `200 OK`:
```json
[
  { "id": 26, "name": "Finance and Accounts" },
  { "id": 28, "name": "Academics" }
]
```

### `GET /api/batches/`
List batches, one row per distinct year (`Batch.objects.distinct('year')`).

Response `200 OK`:
```json
[
  {
    "id": 89,
    "name": "B.Tech",
    "year": 2022,
    "running_batch": true,
    "total_seats": 60,
    "curriculum_options": null,
    "discipline": 2,
    "curriculum": 2
  }
]
```

### `GET /api/programmes/`
List all programmes (ordered by id).

Response `200 OK`:
```json
[
  { "id": 1, "category": "UG", "name": "B.Tech", "programme_begin_year": 2010 }
]
```

### `GET /api/users/`
List ERP users of a given type, with optional filters.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | One of `student`, `faculty`, `staff`. Missing/invalid → `400`. |
| `gender` | string | No | Filter by sex (applies to all three types). |
| `programme` | string | No | Student only. |
| `batch` | integer | No | Student only (batch year). |
| `discipline` | string | No | Student only (discipline name). |
| `category` | string | No | Student only. |
| `designation` | string | No | Faculty / staff only (role name). |

Response `200 OK` for `type=student`:
```json
[
  {
    "id": "22BCS502",
    "username": "22BCS502",
    "full_name": "John Doe",
    "user_type": "student",
    "programme": "B.Tech",
    "discipline": "Computer Science and Engineering",
    "batch": 2022,
    "curr_semester_no": 6,
    "category": "GEN",
    "gender": "M"
  }
]
```
For `type=faculty`, each item is
`{ id, username, full_name, user_type, department, designations: [...], gender }`.
For `type=staff`, each item is
`{ id, username, full_name, user_type, gender, designations: [...] }`.

Error (missing/invalid type) `400 Bad Request`:
```json
{ "error": "Invalid or missing user type." }
```

---

## Role Management

All require authentication. A "role" is a `GlobalsDesignation`; module access is
a `GlobalsModuleaccess` row keyed by the designation name.

### `GET /api/get-user-roles-by-username/`
Fetch a user and their designations by username.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | Username (case-insensitive). |

Response `200 OK`:
```json
{
  "user": {
    "id": 1,
    "username": "22BCS502",
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "22bcs502@iiitdmj.ac.in",
    "is_staff": false,
    "is_active": true,
    "date_joined": "2019-11-24T14:23:49.431661Z"
  },
  "roles": [
    { "id": 7, "name": "student", "full_name": "Computer Science and Engineering",
      "type": "academic", "basic": true, "category": "student", "dept_if_not_basic": null }
  ]
}
```
Errors: `400` (missing `username`), `404` (user not found / user has no designations).

### `PUT /api/update-user-roles/`
Replace a user's set of designations: roles not in the request are removed, new
ones added.

Request body:
```json
{ "username": "22BCS502", "roles": ["student", { "name": "co-ordinator" }] }
```
(`roles` accepts plain strings or objects with a `name` key.)

Response `200 OK`:
```json
{ "message": "User roles updated successfully." }
```
Errors: `400` (missing `username`/`roles`), `404` (unknown user or role name).

### `GET /api/view-roles/`
List every role (`GlobalsDesignation`).

Response `200 OK`:
```json
[
  { "id": 48, "name": "Dean_s", "full_name": "Computer Science and Engineering",
    "type": "academic", "basic": false, "category": null, "dept_if_not_basic": null }
]
```

### `POST /api/view-designations/`
List roles filtered by category and `basic` flag.

Request body (both optional; defaults shown):
```json
{ "category": "student", "basic": true }
```
Response `200 OK`: array of role objects (same shape as `view-roles`).

### `POST /api/create-role/`
Create a role and seed a `GlobalsModuleaccess` row (all module flags `false`).

Request body:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique short name. |
| `full_name` | string | Yes | Full name. |
| `type` | string | Yes | e.g. `academic` / `administrative`. |
| `basic` | boolean | No | Defaults to `false`. |
| `category` | string | No | e.g. `student` / `faculty` / `staff`. |

Response `201 Created`:
```json
{
  "role": { "id": 60, "name": "prof", "full_name": "Professor",
            "type": "academic", "basic": true, "category": "faculty",
            "dept_if_not_basic": null },
  "modules": {
    "id": 101, "designation": "prof",
    "program_and_curriculum": false, "course_registration": false,
    "course_management": false, "other_academics": false, "spacs": false,
    "department": false, "examinations": false, "hr": false, "iwd": false,
    "complaint_management": false, "fts": false, "purchase_and_store": false,
    "rspc": false, "hostel_management": false, "mess_management": false,
    "gymkhana": false, "placement_cell": false, "visitor_hostel": false,
    "phc": false, "inventory_management": false
  }
}
```
Error `400 Bad Request`: serializer validation errors.

### `PUT` / `PATCH` `/api/modify-role/`
Update an existing role, looked up by `name`. `PUT` is a full update; `PATCH`
is partial.

Request body:
```json
{ "name": "prof", "full_name": "Professor", "type": "academic", "basic": true, "category": "faculty" }
```
Response `200 OK`: the updated role object. Errors: `400` (no `name` / invalid
data), `404` (role not found).

### `GET /api/get-module-access/`
Get the module-access flags for a role.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `designation` | string | Yes | Role name. |

Response `200 OK`:
```json
{
  "id": 4, "designation": "student",
  "program_and_curriculum": true, "course_registration": true,
  "course_management": true, "other_academics": true, "spacs": true,
  "department": true, "examinations": false, "hr": false, "iwd": false,
  "complaint_management": true, "fts": false, "purchase_and_store": false,
  "rspc": false, "hostel_management": true, "mess_management": true,
  "gymkhana": true, "placement_cell": true, "visitor_hostel": true,
  "phc": true, "inventory_management": false
}
```
Errors: `400` (no `designation`), `404` (not found).

### `PUT /api/modify-roleaccess/`
Update module-access flags for a role. Partial update — send only the flags to
change, keyed by `designation`.

Request body:
```json
{ "designation": "student", "examinations": true, "hr": false }
```
Response `200 OK`: the full updated module-access object (same shape as
`get-module-access`). Errors: `400` (no `designation` / invalid), `404` (not found).

---

## User Management

Create/maintain ERP users. All require authentication;
`reset_password` additionally requires a **staff operator**
(`IsAdminUser`).

### `POST /api/users/add-faculty/`
Create a faculty user across the auth, extra-info, holds-designation and faculty
tables. Password is generated server-side.

Request body:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username (lower-cased; email becomes `<username>@iiitdmj.ac.in`). |
| `first_name` | string | Yes | |
| `last_name` | string | Yes | |
| `sex` | string | Yes | `M` / `F` (first letter used). |
| `designation` | string | Yes | Designation id/name for holds-designation. |
| `title`, `dob`, `address`, `phone`, `department` | — | No | Defaults applied when omitted (`Mr.`/`Ms.`, `2025-01-01`, `NA`, `9999999999`, CSE dept). |

Response `201 Created`:
```json
{
  "message": "Faculty added successfully",
  "auth_user_data": { "username": "testfaculty", "email": "testfaculty@iiitdmj.ac.in", "is_staff": false, "...": "..." },
  "extra_info_user_data": { "id": "testfaculty", "user_type": "faculty", "department": 51, "...": "..." },
  "holds_designation_user_data": { "designation": "3", "user": 5443, "working": 5443 },
  "globals_faculty_data": { "id": "testfaculty" }
}
```
Error `400 Bad Request` (missing fields):
```json
{ "error": "Missing required fields.", "missing_fields": ["designation"] }
```

### `POST /api/users/add-staff/`
Same request/response shape as `add-faculty` (required fields: `username`,
`first_name`, `last_name`, `sex`, `designation`), except the auth user is
created with `is_staff = true` and the final key is `globals_staff_data`.

Response `201 Created`:
```json
{
  "message": "Staff added successfully",
  "auth_user_data": { "username": "teststaff", "is_staff": true, "...": "..." },
  "extra_info_user_data": { "id": "teststaff", "user_type": "staff", "...": "..." },
  "holds_designation_user_data": { "designation": "46", "user": 5442, "working": 5442 },
  "globals_staff_data": { "id": "teststaff" }
}
```

### `POST /api/users/reset_password/` — *staff operator only*
Reset a user's password to a new random value and email the new credentials to
the user's registered address. The plaintext password is **never** returned in
the response.

Request body:
```json
{ "username": "22BCS502" }
```
Response `200 OK`:
```json
{ "message": "Password reset successfully. The new password has been emailed to the user." }
```
Errors: `404` (user not found), `500` (unexpected error). A failed email does
**not** fail the reset — the password has already been changed.

### `POST /api/users/import/`
Bulk-import users from a CSV file (multipart upload). Field name: `file`.
Expected columns: `username, first_name, last_name, sex, category, father_name,
mother_name, batch, programme, title, dob, address, phone_no, department`
(rows with fewer than 9 columns are skipped). Successfully created users are
emailed their credentials.

Response `201 Created`:
```json
{
  "message": "42 users created successfully.",
  "created_users": [ { "id": 5444, "username": "23BCS501", "email": "23bcs501@iiitdmj.ac.in", "...": "..." } ],
  "skipped_users_count": 2,
  "skipped_users_csv": "username,first_name,...\n..."
}
```
(`skipped_users_csv` is present only when some rows failed.) Errors: `400` (no
file / non-CSV file).

### `GET /api/users/export/`
Export all users as CSV. Responds with `Content-Type: text/csv`
(`attachment; filename="users_export.csv"`). Columns: `username, first_name,
last_name, email, is_staff, is_superuser`.

### `POST /api/users/mail-batch/`
Email credentials to every student in a batch.

Request body:
```json
{ "batch": 2022 }
```
Response `200 OK`:
```json
{ "message": "Mail sent to whole batch successfully." }
```
Error `500`: `{ "error": "<detail>" }`.

### `GET /api/download-sample-csv/`
Download the blank CSV template (header row only) used for bulk import. Plain
Django view returning `text/csv` (`attachment; filename="sample.csv"`) — not
DRF-authenticated. Header row: `username, first_name, last_name, sex, category,
father_name, mother_name, batch, programme, title, dob, address, phone_no,
department`.

---

## Schema

### `GET /api/update-globals-db/` — *staff operator only*
Run idempotent schema migrations / fix-ups against the ERP `globals_*` tables
(adds missing columns such as `basic`, `category`, `inventory_management`,
rebuilds id sequences and the single-basic-designation trigger, and back-fills
category values).

Response `200 OK`:
```json
{ "success": true, "message": "Database updates completed successfully." }
```
On failure the same endpoint returns `{ "success": false, "error": "<detail>" }`.

---

## Upcoming Batches

Manage incoming-batch configuration and the staged student upload
(`StudentBatchUpload`). Read endpoints require authentication; create / delete /
save-students / add-student require a **staff operator** (`IsAdminUser`). These
endpoints return `JsonResponse` bodies with a top-level `success` flag; service
errors return `{ "success": false, "message": ... }` with a `4xx`/`5xx` status.

### `GET /api/upcoming-batches/disciplines/`
List disciplines.
```json
{ "success": true, "disciplines": [ { "id": 2, "name": "Computer Science and Engineering", "acronym": "CSE" } ] }
```

### `GET /api/upcoming-batches/curriculums/`
List working curriculums.
```json
{ "success": true, "curriculums": [ { "id": 2, "name": "CSE UG", "version": "1.0", "programme": "B.Tech" } ] }
```

### `GET /api/upcoming-batches/sync/`
Summarise all running batches with seat counts and curriculum status.
```json
{
  "success": true,
  "batches": [
    { "batch_id": 89, "name": "B.Tech", "discipline": "CSE",
      "discipline_name": "Computer Science and Engineering", "year": 2025,
      "total_seats": 60, "filled_seats": 0, "available_seats": 60,
      "curriculum": "CSE UG", "curriculum_id": 2, "status": "READY" }
  ],
  "total_batches": 1
}
```

### `POST /api/upcoming-batches/create/` — *staff operator only*
Create a running batch.

Request body:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `programme` | string | Yes | Batch name, e.g. `B.Tech` (alias `batch_name`). |
| `discipline` | integer | Yes | Discipline id. |
| `year` | integer | Yes | Batch year (alias `batchYear`). |
| `total_seats` | integer | Yes | Alias `totalSeats`. |
| `curriculum` | integer | No | Working-curriculum id (alias `curriculum_id`). |
| `specialization` | string | No | Echoed back only. |

Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "id": 90, "programme": "B.Tech",
    "discipline": "Computer Science and Engineering", "disciplineAcronym": "CSE",
    "year": 2025, "total_seats": 60, "totalSeats": 60, "specialization": "",
    "running_batch": true, "curriculum": "CSE UG", "curriculum_id": 2
  },
  "message": "Batch created successfully with curriculum: CSE UG"
}
```
Service errors `400`: missing fields, invalid discipline/curriculum id, or a
duplicate batch (`validation_error: "duplicate_batch"`).

### `DELETE` / `POST` `/api/upcoming-batches/<batch_id>/delete/` — *staff operator only*
Delete a batch (only if it has no students).

Response `200 OK`:
```json
{ "success": true,
  "message": "Successfully deleted batch \"B.Tech CSE 2025\".",
  "deleted_batch": { "id": 90, "name": "B.Tech", "discipline": "CSE", "year": 2025 } }
```
Errors: `404` (not found); `400` with `validation_error: "batch_has_students"`
and `student_count` when the batch still contains students.

### `GET /api/upcoming-batches/<batch_id>/students/`
List staged students for a batch.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `specialization` | string | No | PG batches: filter by specialization. |

Response `200 OK`:
```json
{
  "success": true,
  "batch": { "id": 89, "name": "B.Tech", "discipline": "CSE", "year": 2025, "curriculum": "CSE UG" },
  "students": [
    { "id": 1, "name": "John Doe", "roll_number": "22BCS502",
      "institute_email": "22bcs502@iiitdmj.ac.in", "branch": "Computer Science and Engineering",
      "category": "GEN", "gender": "Male", "reported_status": "NOT_REPORTED",
      "status_display": "Not Reported", "source": "excel_upload", "...": "..." }
  ],
  "total_students": 1
}
```
Error `404`: batch not found.

### `POST /api/upcoming-batches/save-students/` — *staff operator only*
Bulk-save an array of staged students (from an Excel/JSON upload). Validates
that a working curriculum and active batches (with curriculums assigned) exist
for the resolved academic year, de-duplicates, validates phone numbers, and
allocates each student to a batch.

Request body:
```json
{
  "students": [ { "Name": "John Doe", "Institute Roll Number": "22BCS502",
                  "Discipline": "Computer Science and Engineering", "Gender": "Male",
                  "Category": "GEN", "Mobile No": "9876543210" } ],
  "programme_type": "ug",
  "academic_year": "2025-26",
  "skip_duplicates": false,
  "duplicate_check_fields": ["jeeAppNo", "rollNumber", "instituteEmail"]
}
```
(Student records accept both the human "Excel header" keys shown above and
camelCase keys such as `rollNumber`, `instituteEmail`, `phoneNumber`.)

Response `200 OK`:
```json
{
  "success": true,
  "data": {
    "successful_uploads": 1, "failed_uploads": 0, "skipped_duplicates": 0,
    "validation_errors": 0, "skipped_invalid": 0, "total_processed": 1, "original_count": 1
  },
  "summary": { "total_students": 1, "branch_counts": { "BCS": 1 }, "programme": "UG" },
  "errors": [],
  "message": "1 students uploaded successfully."
}
```
Service errors `400`: no students, missing curriculum/batch
(`validation_error: "missing_curriculum"` / `"missing_batch"` /
`"batch_missing_curriculum"`), or an invalid year format.

### `POST /api/upcoming-batches/add-student/` — *staff operator only*
Add a single staged student. Same curriculum/batch preconditions as
save-students.

Request body (snake_case shown; camelCase aliases like `fname`, `jeeAppNo`,
`phoneNumber` are mapped automatically). Required: `name`, `father_name`,
`mother_name`, `branch`, `gender`, `category`, `pwd`, `address`.
```json
{
  "name": "John Doe", "father_name": "Father", "mother_name": "Mother",
  "branch": "Computer Science and Engineering", "gender": "Male",
  "category": "GEN", "pwd": "NO", "address": "NA",
  "programme_type": "ug", "academic_year": "2025-26"
}
```
Response `200 OK`:
```json
{
  "success": true,
  "data": { "student_id": 12, "roll_number": null,
            "institute_email": "", "name": "John Doe" },
  "message": "Student John Doe added successfully."
}
```
Service errors `400`: missing required fields, duplicate JEE application number,
or missing curriculum/batch preconditions.

---

## Backups & Restores

Backup/restore/schedule/health-check management for the two managed PostgreSQL
databases (main ERP DB — `fusionlab` in dev / `fusion_newui_prod` in prod — and
the tool's own `system_db`). Both databases can be **backed up**; only the main
ERP database can be **restored** into (the system DB is backup-only). All
endpoints require authentication; `delete`/`restore`/schedule-`delete` require a
**staff operator** (`IsAdminUser`).

### `GET /api/backups/`
List backup records. Also syncs any orphaned `.dump` files on disk into records.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `db_name` | string | No | Filter by database name. |

Response `200 OK`:
```json
[
  { "id": "3f0c…", "db_name": "fusionlab",
    "created_at": "2026-07-13T02:00:00+00:00", "status": "success",
    "size_bytes": 10485760, "duration_ms": 4200,
    "file_name": "fusionlab__2026-07-13_02-00-00__3f0c….dump",
    "error_message": null, "encrypted": false }
]
```

### `POST /api/backups/create/`
Start a `pg_dump` in a background thread; returns immediately with status
`in_progress`.

Request body:
```json
{ "db_name": "fusionlab" }
```
(`db_name` optional — defaults to the main ERP DB; an unknown name → `400`.)

Response `201 Created`:
```json
{ "id": "3f0c…", "db_name": "fusionlab", "created_at": "2026-07-13T02:00:00+00:00",
  "status": "in_progress", "size_bytes": null, "duration_ms": null }
```

### `GET /api/backups/<uuid>/`
Poll a single backup record.

Response `200 OK`:
```json
{ "id": "3f0c…", "db_name": "fusionlab", "created_at": "2026-07-13T02:00:00+00:00",
  "status": "success", "size_bytes": 10485760, "duration_ms": 4200,
  "file_path": "/…/backups/fusionlab/…​.dump", "error_message": null }
```
Error `404`: backup not found.

### `DELETE /api/backups/<uuid>/delete/` — *staff operator only*
Delete a backup record and its dump file from disk.

Response `200 OK`: `{ "message": "Backup deleted." }`.
Errors: `404` (not found), `409` (cannot delete an `in_progress` backup).

### `POST /api/backups/<uuid>/restore/` — *staff operator only*
Restore the main ERP database from a successful backup. Runs `pg_restore` in a
background thread and creates a `RestoreRecord`.

Response `201 Created`:
```json
{ "restore_id": "9ab2…", "backup_id": "3f0c…", "db_name": "fusionlab",
  "started_at": "2026-07-13T03:00:00+00:00", "status": "in_progress",
  "source_backup_created_at": "2026-07-13T02:00:00+00:00" }
```
Errors `400`/`404`: backup not found, backup not a `success`, dump file missing,
or the backup's `db_name` is not restorable (e.g. the system database).

### `GET /api/restores/`
List restore records (optional `?db_name=` filter).

Response `200 OK`:
```json
[
  { "id": "9ab2…", "db_name": "fusionlab", "source_backup_id": "3f0c…",
    "source_backup_created_at": "2026-07-13T02:00:00+00:00",
    "started_at": "2026-07-13T03:00:00+00:00",
    "finished_at": "2026-07-13T03:00:05+00:00",
    "status": "success", "duration_ms": 5000, "error_message": "" }
]
```

### `GET /api/restores/<uuid>/`
Poll a single restore record (same shape as an item above). Error `404`: not found.

### `GET /api/schedules/`
List all backup schedules.

Response `200 OK`:
```json
[
  { "id": "d41d…", "db_name": "fusionlab", "enabled": true, "frequency": "daily",
    "hour": 2, "minute": 0, "day_of_week": null, "day_of_month": null,
    "cron_expression": "", "retain_last_n": 7,
    "last_run_at": null, "next_run_at": "2026-07-14T02:00:00+00:00",
    "created_at": "…", "updated_at": "…" }
]
```

### `POST /api/schedules/save/`
Create or update the schedule for a `db_name` (upsert), then (de)registers the
APScheduler job.

Request body:
```json
{ "db_name": "fusionlab", "frequency": "daily", "enabled": true,
  "hour": 2, "minute": 0, "day_of_week": null, "day_of_month": null,
  "cron_expression": "", "retain_last_n": 7 }
```
(`frequency` one of `daily`/`weekly`/`monthly`/`custom`; for `custom` the
`cron_expression` must have exactly 5 fields.)

Response `200 OK` (or `201 Created` when newly created): the serialized schedule.
Errors `400`: missing `db_name`, invalid cron expression, or trigger build error.

### `POST /api/schedules/preview/`
Preview the next 5 run times for schedule parameters without saving anything.

Request body:
```json
{ "frequency": "weekly", "hour": 2, "minute": 0, "day_of_week": 0 }
```
Response `200 OK`:
```json
{ "next_runs": ["2026-07-20T02:00:00+00:00", "2026-07-27T02:00:00+00:00", "..."] }
```
Error `400`: invalid trigger parameters.

### `POST /api/schedules/<uuid>/toggle/`
Flip a schedule's `enabled` flag.

Response `200 OK`: the updated schedule object. Error `404`: not found.

### `DELETE /api/schedules/<uuid>/delete/` — *staff operator only*
Delete a schedule and deregister its APScheduler job.

Response `200 OK`: `{ "message": "Schedule deleted." }`. Error `404`: not found.

### `GET /api/health-checks/`
Return health-check records from the last 90 days.

Query parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `db_name` | string | No | Defaults to the main ERP DB name. |

Response `200 OK`:
```json
[
  { "id": "…", "db_name": "fusionlab", "checked_at": "2026-07-13T02:00:00+00:00",
    "status": "success", "response_time_ms": 3, "error_message": null }
]
```

### `POST /api/health-checks/run/`
Ping a database now and record the result.

Request body:
```json
{ "db_name": "fusionlab" }
```
(`db_name` optional — defaults to the main ERP DB.)

Response `200 OK`:
```json
{ "id": "…", "db_name": "fusionlab", "checked_at": "2026-07-13T02:00:00+00:00",
  "status": "success", "response_time_ms": 3, "error_message": null }
```

### `GET /api/db-info/`
Metadata for every managed database (used to list backup targets). Also syncs
orphaned dump files.

Response `200 OK`:
```json
[
  { "id": "fusionlab", "name": "fusionlab (PostgreSQL)", "engine": "postgresql",
    "host": "localhost", "port": "5432", "size_bytes": 52428800,
    "backup_count": 3, "last_backup_at": "2026-07-13T02:00:00+00:00",
    "status": "online", "restorable": true }
]
```
(The system database appears here too, with `"restorable": false`.)
