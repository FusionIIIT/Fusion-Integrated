---
owner: platform-lead
status: authoritative
last-reviewed: 2026-09-29
purpose: >
  The single prompt used to start any new Fusion-Integrated module from its BR/UC
  specification. Copy §0–§9 verbatim into a new session, fill the four blanks in §0,
  and change nothing else. Uniformity across modules is the point of the document.
---

# New module — the starting prompt

Two modules are already built to this shape: `modules/placement` (largest, the reference)
and `modules/leave` (most rule-dense, the reference for state machines and ledgers).
A third module that does not look like them is a defect, not a style choice.

**How to use this:** copy everything from the `--- PROMPT BEGINS ---` line to the
`--- PROMPT ENDS ---` line into a fresh session. Fill in the four bracketed blanks in §0.
Do not summarise it, do not trim it — the length is what keeps modules identical.

---

--- PROMPT BEGINS ---

## §0 — The job

Build the **[MODULE_NAME]** module in `Fusion-Integrated`, from its specification set at
**[SPEC_FOLDER_PATH]**, to the same standard and the same shape as the existing
`modules/placement` and `modules/leave` modules.

- Specification id prefixes: **[ID_PREFIX]** (e.g. `PC-BR-`, `PC-UC-` for Placement;
  `BR-EL-`, `EL-UC-` for Leave).
- Module code / URL segment: **[module_code]** (lowercase, singular-ish, no underscores).

This is production code for an institute that will run it for years. "The tests pass" is
not the finish line — §8 is.

Work in phases. **Do not write a line of application code before Phase 2 is approved by me.**

---

## §1 — Phase 0: read, before anything else

Read these in this order and do not skim. You are being asked to match an existing house
style precisely, and you cannot match what you have not read.

**The platform's own rules**
- `docs/01-architecture/adr/` — every ADR. `0013` (no cross-module FKs), `0010`
  (server-driven navigation), `0002` (separate IAM service and database) and `0006`
  (outbox + Celery) constrain your design directly.
- `docs/03-platform/platform-structure.md` — the layering rules.
- `docs/03-platform/shared-kernel-reference.md` — what may and may not go in `core/`.
- `docs/06-crosscutting/testing-strategy.md` and `security-baseline.md`.
- `docs/08-delivery/definition-of-done.md`.
- `.importlinter` — the four contracts. These are enforced by CI, not advisory.
- `Makefile` — specifically the `check` target. That list is the contract with CI.

`docs/03-platform/module-authoring-guide.md` has drifted from the code (it names paths and
a `make new-module` target that no longer exist). Read it for intent; trust the code and
this document for shape. If you spot a specific drift, list it at the end — do not fix it
mid-task.

**The reference implementations**
- `modules/placement/` in full — this is the shape you are copying.
- `modules/leave/` in full — read `domain/state_machine.py`, `services/workflow.py`,
  `selectors/scoping.py` and `models/ledger.py` closely even if your module has no ledger.
  They demonstrate the choke-point pattern you will need.
- `core/` in full — `api/exceptions.py`, `api/pagination.py`, `api/csrf.py`,
  `api/throttling.py`, `db/mixins.py`. Anything already here you must reuse, not reinvent.
- `client/src/modules/placement/` and `client/src/modules/leave/` — the frontend shape.

**The specification**
Read every document in the spec folder. Build an inventory before you interpret anything:
- How many business rules exist, and **which ids the spec explicitly retires**. Retired ids
  are a trap: some retirements moved the behaviour to a requirement id rather than dropping
  the behaviour. Record which is which.
- How many use cases, and which are retired.
- The workflow ids (basis and composite) and their current naming.
- The requirement ids, if the spec has a separate requirements layer.
- Whether the traceability matrix's mapping columns are actually populated. If they are
  empty, say so and derive coverage by reading each rule — never by trusting the matrix.

At the end of Phase 0, tell me: the artefact counts, the retired ids with their
replacements, any internal contradiction between two spec documents, and any rule that
cannot be implemented as written. **Do not invent an id that the spec does not contain**,
and do not cite a retired id as if it were live.

---

## §2 — Phase 1: the questions that must be answered before code

Some specs are written against assumptions Fusion does not hold. Surface these now, not in
review. Answer what you can from the code; ask me the rest as a short numbered list.

1. **Is this one bounded context?** If the answer is "mostly", it is two modules.
2. **What does it need from other modules?** Every answer becomes a function on *their*
   `contracts.py`, agreed with them. A long list means the boundary is wrong.
3. **Identity.** Fusion's identity lives in a *different database*, reached over HTTP
   (`fusion_auth/client.py`), projected locally by `modules/directory`. If a spec says
   "foreign key to Employee" or "request.user.employee", it is describing a system we do
   not have. Every person reference in your module is a **plain integer `user_id`**
   (`core/db/mixins.py::UserScopedModel`). No exceptions.
4. **Who decides, and who may see.** List every role in the spec and map it to a
   designation as it actually exists in `globals_designation`, plus the basic `student` /
   `faculty` / `staff` kinds. A role the IAM cannot express is a blocker, not a detail.
5. **Scope.** For each read endpoint: whose rows does this person see? The answer becomes
   queryset narrowing in `selectors/scoping.py`, which yields **404, never 403** — a 403
   confirms the row exists to someone who should not know that.
6. **Time.** Does anything expire, escalate, credit annually, or advance on a date? That is
   a Celery beat entry in `schedule.py`, and beat *must* be running in production. If
   nothing in the module needs a clock, say so explicitly.
7. **Money / quota / balance.** If the module counts anything a person can spend, it is an
   **append-only ledger**, not a balance column. Corrections are reversing entries.
   See `modules/leave/models/ledger.py`.
8. **Policy.** Anything an administrator configures is **effective-dated and never edited** —
   superseded by a new version. A module with no seeded policy must not 500 on first use;
   it must say what is missing.

---

## §3 — Phase 2: the blueprint (deliverable, needs my approval)

Write `docs/[NN]-[module_code]/[module_code]-blueprint.md` **before any code**. It contains:

**a. Traceability table.** One row per live business rule and per live use case:

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |

The "layer" column is the design decision. A rule that lands in `api/` is almost always
misplaced — API is transport, not policy.

**b. Domain model.** Entities, their fields, their invariants. Name the constraints you will
push into the database (`UniqueConstraint`, `CheckConstraint`, partial unique indexes) as
opposed to enforcing in Python. Anything that must hold under concurrency belongs in the
database.

**c. State machine, if the module has one.** A **declarative transition table** — a data
structure listing (state, event, actor) → state. Not a chain of `if` statements. An illegal
transition must be *inexpressible*, not merely rejected. See
`modules/leave/domain/state_machine.py`.

**d. Permission list.** The exact `registry.py` content: `MODULE`, `PERMISSIONS`,
`SYSTEM_PERMISSIONS` (bare strings, for scheduled work no human holds), `SCOPE_PERMISSIONS`,
and `ROLE_GRANTS` keyed by real designation names.

**e. Endpoint list.** Method, path under `/api/v1/[module_code]/`, the two gates it sits
behind, what it returns, and which rule ids it enforces.

**f. Contracts.** What `modules/[module_code]/contracts.py` will expose to other modules,
and what you need added to theirs. Every getter is **plural** — `get_x(ids: Sequence[int])`
— because a singular getter is the one that ends up inside a loop
(`ops/checks/contracts_are_plural.py` enforces this).

**g. Scheduled work.** Each beat entry, its cadence, and what breaks in the real world if it
does not run.

**h. Open questions.** Anything the spec does not settle. Do not guess and do not build on
a guess.

Stop here. Wait for my approval.

---

## §4 — Phase 3: backend, in layer order

Build strictly bottom-up. Each layer must be complete and tested before the next.

```
modules/[module_code]/
├── __init__.py  apps.py  contracts.py  registry.py  schedule.py  tasks.py
├── domain/          framework-free Python: rules, state machine, calculations
├── models/          Django models, one file per aggregate, package not module
├── selectors/        all reads, including scoping.py
├── services/         all writes, one file per use-case family
├── api/              views.py serializers.py urls.py (+ permissions.py if it needs
│                    its own gate classes — placement has one, leave does not)
├── management/commands/
├── migrations/
└── tests/
```

Layer rules, enforced by `.importlinter` (add your module to the existing contracts — the
`domain-is-pure-python` and `modules-only-touch-contracts` contracts each list modules
explicitly, and a module you forget to add is a module that is **never checked**):

- **`domain/`** imports no Django, no DRF, no Celery. Pure functions and dataclasses. It may
  raise plain exceptions; the **service layer** translates them into `core.api.exceptions`
  types. Never import `core.api.exceptions` from `domain/`.
- **`models/`** may import `domain/`. No `ForeignKey` crosses a module boundary, ever
  (`ops/checks/no_cross_module_fk.py`). Use `TimeStampedModel` / `UserScopedModel`.
- **`selectors/`** returns querysets and read DTOs. No writes. `scoping.py` owns visibility
  and every list endpoint starts from it.
- **`services/`** owns every write. Rules:
  - One transactional choke point per state change. If there is a workflow, *all* movement
    goes through one function (`modules/leave/services/workflow.py::apply_event` is the
    model to copy) that takes `select_for_update`, refuses a terminal source state, refuses
    the wrong actor, writes the audit trail, and emits any ledger entry — in one
    transaction. Two paths into the same state is how the rules drift apart.
  - Raise `DomainError` subclasses from `core/api/exceptions.py` with a `code=`. The message
    is read by a person at IIITDMJ; write it as a sentence that tells them what to do next.
  - **Order the refusals deliberately.** When two checks can both fail, the one whose message
    is more useful goes first.
- **`api/`** is transport only: parse, delegate, serialise. Two gates on every endpoint —
  the module grant first, then the permission. Query parameters are hostile input: an
  unparseable `?year=abc` is a **400, never a 500**.
- **`registry.py`** as designed in Phase 2. `nav_matches_routes.py` will fail CI if a nav
  entry has no client route or a route has no nav entry.
- **`schedule.py`** exports `BEAT_SCHEDULE` and `TASK_ROUTES`; register both in
  `config/celery.py`. Each module owns its own timers so a module stays removable.
- **Management commands** for anything an operator must do: seeding policy, a readiness
  check, a manual run of each scheduled task. Never name a flag `--version` — it collides
  with Django's own and the command becomes uninvokable at parser construction.

Comments: **single line only, and only where the reason is not obvious from the code.**
If it will not fit on one line it belongs in `docs/`. This applies to `#`, `//`, JSX
comments and docstrings alike. A docstring that restates the function name is noise.

---

## §5 — Phase 4: tests that would actually catch a bug

Mirror `modules/placement/tests/` — one file per concern, named for the concern.
Required, not optional:

- **Domain tests** with no database. Every branch of every rule.
- **State machine tests**: assert that every illegal transition is *refused*, enumerated
  from the transition table rather than hand-picked.
- **Privilege escalation tests** (`test_privilege_escalation.py`): for each endpoint, a
  principal who should not reach it, asserting 403 or 404 as designed.
- **Scoping isolation tests** (`test_recruiter_isolation.py` is the model): person A must
  not see person B's rows, including through a filter, a search and an export.
- **Concurrency tests** for anything that credits, allocates, or must happen once. Run real
  threads against the real database. Green single-threaded tests prove nothing here —
  a double-credit bug in leave survived 631 passing tests and was only ever found this way.
- **Query budget tests** (`test_query_budgets.py`): assert a maximum query count per list
  endpoint so an N+1 fails CI instead of production.
- **Schedule tests**: assert every beat entry your module registers is actually present in
  `config/celery.py`'s merged schedule.
- **Adversarial pass.** Before you tell me it is done, spend a deliberate pass trying to
  break your own module as a malicious insider. Specifically ask: can an approver approve
  their own record? Can a thing appear in its own approval queue? Can a balance go negative?
  Can something be back-dated without limit? Can a required third party be someone who is
  themselves unavailable? Each of those five was a real hole in leave that the test suite
  did not see.

---

## §6 — Phase 5: frontend

`client/src/modules/[module_code]/`, matching the two existing modules exactly:

```
api/types.ts        types mirroring the serializers
api/hooks.ts        TanStack Query hooks, one per endpoint
api/hooks.test.tsx
components/         module-specific components
pages/              one file per route
routes.tsx          the route table nav_matches_routes.py reads
```

- Use the shared axios instance `client/src/lib/http.ts`. It already carries the session
  cookie and the CSRF header. Do not create a second one.
- Every page must render a real empty state and a real error state. "Loading…" forever when
  the API 500s is a defect.
- Never render a control the user's permissions do not allow — navigation arrives from the
  server already filtered (ADR-0010), and the same must be true inside the page.
- Commit the client with `--no-verify`; the husky hook fails on pre-existing lint.

---

## §7 — Phase 6: ops, docs and the seams

- `make schema` — regenerate and **commit** `openapi/fusion-integrated.v1.yaml`. CI diffs it.
- `make permissions` — regenerate `registry/permissions.json`, which the IAM seeds from.
- Migrations: reviewed by hand. A data migration that backfills must be idempotent and must
  state what it does when run against an empty table.
- Deployment order must be documented and must work: `migrate` → `seed_modules` → grants →
  your readiness command. A readiness command that names the **unmet prerequisites** (as
  `leave_readiness` does) is required; "module is not ready" without saying why is not.
- Write the module's docs under `docs/[NN]-[module_code]/`: domain model, state machine,
  and whatever else has a genuine reader. Then generate the teaching reference in the shape
  of `docs/09-leave/ELM_REFERENCE.md` via a script under `ops/docs/`, so that every rule and
  use case links to the code that enforces it and the links are **verified to resolve**.

---

## §8 — Definition of done

Not "tests pass". All of it:

1. `make check` green — including `lint-imports`, the three `ops/checks/` scripts,
   `permission_manifest --check` and `schema-check`.
2. `make check-client` green — **wait for `tsc` to finish**; reading `npm test` output
   early has shipped a broken typecheck here before.
3. Every live spec id from Phase 0 is either implemented and cited at its enforcement point,
   or listed in the blueprint as a known gap with a reason. **No retired id is cited
   anywhere in the code.**
4. The module can be turned on from nothing: fresh database → migrate → seed → grant →
   first user action succeeds. Prove it by doing it, not by reasoning about it.
5. The adversarial pass in §5 is done and its findings are either fixed or written down.
6. Every scheduled task has been run manually once and its effect observed.
7. No comment longer than one line anywhere in the diff.
8. No AI attribution anywhere — not in code, comments, commit messages, PR bodies or docs.
   All work is committed under my own GitHub identity.
9. No production data — no roll numbers, names or person ids — in any commit message, PR
   body, issue or doc.

---

## §9 — Standing rules for this session

- **Do not commit, push, or open a PR until I explicitly say so.** An instruction to do it
  once does not carry forward to the next piece of work.
- Do not touch `Fusion/FusionIIIT/Fusion/settings/common.py` or anything in the legacy
  Fusion app. Only the active modules are in scope.
- Do not claim something works because a test is green. Run it, look at the result, and
  report what you actually saw — including the parts that failed.
- If a spec rule and the platform's architecture genuinely conflict, stop and tell me.
  Do not resolve it silently in either direction.
- If you find yourself about to write "this should probably…", that is an open question for
  §3h, not a decision.

--- PROMPT ENDS ---

---

## Appendix — why each rule is in there

Short notes for whoever maintains this document. Every one of these is a bug that actually
happened in Placement or Leave.

| Rule | The incident |
|---|---|
| Add your module to *every* `.importlinter` contract | `domain-is-pure-python` listed only `modules.placement.domain`, so leave's domain was never checked and had drifted. |
| Domain raises plain exceptions, services translate | A bare `Exception` in leave's domain meant a fresh install returned 500 on the very first Apply. |
| Never name a flag `--version` | `seed_leave_policy --version` collided with Django's own flag and threw at parser construction — the command could not be invoked at all. |
| Concurrency tests with real threads | `credit_year` read-then-wrote with no lock and double-credited. 631 green tests did not see it. |
| Constraints in the database, not Python | The fix for the above was a partial unique constraint plus `ignore_conflicts`, not a Python guard. |
| Compare identities, not counts | A completeness check passed at "229 vs 229" while one person was genuinely missing. The same count-vs-identity mistake was made twice. |
| Sync must retire, not only upsert | `sync_directory` only ever inserted, so it held 230 employees while the IAM reported 175. |
| Query parameters are hostile | `?year=abc` returned 500 until `_int_param` was added. |
| One choke point per state change | Leave's scheduler gap was four bugs at once, all because nothing owned the transition into `ONGOING`. |
| The adversarial five | Unit head approving own leave; own request in own queue; balance going negative; unlimited back-dating; a substitute who is themselves away. All found by probing, none by the suite. |
| Verify generated links resolve | A fabricated `BW-EL-13` citation was written for a workflow the spec deliberately retires. |
| Wait for `tsc` | A failing client typecheck was committed because `npm test` output was read before the typecheck finished. |
