# ADR-0001 — Modular monolith over microservices

- **Status:** accepted
- **Date:** 2026-08-01
- **Deciders:** platform lead
- **Related:** [0013](0013-no-cross-module-foreign-keys.md), [0002](0002-separate-iam-service-and-database.md)

## Context

The non-academic platform will eventually hold on the order of twenty functional areas — placement,
HR, leave, finance, purchase, hostel, mess, health centre, complaints, gymkhana, IWD, scholarships,
research projects, and more. The obvious instinct at that count is one service per area.

What we actually have:

- **~3,277 users** at one institute, on **one VM**.
- **One small team**, with no dedicated platform or SRE function.
- The existing estate has **no CI, no tests, and no container orchestration**. There is no operational
  muscle to borrow from.
- The workflows are strongly transactional and cross-area. Accepting a placement offer must, in one
  atomic step, create a record, supersede a prior offer, withdraw other applications and update
  counters. Splitting that across services turns a transaction into a saga.

The real requirement behind "follow big-tech strategies" is *maintainability and the ability to evolve
without a rewrite*. Large organizations get that from **hard module boundaries**, and adopt separate
deployables mainly to let independent teams ship independently. We have one team. We need the
boundaries; we do not need the deployables.

## Decision

Build `fusion-platform` as a **modular monolith**: one Django project, one database, one deployable,
with bounded contexts enforced mechanically rather than by convention.

Enforcement, all in CI:

- A module may import another module **only** via `modules.<other>.contracts` — `import-linter`
  contracts fail the build otherwise.
- **No foreign key crosses a module boundary** ([ADR-0013](0013-no-cross-module-foreign-keys.md)); a
  script walks every `ForeignKey` target.
- `domain/` may not import Django at all.
- Each module has one public surface (`contracts.py`), plural by signature.

`fusion-iam` is a **separate** service, because identity has a genuinely different security boundary,
lifecycle and blast radius ([ADR-0002](0002-separate-iam-service-and-database.md)). Two deployables,
not twenty.

## Consequences

**Good**

- One transaction covers a business operation. No sagas, no compensating actions, no
  eventually-consistent bugs inside a single workflow.
- One migration history, one deploy, one log stream, one set of dashboards — operable by this team.
- Cross-module reads are in-process function calls: no network, no timeouts, no retry budgets, no
  circuit breakers.
- **Extraction stays cheap.** Because no FK crosses a boundary and all access is through
  `contracts.py`, promoting a module to a service later means replacing one file's implementation with
  HTTP calls. That is the option we are buying.
- A new developer can run the whole platform with `docker compose up`.

**Bad, and accepted**

- A module cannot be scaled independently. Mitigated by separate Celery queues per workload
  (`ingest`, `reports`, `notifications`) so heavy background work is already isolated.
- A bad deploy affects every module. Mitigated by module grants: a module granted to nobody is
  invisible and unroutable, so partial features ship safely, plus atomic symlink deploys with
  automated rollback.
- One process's memory leak or runaway query affects all modules. Mitigated by `MemoryMax` in systemd,
  `--max-requests` recycling in gunicorn, and statement timeouts.
- **The boundaries only hold if CI holds them.** Without `import-linter` and the FK check this design
  degenerates into the 34-app tangle we are replacing. Those checks are not optional niceties; they
  are the architecture.

## Alternatives considered

**Microservices per functional area.** Rejected: distributed transactions for inherently atomic
workflows, ~20× the operational surface for one team, and no independent-deployment benefit because
there are no independent teams. It would also make the shell's single-login/single-sidebar requirement
substantially harder.

**Keep extending the existing 34-app monolith.** Rejected: that is the codebase whose lack of
boundaries is the problem. It has no cache, a non-functional Celery, one index across 424 models, and
`DEBUG=True` in production. Adding to it would inherit all of that.

**Two services split academic/non-academic only, with no internal modularity.** Rejected: this is how
the current monolith started. Without enforced internal boundaries, `placement` will reach into `hr`'s
tables within a quarter.

**Serverless / functions.** Rejected: no fit for a long-lived transactional Django application on
self-hosted infrastructure.

## Revisit if

- A module develops a genuinely different scaling profile (sustained CPU or memory an order of
  magnitude above the rest).
- The team grows past roughly three independent squads wanting independent release cadences.
- A single module's deploy risk becomes the binding constraint on release frequency.

In any of those cases, extraction is a scoped project on one module, not a re-architecture — which is
exactly the property this decision preserves.
