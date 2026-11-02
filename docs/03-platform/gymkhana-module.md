# Gymkhana module

The Gymkhana module implements the synchronized GYMKHANA v1.1 baseline in
`modules/gymkhana` and `client/src/modules/gymkhana`. It is independent of ELM
and owns its club, booking, membership, poll, budget, report, and notification
tables. Institute identities remain IAM user IDs; Gymkhana does not create user
rows or cross-module foreign keys.

## Configuration

Set `GYMKHANA_VENUES` to the comma-separated venue names that may be booked.
The default is empty, which intentionally rejects every booking until an
administrator configures the list. Poll `branch` values use the directory
projection's `discipline` field; `*` means all disciplines in the selected
batch.

Set `GYMKHANA_UPLOAD_ROOT` to a persistent directory outside the repository.
Production settings require it. `GYMKHANA_MAX_UPLOAD_BYTES` defaults to 10 MiB.
The module accepts posters and supporting documents through authenticated
multipart requests and serves them only through permission-checked download
routes.

The IAM role designation `Student Admin` receives club establishment and
confirmation permissions. Student permissions include operational capabilities
for potential Club Heads; every club operation independently verifies that the
actor is that club's current coordinator or co-coordinator. Faculty report
access is restricted to the assigned Club Faculty Councillor.

## Implemented baseline

- Student Admin creates clubs as `open` and confirms them as `confirmed`.
- Current Club Heads change leadership and book sessions/events. A locked
venue/date booking guard rejects overlapping bookings across both types.
- Students apply to confirmed clubs once per club; Club Heads approve open
applications to confirmed membership. Rejection and withdrawal are not exposed.
- Club Heads create polls with unique choices, batch/discipline audiences, and a
future expiry. Eligible students can vote once; vote totals are derived from
persisted votes.
- Club Heads submit non-negative budget requests with files; these remain open
for tracking and have no online approval lifecycle.
- Club Heads submit event reports; only the assigned councillor and that club's
current Club Heads can retrieve the report file.
- Activity notices go to confirmed club members. Poll notices go to the
selected directory groups. Notifications are transactionally queued in the
Gymkhana outbox and delivered by Celery or `manage.py
send_gymkhana_notifications`; failed messages can be retried with
`--retry-failed`.

The module does not implement the specification's explicit exclusions:
membership rejection/cancellation, budget approval/rejection, fest budgets,
fest core-team applications, registration forms, generic file tracking,
payments, or attendance.

## Local operations

After setting `GYMKHANA_VENUES` and `GYMKHANA_UPLOAD_ROOT` in `.env`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py permission_manifest
.\.venv\Scripts\python.exe manage.py send_gymkhana_notifications --status
```

The permission manifest must be seeded into IAM before users can see the module.
Celery beat schedules outbox delivery once per minute; the management command
is also available for operations and recovery.
