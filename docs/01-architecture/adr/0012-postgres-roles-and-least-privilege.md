# ADR-0012 — Per-service Postgres roles with least privilege

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0002](0002-separate-iam-service-and-database.md), [0007](0007-read-only-erp-access-via-acl.md), [0008](0008-declared-academic-snapshot-for-cpi.md)

## Context

Four processes will connect to one Postgres cluster: the legacy monolith, the sysadmin console,
`fusion-iam` and `fusion-platform`. Two of them (IAM's projector, the platform's academic ACL) reach into
the ERP database, which holds every student record in the institute.

The existing situation is a single superuser-ish account shared by everything, with the password hardcoded
in `development.py`, `production.py`, `docker-compose.yml` and `README.md:272`. The sysadmin console also
runs `pg_restore` in-process and applies raw `ALTER TABLE` statements against the ERP
(`api/views/schema.py:12-52`).

With that arrangement, a SQL-injection bug or a wrong `.delete()` anywhere in ~180k lines of code can drop
academic data. Code review and testing are the only barriers, and there is currently no test suite at all.

Separately, `academics_resultsnapshot` must be immutable — it is the audit record behind every eligibility
decision ([ADR-0008](0008-declared-academic-snapshot-for-cpi.md)). "Immutable by convention" survives
exactly until the first developer who needs to fix a typo.

## Decision

**One Postgres role per service per purpose, granted the minimum that purpose needs.** Privileges are
infrastructure, applied by an idempotent SQL script in `ops/db/roles.sql` and verified at service startup.

| Role | Used by | Grants |
|---|---|---|
| `iam_app` | `fusion-iam` | full DML + DDL on `fusion_system_db` schema `iam`. **No access to `public`.** |
| `iam_erp_projector` | IAM projector task | `SELECT, INSERT, UPDATE, DELETE` on exactly `globals_designation`, `globals_holdsdesignation`, `globals_moduleaccess`; `SELECT, INSERT, UPDATE` on `auth_user`, `globals_extrainfo`. **Nothing else in the ERP.** |
| `platform_app` | `fusion-platform` | full DML on `fusion_nonacad`, **except** `REVOKE UPDATE, DELETE ON academics_resultsnapshot` |
| `platform_migrator` | migrations only | DDL on `fusion_nonacad`. Not used by the running service. |
| `platform_erp_ro` | platform academic ACL | `SELECT` only, on a **named allowlist** of ERP tables |
| `sysops_app` | sysadmin console | unchanged from today, plus a documented note that its restore capability is why IAM does not share its schema |

**Snapshot immutability is a database guarantee:**

```sql
REVOKE UPDATE, DELETE ON academics_resultsnapshot FROM platform_app;
```

An ingest correction re-declares and inserts a new snapshot; it never edits one. Deleting a declaration's
snapshots is a `platform_migrator` operation, i.e. a deliberate, audited, out-of-band act.

**Migrations run as a different role than the service.** `platform_app` has no DDL, so an application bug
cannot alter a table.

**Startup assertions.** Each service asserts its effective privileges at boot and refuses to start on
mismatch — `search_path` is correct, a write to a forbidden table raises, `current_user` is as expected.
A misconfigured deployment fails immediately and loudly rather than at 3 a.m. on the first bad query.

**No credentials in the repository.** Roles have distinct passwords delivered by systemd
`EnvironmentFile` (mode `0640`, owner `root:fusion`), with rotation documented in
[rotate-signing-key.md](../../07-ops/runbooks/rotate-signing-key.md) alongside the signing key.

## Consequences

**Good**

- **The platform cannot corrupt academic data.** Not "should not" — cannot. That guarantee holds through
  bad code, missed reviews and SQL injection.
- The IAM projector's blast radius is three tables. A bug in it cannot delete a student.
- Snapshot immutability survives well-intentioned developers.
- A compromised service yields a narrow credential, not cluster-wide access.
- Startup assertions turn privilege misconfiguration into a fast, obvious failure.
- An audit question — "could this service have written that row?" — is answered from `roles.sql`.

**Bad, and accepted**

- More moving parts: six roles, six passwords, a role script to keep in step with new tables. Mitigated by
  `roles.sql` being idempotent and run on every deploy, plus a CI check that every table in
  `fusion_nonacad` appears in an explicit grant (so a new table cannot silently inherit broad access).
- A forgotten grant surfaces as a runtime `InsufficientPrivilege`. Mitigated by startup assertions and by
  tests running as the **real** application role, not as a superuser — this is the important detail. Tests
  that run as superuser would not catch a missing grant, and would make this entire ADR decorative.
- Adding an ERP table to the ACL allowlist is a two-step change (shadow model + grant). Accepted; the
  friction is the feature.
- `pytest --create-db` needs a role with `CREATEDB`, distinct from the runtime role. Documented in
  [environments.md](../../07-ops/environments.md).

## Alternatives considered

**One shared application role for everything.** Rejected: it is the current arrangement, and it means any
bug anywhere can drop academic data. With no existing test suite, code review would be the only control.

**Row-level security (RLS) instead of table grants.** Rejected: RLS solves per-row visibility, which is a
multi-tenant problem we do not have ([ADR-0011](0011-no-multi-tenancy.md)). Table-level grants match the
actual boundary — service to table — and are far easier to reason about and to audit.

**Enforce read-only via a Django database router with `allow_migrate = False` and discipline in code.**
Rejected as the sole mechanism: a router prevents migrations, not `raw()` or a stray `.save()`. It is used
*in addition*, as defence in depth, but the Postgres grant is the actual control.

**Application-level immutability for snapshots (override `save()`, block `delete()`).** Rejected as the sole
mechanism for the same reason — `queryset.update()` and `bulk_update` bypass `save()` entirely. Also applied
as defence in depth, but the `REVOKE` is what makes it true.

**Postgres triggers to block snapshot mutation.** Equivalent in effect to the `REVOKE` but harder to
discover and to test. `REVOKE` is visible in `\dp` and in one script.

## Verification

- `pytest` runs as `platform_app`. A test asserts `UPDATE` on `academics_resultsnapshot` raises
  `InsufficientPrivilege`.
- A test asserts a write through the `erp` alias raises `InsufficientPrivilege`.
- A test asserts the IAM projector role cannot write `academic_information_student`.
- A CI check asserts every table in `fusion_nonacad` has an explicit grant in `roles.sql`.
- Startup assertions covered by an integration test that boots each service against a correctly and an
  incorrectly configured role, expecting a clean start and a hard failure respectively.
