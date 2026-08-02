# ADR-0013 — No foreign key crosses a module boundary

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0001](0001-modular-monolith-over-microservices.md), [0007](0007-read-only-erp-access-via-acl.md)

## Context

`fusion-platform` is a modular monolith ([ADR-0001](0001-modular-monolith-over-microservices.md)). All the
modules share one database, so nothing *prevents* `placement.Application` from declaring
`ForeignKey("hr.Employee")`. Django would allow it, the join would work, and it would be the most
convenient thing to write.

That convenience is exactly how the current 34-app monolith became inseparable. Once a foreign key exists,
three things follow automatically and irreversibly:

1. A **join** appears, so the query planner — and then every developer — treats the two tables as one
   schema.
2. **Cascade semantics** cross the boundary. Deleting an `hr.Employee` now silently affects placement data,
   decided by whoever wrote the `on_delete` argument.
3. **Migration coupling.** The two modules' migration histories reference each other, so neither can move
   without the other.

The third is the one that kills optionality. A module with inbound foreign keys cannot be extracted, cannot
be moved to another database, and cannot be deleted — which is why the deprecated apps are still installed.

## Decision

**No `ForeignKey`, `OneToOneField` or `ManyToManyField` may reference a model in another module.**

Cross-module references are **plain integer or UUID columns** with an explicit, documented meaning:

```python
class Application(models.Model):
    posting = models.ForeignKey("placement.JobPosting", on_delete=models.CASCADE)  # same module: fine
    user_id = models.IntegerField(db_index=True)   # IAM erp_user_id — NO FK, cross-boundary
```

Reads happen through the other module's `contracts.py`, **plural by signature**:

```python
from modules.directory import contracts as directory

apps = selectors.applications_for_posting(posting_id)
users = directory.get_users([a.user_id for a in apps])   # one batched call
```

Enforced in CI by a script that introspects every model's relation fields and fails on any cross-module
target — `ops/checks/no_cross_module_fk.py`, run in `backend.yml` alongside `import-linter`.

**The same rule applies to the ERP**, where it is enforced by physics: cross-database foreign keys are
impossible in Django. Platform tables reference `auth_user` as `user_id`, never as an FK
([ADR-0007](0007-read-only-erp-access-via-acl.md)).

### Explicitly allowed

- Foreign keys **within** a module — encouraged, with real `on_delete` semantics.
- Foreign keys into `core/`'s shared tables, which have no domain semantics.
- Denormalizing a small, stable label alongside the id (`batch_erp_id` **plus** `batch_label`) where it
  avoids a chatty contract call for display purposes. Documented as denormalization; never treated as the
  source of truth.

## Consequences

**Good**

- **Extraction stays cheap.** Promoting a module to its own service means changing one file's
  implementation — `contracts.py` becomes HTTP calls — with no schema surgery. That is the option
  [ADR-0001](0001-modular-monolith-over-microservices.md) is buying, and this is the decision that pays for
  it.
- No accidental cascades across boundaries. Deleting an employee cannot silently mutate placement records;
  what happens is written explicitly in a service or an event handler.
- Migration histories stay independent. A module can be added, changed or removed on its own.
- **The plural-by-signature rule makes N+1 queries hard to write.** There is no
  `get_employment(user_id)` to call in a loop, because it does not exist.
- The boundary is visible in the schema, so a reviewer can see it without reading imports.

**Bad, and accepted**

- **No database-level referential integrity across boundaries.** An `Application.user_id` can point at a
  user who no longer exists. Mitigated by: users being archived rather than deleted (`identity_user.status`);
  `iam.user.status_changed` events letting modules react deliberately; a nightly orphan-reference report;
  and contract functions returning a mapping so a missing id is a visible `KeyError`-shaped case rather than
  silent `NULL`.
- **No cross-boundary joins**, so some reads become two queries plus an in-memory join. This is the real
  cost. Accepted because the batched contract call keeps it at exactly two queries, and because unbounded
  join freedom is what made the legacy codebase inseparable.
- Cross-module filtering is harder. "All applications from CSE students" cannot be one join; it is
  `directory.search_users(department="CSE")` then `applications_for_users(ids)`. For genuinely large
  cross-cutting reports this is done in a Celery job against a materialized snapshot rather than
  synchronously.
- `select_related` cannot span the boundary, so serializers must be given pre-fetched maps. Mitigated by a
  small `core/api/hydrate.py` helper that takes a contract mapping and attaches it to serializer context.
- Developers will want to break this rule roughly weekly. Mitigated by CI, and by the reviewer response
  being a question rather than a refusal: *"Is the boundary in the wrong place?"* If two modules need to
  join constantly, that is real evidence they are one module — and merging them is the correct fix, not
  adding the key.

## Alternatives considered

**Allow cross-module FKs with `db_constraint=False`.** Tempting: you get `select_related` and Django's
relation API with no database constraint. Rejected because it keeps the *code* coupling — the join, the
cascade declaration, the migration dependency — while discarding the one genuine benefit (integrity). Worst
of both.

**Allow FKs, forbid them only at extraction time.** Rejected: extraction never happens if it requires
untangling schema first. This is the exact reason the 26 deprecated apps are still in `INSTALLED_APPS`.

**Separate databases per module, so the rule is enforced by physics.** Rejected: it would forfeit the
single-transaction property that is the main reason for choosing a modular monolith. Accepting an offer must
be atomic.

**Rely on code review.** Rejected: a rule that is only enforced socially is not enforced. There is no
existing test suite or CI to lean on, and the reviewer who is tired at 6 p.m. is the one who lets the first
one through.

## Verification

- `ops/checks/no_cross_module_fk.py` introspects `apps.get_models()` and fails on any relation field whose
  target's app label differs from the source's, excluding `core`. Runs in CI.
- `import-linter` independently forbids importing another module's `models`.
- A nightly `report_orphan_references` task counts dangling cross-module ids per table and alerts on any
  increase.
- Every `contracts.py` function is asserted plural-by-signature by a test that inspects its annotations for
  a sequence parameter.
