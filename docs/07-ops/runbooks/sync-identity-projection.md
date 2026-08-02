# Runbook — the identity projection (ERP → IAM)

- **Owner:** platform
- **Applies to:** `Fusion_System_Administrator` (the IAM), app `iam`
- **Related:** [ADR-0014](../../01-architecture/adr/0014-identity-ownership-migration-path.md) ·
  [incident-auth-outage.md](incident-auth-outage.md)

The IAM serves `/me` and `/directory/users` from its own tables in `system_db`, not from the ERP.
A scheduled job keeps that copy current. This runbook covers running it, reading its output, and
what to do when it is stale or wrong.

---

## What the job does

```
ERP (fusionlab / fusion_newui_prod)          IAM (system_db)
  auth_user                                    iam_user
  globals_extrainfo          ── sync ──►       iam_user_designation
  academic_information_student                 iam_designation_module
  globals_holdsdesignation                     iam_sync_run
  globals_moduleaccess
```

One-way and idempotent. Running it twice changes nothing; a half-finished run is safe to repeat.

Two of the three writes **replace wholesale** rather than diff — designations and module grants.
That is deliberate: the security-relevant change is a role being *removed*, and an additive diff
would silently keep a revoked role alive. Both replacements happen inside one transaction.

Users are upserted, never deleted. Someone who disappears from the ERP is marked `is_active=False`,
because placement applications and audit rows reference their id.

---

## Running it

```bash
cd Fusion_System_Administrator/Backend/backend
../venv/bin/python manage.py sync_identity
```

| Flag | Use |
|---|---|
| `--status` | Report freshness and exit. Changes nothing. |
| `--batch-size N` | Rows per bulk write. Default 500. Lower it if the ERP is under load. |
| `--keep-missing` | Skip the deactivation pass. Use when the ERP read is known to be partial. |

Expected output on the live dataset:

```
  users seen         3277
  users written      3277
  designations       3155
  module grants      1
  deactivated        0
  took               0.3s
  succeeded
```

**Schedule:** every 15 minutes is ample. A role change taking up to 15 minutes to reach the platform
is acceptable; see "Making a role change take effect now" below for the exception.

---

## Reading the result

Every run writes an `iam_sync_run` row. `manage.py sync_identity --status` reads the latest one.

| Symptom | Meaning | Action |
|---|---|---|
| `status=failed`, error mentions `OperationalError` | ERP unreachable | Nothing breaks — the projection keeps serving. Fix the ERP; the next run catches up. |
| `deactivated` unexpectedly large | The ERP read returned a partial user list | **Investigate before the next run.** Re-run with `--keep-missing`, then reactivate: `IamUser.objects.filter(erp_user_id__in=[...]).update(is_active=True)`. |
| `users_written` far below ~3,277 | Same as above | As above. |
| `age_seconds` growing without bound | The scheduler is not firing | Check the timer; the projection is stale but still serving. |

A run with `users_seen == 0` does **not** deactivate anyone — an empty read is treated as a failed
read, not as "nobody exists". That guard is covered by
`iam.tests.test_sync.test_an_empty_erp_read_does_not_deactivate_everyone`.

---

## Common tasks

### Making a role change take effect now

A designation granted in the ERP reaches the platform on the next sync. To skip the wait:

```bash
../venv/bin/python manage.py sync_identity
```

The whole run takes well under a second, so there is no partial-sync option and none is needed.

### A password was just reset in the ERP

No action. The first login with the new password fails against the synced hash, falls back to a
live ERP read, succeeds, and re-syncs that one hash. If the ERP is *also* down at that moment the
login fails — correct, since the credential cannot be verified.

### Someone can log in but sees an empty sidebar

Their designation has no module grant. Check in order:

```python
IamUserDesignation.objects.filter(erp_user_id=<id>)          # do they hold a designation?
IamDesignationModule.objects.filter(designation="<name>")     # does it grant anything?
```

If the first is empty for a student, that is expected — students hold no `HoldsDesignation` row in
the ERP, and `build_session()` adds the implicit `student` role. If the second is empty, the grant
is missing in the ERP's `globals_moduleaccess`, which is where it must be fixed.

### The ERP is down and login is failing

It should not be. Confirm the projection is what is serving:

```bash
../venv/bin/python manage.py sync_identity --status
```

If that reports users, the ERP is not on the login path and the fault is elsewhere — see
[incident-auth-outage.md](incident-auth-outage.md).

---

## Verifying the isolation still holds

The whole point of Phase 1 is that a request never needs the ERP. To prove it after a change:

```bash
createdb erp_blackhole                    # valid, empty — the process still boots
DB_NAME=erp_blackhole ../venv/bin/python manage.py runserver 127.0.0.1:8001 --noreload
```

Then log in and call `/me` and `/directory/users`. All three must succeed.

> Point the alias at an **empty** database, not a nonexistent one. A bad DSN kills the process at
> boot (`api/apps.py` introspects `default` for the scheduler, and `runserver` checks migrations),
> which tells you nothing about the request path.

The static half of the same guarantee is enforced in CI by `iam.tests.test_erp_isolation`, which
fails if any view — or any module other than `sync.py` — imports `erp_source`.

---

## Service credentials

Fusion-Integrated reads the directory server-to-server, with no user session behind the call.

```bash
../venv/bin/python manage.py service_token --issue fusion-integrated   # prints the value ONCE
../venv/bin/python manage.py service_token --list
../venv/bin/python manage.py service_token --revoke fusion-integrated
```

Set the printed value as `IAM_SERVICE_TOKEN` in the calling service. It is sent as
`Authorization: Service fsvc_…` — a different scheme from a user session, so the IAM cannot mistake
a machine for a person, and a service credential cannot reach `/me`.

Only a SHA-256 digest is stored. A lost token is re-issued, never recovered. Revocation takes effect
on the next request.
