# ADR-0014 — The projection becomes the source of truth

- **Status:** accepted
- **Date:** 2026-08-02
- **Related:** [0002](0002-separate-iam-service-and-database.md), [0013](0013-no-cross-module-foreign-keys.md)
- **Answers:** "if academic is eventually rebuilt outside the monolith and also sits behind
  Fusion_System_Administrator, identity would just live in `system_db` — so what is the projection
  actually for?"

## Context

Today the ERP owns identity. Measured on the live database:

| Table | Inbound FK constraints |
|---|---|
| `auth_user` | **126** |
| `academic_information_student` | **83** |
| `globals_extrainfo` | **50** |
| `globals_faculty` | **17** |

**276 constraints**, in a codebase with no test suite. Moving those tables into `system_db` today
would break every one of them at once, against live production. It would also create two writers for
one fact, because the ERP still *creates* users through admissions, registration and batch
onboarding.

So the near-term answer is a projection: IAM keeps its own copy of identity in `system_db`, synced
one-way from the ERP, and serves `/me` and `/directory/users` from that copy instead of reading the
ERP on every request.

The reasonable objection is that this looks like scaffolding. If the academic side is eventually
rebuilt as its own application — a sibling of Fusion-Integrated, also sitting behind
Fusion_System_Administrator — then identity would naturally live in `system_db` and the projection
would appear to have been a detour.

## Decision

**Build the projection as the destination, not as scaffolding.** The IAM tables that hold identity
today are the same tables that will hold it when the monolith is gone. What changes over time is the
*direction of the sync* and *who writes first* — never the schema, and never the consumers.

### Phase 1 — ERP writes, IAM projects — **implemented**

```
ERP  auth_user, extrainfo, student, faculty     ← source of truth, 276 FKs intact
      │  one-way sync   (iam/sync.py, scheduled)
      ▼
IAM  identity tables in system_db               ← serves /me and /directory
      │
      ▼
Fusion-Integrated                               ← holds only user_id references
```

IAM stops reading the ERP on the hot path. The ERP remains authoritative for creation.

**What was built** (in `Fusion_System_Administrator`, app `iam`):

| Piece | File | Note |
|---|---|---|
| Identity tables | `iam/models.py` | `IamUser`, `IamUserDesignation`, `IamDesignationModule`, `SyncRun`. Not named `*_cache` — they are the destination, not scaffolding. |
| The ERP boundary | `iam/erp_source.py` | The only ERP-aware module. Flattens `auth_user` + `extrainfo` + `student`, resolves designations on `working_id`, and turns the one-boolean-column-per-module table into rows. |
| The projection | `iam/sync.py` | One-way, idempotent, batched. Designations and grants replace wholesale — an additive diff would keep a revoked role alive. |
| Serving | `iam/services.py` | Reads IAM tables only. |
| Service credentials | `iam/models.py`, `iam/authentication.py` | `Authorization: Service fsvc_…`, hashed at rest. The platform's server-to-server directory reads have no user session behind them. |
| Operations | `manage.py sync_identity`, `manage.py service_token` | See [the runbook](../../07-ops/runbooks/sync-identity-projection.md). |

**Measured against the live dataset** (2026-08-02): 3,277 users, 3,155 designations projected in
**0.3 s**. With the ERP alias pointed at an empty database, login, `/me`, `/directory/users` and the
platform's pull-through directory cache all served correctly, and the platform completed a full
login → session → placement-postings flow. Zero ERP relations were touched on any request path.

Two guarantees are held by tests rather than by convention:

- `iam.tests.test_erp_isolation` parses the import graph and fails if any view — or any module other
  than `sync.py` — imports `erp_source`. The comment in `erp_source.py` ("if this file is imported
  from a view, Phase 1 has been undone") is executable.
- `iam.tests.test_sync` covers the revocation direction specifically: a removed designation or
  module grant must actually disappear, and an empty ERP read must not deactivate the institute.

### Phase 2 — IAM writes, ERP receives (the flip)

```
IAM  identity tables                            ← source of truth; new users created HERE
      │  one-way projection (reverse direction)
      ▼
ERP  auth_user row written so the 126 FKs still resolve
```

The same sync machinery runs backwards. The monolith keeps working untouched because it still has an
`auth_user` row for everyone — it simply is not the thing that decides who exists any more. This is
the strangler flip, and it is the only genuinely delicate step.

### Phase 3 — the monolith is gone

```
IAM  identity                                   ← the only copy
      ├──► Fusion-Integrated   (placement, hr, …)
      └──► Fusion-Academic     (rebuilt: registration, grades, curriculum)
```

The projection into the ERP stops and the ERP-side copy is dropped with it. `auth_user` ceases to
exist. Nothing else changes: both applications were already holding `user_id` integers and asking IAM,
so neither notices.

## Consequences

**Good**

- **Nothing built now is discarded.** The IAM identity tables, the sync job, `/me`,
  `/directory/users` and every consumer survive all three phases unchanged. Only the arrow flips.
- **Each phase is independently valuable.** Phase 1 alone removes IAM's runtime dependency on the ERP,
  so identity survives ERP downtime — worth doing even if phases 2 and 3 never happen.
- **A rebuilt academic app is just another consumer.** It holds no user table, references `user_id`,
  and reads IAM — exactly like Fusion-Integrated. No new identity design is needed when that day
  comes; the work is the academic domain, not the plumbing.
- **The risky step is isolated.** Only Phase 2 touches who-writes-what, and it is reversible: stop
  the reverse projection and the ERP is authoritative again.
- **The no-cross-module-FK rule pays off here.** Because no platform table has a foreign key to a user
  table, none of them care which database identity lives in
  ([ADR-0013](0013-no-cross-module-foreign-keys.md)).

**Bad, and accepted**

- Two copies of identity exist for as long as the monolith does. Mitigated by the sync being strictly
  one-way at any given moment, and by a reconciler reporting drift.
- Phase 2 needs a real cutover plan — dual-write, verify, flip, with a rollback. It is the same shape
  as the auth cutover already documented in
  [auth-migration-runbook.md](../../02-iam/auth-migration-runbook.md).
- Password hashes have to live wherever authentication happens. In Phase 1 that means IAM either reads
  the ERP hash at login or syncs it; in Phase 2 IAM owns it outright. As built, the hash is synced and
  a failed match falls back to one live ERP read (so a reset done in the ERP works before the next
  sync), then re-syncs. If the ERP is unreachable at that moment the login fails — correct, because
  the credential cannot be verified.
- Role changes are visible to the platform only as fast as the sync runs. At a 15-minute schedule
  that is the worst-case lag; the job itself takes 0.3 s, so an urgent change is a manual re-run.

## Alternatives considered

**Move the tables into `system_db` now.** Rejected: 276 FK constraints, live production, no tests. The
riskiest available operation, for a benefit the projection delivers safely.

**Skip the projection; keep reading the ERP live until the monolith dies.** Tempting — it is less code
today. Rejected because it chains IAM's availability to the ERP's indefinitely, and because the
monolith's retirement is not scheduled. It also means the eventual move is a big-bang with nothing
rehearsed.

**Wait for the academic rewrite, then design identity once.** Rejected: that rewrite is
[out of scope](../../00-overview/vision-and-scope.md#non-goals) and unscheduled, and Fusion-Integrated
needs working identity now. Deferring would mean either no login or a throwaway one.

## Revisit if

The academic rewrite is actually committed and scheduled — at which point Phase 2 should be planned
alongside it, rather than as a separate migration, so the flip and the rewrite share one cutover.
