# ADR-0011 — Single tenant. No `tenant_id`, no per-tenant schemas

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0001](0001-modular-monolith-over-microservices.md)

## Context

The brief asked for a system that can "handle 1 million users". Production today serves **~3,277 users** at
one institute, PDPM IIITDM Jabalpur.

A million users is only reachable by serving many institutes, which means multi-tenancy: a `tenant_id` on
every table, tenant-scoped querysets enforced at the ORM layer, per-tenant subdomains, tenant-aware caching,
tenant-aware migrations, and a tenant dimension in every index, every report and every export.

When the question was put directly — is this a multi-institute SaaS, or one institute that must not fall
over as it grows — the answer was **one institute, engineered for headroom**.

That answer is worth taking seriously rather than hedging. Tenancy is not a feature you add cheaply later,
but it is also not something you can carry cheaply *unused*: every queryset, every cache key, every
migration and every index pays for it, and a single missed `.filter(tenant=...)` is a cross-tenant data
leak. Building it "just in case" for a tenant that does not exist buys a permanent tax and a permanent
class of security bug.

## Decision

**Build single-tenant.** No `tenant_id` column, no tenant schemas, no subdomain routing, no tenant-aware
middleware, no sharding.

Instead, invest the same effort in the things that are expensive to retrofit and that we will certainly
need:

| Investment | Why it is the better spend |
|---|---|
| Redis for cache **and** sessions | The legacy writes a session row to Postgres on **every** request (`SESSION_SAVE_EVERY_REQUEST = True`) and has no `CACHES` setting at all |
| A working Celery + transactional outbox | Legacy Celery cannot boot — broker commented out, settings module misnamed |
| PgBouncer transaction pooling | No `CONN_MAX_AGE` today, so a fresh connection per request |
| Explicit indexes in `Meta.indexes` | **One** `db_index=True` across 424 legacy models |
| Cursor pagination + throttling everywhere, by default | Neither exists today |
| A read-replica seam (`@use_replica` on chosen selectors) | Turn-on-able later without a rewrite |
| Load tests as a phase gate | No performance baseline exists today |

Recorded as [NG1](../../00-overview/vision-and-scope.md#non-goals).

**What we do keep**, at essentially zero cost, because it happens to be good design anyway:

- No cross-module database joins; all cross-module reads go through `contracts.py`
  ([ADR-0013](0013-no-cross-module-foreign-keys.md)).
- Every module reaches its data through `selectors/`, so a scoping predicate has exactly one place to be
  added per module rather than being sprinkled across views.
- Cache keys are already namespaced and version-bearing, so adding a tenant segment later is mechanical.

That is the honest extent of "tenancy-ready": we are not pre-building tenancy, we are simply not making it
gratuitously harder.

## Consequences

**Good**

- Every queryset is simpler and every index is narrower. No tenant dimension to remember.
- **The entire class of cross-tenant leakage bugs does not exist.** This is the largest security benefit,
  and it is worth more than the optionality we are giving up.
- Migrations are ordinary Django migrations, not a per-tenant orchestration.
- Caching is straightforward; no tenant-key discipline to maintain.
- The team's effort goes into correctness and headroom rather than into infrastructure for a hypothetical
  second customer.

**Bad, and accepted**

- **A second institute would be a genuine re-architecture**, not a configuration change. This is stated
  plainly in [vision-and-scope.md](../../00-overview/vision-and-scope.md) so it is a known trade-off rather
  than a surprise. The realistic path if it happens: a separate deployment per institute first (cheap,
  isolated, immediately correct), and multi-tenancy only if the per-deployment operational cost becomes the
  binding constraint.
- "1 million users" is not achievable on this design. We are explicit that the number was aspirational and
  that the real requirement was headroom.
- Institute-specific values (grade scales, semester conventions, department lists) will end up in
  configuration and reference tables rather than in a tenant model. Acceptable, and better documented in
  [settings-and-configuration.md](../../03-platform/settings-and-configuration.md).

## Alternatives considered

**Multi-tenant from day one (`tenant_id` everywhere).** Rejected: a permanent tax on every table, index,
queryset, cache key and migration, plus a permanent cross-tenant-leak risk, for a tenant that does not
exist. It would also slow the Placement slice materially, which is the thing that actually needs to ship.

**Schema-per-tenant (`django-tenants`).** Rejected: better isolation than a `tenant_id` column, but
migrations must run per schema, connection routing becomes middleware, and Django's migration state handling
across many schemas is operationally heavy for a single-VM deployment with no SRE function.

**Database-per-tenant.** Effectively the "separate deployment per institute" path, and the one we would
actually choose if a second institute appeared — but there is nothing to build for it now.

**Add `tenant_id` columns now, defaulted to 1, unused.** Superficially the cautious middle. Rejected: it
carries most of the cost (wider indexes, a column on every table, a field in every serializer someone will
eventually expose) while providing none of the safety, because the enforcement layer — the part that
actually prevents leaks — would not exist. An unenforced tenant column is worse than no tenant column: it
looks like isolation and is not.

## Revisit if

A second institute is actually committed — funded, scoped and scheduled. At that point the first move is a
separate deployment, and true multi-tenancy is evaluated only against measured operational cost, with a
fresh ADR superseding this one.
