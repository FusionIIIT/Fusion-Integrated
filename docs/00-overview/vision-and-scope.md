---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Vision & Scope

## The one-sentence version

Build a new non-academic platform on its own database, pull authentication and authorization into a
single central authority, put every module behind one login and one server-driven sidebar — and leave
the academic monolith running untouched while it happens.

## Why now

Fusion works. It serves ~3,277 users at PDPM IIITDM Jabalpur and the academic half is actively
maintained. But three specific things now block any further growth, and none of them get better by
waiting. They are documented in detail in [current-state-assessment.md](current-state-assessment.md);
in summary:

1. **Identity is scattered.** Authorization is designation-**name string matching** through three
   parallel, mutually inconsistent mechanisms. Module access is one boolean column per module keyed
   by free text, and it only hides menu items — it does not gate a single request. Administrators of
   the system are a different account set in a different database and cannot log in to the system
   they administer.
2. **The non-academic half does not really exist.** 26 apps, ~60k LOC, ~290 models — deprecated,
   14 of them with no API layer at all, all still on Django templates. There is nothing there worth
   preserving.
3. **Nothing is engineered to scale.** No cache configured at all. Celery cannot boot. One database
   index across 424 models. A database write on every request. `DEBUG=True` in production.

## What we are building

### 1. A central identity service — `fusion-iam`

One authority for *who you are* and *what you may do*. It owns credentials, sessions, tokens, MFA,
roles, permissions, the module registry, module grants and the audit trail. It lives in
`fusion_system_db` (schema `iam`).

The academic monolith and the new platform both validate its tokens. Nobody has a second password.

**`auth_user` rows stay physically in the ERP database.** All ~424 monolith models have foreign keys
pointing at that table; moving it would mean editing every one of them against live production data.
IAM references users by `erp_user_id` — a logical reference, no cross-database foreign key — and
projects roles *one-way* back into the legacy `globals_*` tables so the monolith keeps working
unchanged. See [ADR-0002](../01-architecture/adr/0002-separate-iam-service-and-database.md).

### 2. A non-academic platform — `fusion-platform`

A **modular monolith** on its own database (`fusion_nonacad`), with strict bounded contexts:
Placement, HR, Leave, and more over time. Modules may only talk to each other through an explicit
`contracts.py`, enforced by `import-linter` in CI. No foreign keys cross a module boundary.

It reads academic facts through a **read-only** access layer over the ERP, and never writes there.

### 3. One unified shell — `apps/shell`

A single SPA, a single login, and a sidebar built from **server-sent module grants** rather than a
hardcoded array. The design system is extracted verbatim from the existing
`Fusion_System_Administrator` client, which is the best-engineered UI in the estate — same 280px dark
navbar, same `#15ABFF` accent, same `PageHeader`, pixel-for-pixel.

The `Fusion_System_Administrator` pages move into it as a `sysops` module, making it the control
plane for **both** academic and non-academic administration. The legacy academic SPA is linked out
from the sidebar for now and absorbed later.

### 4. Placement Cell, as the first real module

Chosen deliberately as the first vertical slice: it is student-facing, it has a genuine workflow
(postings → eligibility → applications → rounds → offers), it forces the academic-integration
problem to be solved properly, and it is small enough to finish.

## Non-goals

These are as binding as the goals. A request to do any of them goes through a design document first,
and probably gets declined.

| # | Non-goal | Why |
|---|---|---|
| **NG1** | **No multi-tenancy.** No `tenant_id`, no per-tenant schemas, no subdomain routing. | One institute. Tenancy would tax every table, every queryset and every migration for a second institute that does not exist. Revisit only if one actually appears. → [ADR-0011](../01-architecture/adr/0011-no-multi-tenancy.md) |
| **NG2** | **No port of the 26 deprecated non-academic apps.** | They are deprecated for good reason. As one concrete example: the old placement module filters students on `Student.cpi`, a column that is permanently `0.0` because nothing has ever written a computed value to it. Porting that code would port its bugs. We design fresh. |
| **NG3** | **No rewrite of the academic monolith in this programme.** | The five live academic apps stay exactly where they are. We add token validation and a one-way role projection; we change nothing else about how they work. Absorption is a later, separately-scoped programme. |
| **NG4** | **No microservices.** Two new deployables, not twelve. | At this scale microservices buy distributed transactions, eventual-consistency bugs and an operations burden, and buy nothing back. Boundaries are enforced in-process so extraction stays cheap if it is ever justified. → [ADR-0001](../01-architecture/adr/0001-modular-monolith-over-microservices.md) |
| **NG5** | **Placement does not compute CPI.** Ever. | The ERP's `calculate_cpi_for_student` has subtle, load-bearing semantics (grade `S` earns credit but is excluded from the average; `X` and `CD` are excluded entirely; **`F` earns 2.0 points and its credit**; dedup by course code; swayam replacement chains). Reimplementing it would produce a second, disagreeing CPI. We snapshot the ERP's own output. → [academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md) |
| **NG6** | **No Kubernetes, no service mesh, no multi-region.** | One VM, hardened, with a restore runbook that has actually been executed. Add infrastructure when a measured problem demands it. |
| **NG7** | **No new UI language.** | The design system is *extracted*, not redesigned. Visual changes are a separate conversation with a separate approval. |
| **NG8** | **No GraphQL.** | REST with a committed OpenAPI schema and a generated typed client. One way to do things. |

## What "handles growth" means here

The system serves ~3,277 users today. The instruction was to engineer so that growth does not break
it — not to build for a million users we do not have. Concretely, that means we invest in the things
that are expensive to retrofit and cheap to do now:

- Redis for cache **and** sessions (the legacy currently writes a session row to Postgres on every
  single request).
- A Celery broker that actually works, with idempotent tasks and a transactional outbox.
- PgBouncer connection pooling, with the `CONN_MAX_AGE=0` /
  `DISABLE_SERVER_SIDE_CURSORS=True` constraints that transaction pooling imposes.
- Indexes designed against real query plans, declared explicitly in `Meta.indexes`.
- Pagination and throttling on every endpoint from day one.
- A read-replica seam (an explicit `@use_replica` decorator on chosen selectors) that can be turned
  on later without a rewrite.
- Load tests as a phase gate, with committed results.

And it means we deliberately **do not** build: sharding, tenancy, eventual-consistency read models,
or a message bus beyond Postgres-plus-Celery.

## Success criteria

The programme has succeeded when all of the following are true:

1. A user logs in **once** at `/app/` and sees exactly the modules their roles grant — with the
   sidebar built by the server, not by a hardcoded client array.
2. Revoking a role in the shell takes effect in the **legacy** monolith within 30 seconds, and a
   nightly reconciler reports zero drift between IAM and the `globals_*` tables.
3. The Placement Cell runs a full real season end to end: postings, eligibility, applications,
   rounds, offers, acceptance policy, statistics.
4. Every CPI displayed in Placement is provably identical to the ERP's own computation for the
   declared semester, carries its provenance on screen (`8.10 · Sem 5 (Odd) · declared 28 Jul 2026`),
   and is never a provisional value.
5. `manage.py check --deploy` is clean on every service, no secret is committed, and the legacy
   monolith no longer runs `DEBUG=True` in production.
6. A new developer can add a module by following
   [module-authoring-guide.md](../03-platform/module-authoring-guide.md) without asking anyone.
7. A backup restore has been performed for real, on a scratch host, with the elapsed time written
   into the runbook.

## Explicitly out of scope for the first release

Documented here so they are decisions rather than oversights: SSO against institute LDAP/Google
Workspace (the seam exists — `identity_credential.algo` and an `amr` claim — but no provider is
wired), mobile applications, a public API for third parties, and offline support.

## Sequencing

Nine phases, each independently shippable, gated, and reversible. Phase 0 is this documentation set
plus legacy hardening. The risky one is Phase 3 (dual auth); it is entirely feature-flagged, and
existing tokens keep working throughout so a rollback needs no re-login.

Full detail: [roadmap-and-phases.md](../08-delivery/roadmap-and-phases.md).
