# ADR-0002 — IAM is its own service; `auth_user` stays in the ERP

- **Status:** accepted, **amended 2026-08-02** — see the amendment note below
- **Date:** 2026-08-01
- **Related:** [0001](0001-modular-monolith-over-microservices.md), [0003](0003-rs256-jwt-access-plus-opaque-refresh.md), [0012](0012-postgres-roles-and-least-privilege.md)

## Context

Authentication and authorization must become central: one login, one role model, one place that answers
"what may this person do". The stated target for that authority is `fusion_system_db`.

Two hard constraints shape how:

**1. ~424 legacy models have foreign keys into `auth_user`.** Relocating that table means editing every
one of them and running the migrations against live production data holding ~3,277 users. That is the
single largest-risk operation available to us, and it buys nothing that a logical reference does not.

**2. `Fusion_System_Administrator/Backend` already owns `fusion_system_db`** — so the tempting move is
to grow IAM inside it. But that project's `default` database alias **is the production ERP database**,
its router defaults everything there, and it runs `pg_restore` in-process as a feature. Identity must
not live inside a process whose normal duties include restoring a database over itself.

There is also a plumbing constraint: two Django projects cannot share one `public.django_migrations`
table without their migration histories colliding.

> ### Amendment, 2026-08-02
>
> The *location* of the IAM changed after this ADR was written. Rather than a new standalone service,
> **Fusion_System_Administrator IS the IAM** — it already owned `fusion_system_db` and already carried
> `managed=False` shadow models for students, faculty, designations and module access, so the identity
> data was largely there. It gained an `iam` Django app providing
> `/api/iam/v1/{auth/login, auth/logout, me, directory/users}`.
>
> Everything else in this ADR stands unchanged, and it is the part that mattered: **`auth_user` rows
> stay in the ERP**, IAM references them by `erp_user_id` with no cross-database foreign key, and the
> projection into `globals_*` is one-way.
>
> One consequence to keep in view: the concern below about identity sharing a process with a tool that
> runs `pg_restore` in-process is now **accepted rather than avoided**. If that ever bites, extracting
> the `iam` app into its own service is mechanical — it has its own app label, its own tables and its
> own URL prefix.
>
> The end-state trajectory is in [ADR-0014](0014-identity-ownership-migration-path.md).

## Decision

**IAM is a new, separate Django service** (`services/iam`), owning **`fusion_system_db` schema `iam`**
via `options: {'-c search_path=iam,public'}`. The sysadmin console keeps schema `public`. Same database,
as required; separate schemas, so the two migration histories never meet.

**`auth_user` rows stay physically in the ERP database.** IAM owns *identity* — credentials, sessions,
MFA, roles, permissions, module grants, audit — and references the ERP row by `erp_user_id`, a plain
integer with a uniqueness constraint. **No cross-database foreign key in either direction.**

IAM projects role and module state **one-way** into `globals_designation`,
`globals_holdsdesignation` and `globals_moduleaccess` so the untouched monolith keeps working, using a
dedicated Postgres role that can write exactly those three tables and nothing else.

User creation projects the `auth_user` row **synchronously** and fails the whole operation if the ERP
write fails — it is the only synchronous projection. Everything else is eventual, under 30 seconds.

## Consequences

**Good**

- Zero migrations against the 424 legacy models. The riskiest possible change is simply not made.
- Identity has its own process boundary, its own Postgres role, its own audit trail, and a blast radius
  that excludes both the ERP and the platform.
- IAM can be restarted, redeployed or rolled back without touching academic services.
- Because access tokens validate locally against JWKS, **IAM being down does not log anyone out** — a
  property worth a great deal during a cutover.
- The console's in-process `pg_restore` cannot touch identity data.

**Bad, and accepted**

- **"A user exists" is a two-step fact** — an `identity_user` row plus a projected `auth_user` row.
  Until the projection lands, the user can log in at `/app/` but the legacy monolith does not know them.
  Mitigated by making that one projection synchronous.
- Referential integrity between IAM and `auth_user` is **application-enforced**, not
  database-enforced. Mitigated by a nightly reconciler that reports dangling `erp_user_id`s, and by
  restore ordering (ERP first, then IAM, then reconcile).
- `search_path` is a connection-level setting; getting it wrong writes IAM tables into `public`.
  Mitigated by asserting the effective `search_path` at startup and failing fast.
- Backups now have an ordering requirement. Documented in
  [restore-from-backup.md](../../07-ops/runbooks/restore-from-backup.md).
- The legacy projection is **lossy** — the ERP schema cannot represent scoped or multi-holder roles
  (hazard H1). This is a property of the legacy schema, not of this decision, but this decision is where
  we accept living with it. See
  [legacy-compatibility-and-erp-projection.md](../../02-iam/legacy-compatibility-and-erp-projection.md).

## Alternatives considered

**Move `auth_user` into `fusion_system_db` and replace 424 FKs with integer columns.** Rejected:
~424 model edits plus 34 apps' migrations against live production data, with no meaningful rollback
once the FKs are dropped. The largest-risk option, for a purity benefit.

**Move `auth_user` to IAM and replicate it back into the ERP via Postgres logical replication.** Genuinely
attractive — the monolith's FKs would resolve against a real local table, and there would be one
authoritative writer. Rejected for now because it couples us to replication topology on a single-VM
deployment, replicated `DELETE`s can violate local FKs on the subscriber, and rollback after cutover is
hard. Recorded as the preferred long-term end state; revisit when the ERP is no longer the FK anchor.

**Grow IAM inside `Fusion_System_Administrator/Backend`.** Rejected: its `default` alias is the
production ERP database and it runs `pg_restore` in-process. Also two Django projects, one
`django_migrations`.

**A separate `fusion_iam` database rather than a schema.** Cleaner isolation, and it was the initial
recommendation — but the requirement was explicitly `fusion_system_db`. A schema honours that while
solving the migration-history collision, so the extra database buys nothing. If IAM is ever extracted
to its own host, promoting the schema to a database is mechanical.

**A third-party identity provider (Keycloak, Ory, Auth0).** Rejected: the role model must project into a
legacy schema with a `unique_together ('working','designation')` constraint and a
column-per-module access table. Every off-the-shelf provider would need that projection written anyway,
plus an operator to run it, plus a migration path for existing password hashes. The seam is preserved
(`identity_credential.algo`, an `amr` claim) so institute SSO can be added later.

## Revisit if

The monolith is retired or its `auth_user` FKs are removed — at which point logical replication or a
straight move becomes both safe and preferable.
