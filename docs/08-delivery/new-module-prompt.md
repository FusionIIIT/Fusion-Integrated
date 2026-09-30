---
owner: platform-lead
status: authoritative
last-reviewed: 2026-09-30
purpose: >
  The single prompt used to start any new Fusion-Integrated module from its BR/UC
  specification. Copy §0–§9 verbatim into a new session, fill the five blanks in §0,
  and change nothing else. Uniformity across modules is the point of the document.
---

# New module — the starting prompt

Two modules are already built to this shape: `modules/placement` (largest, the reference)
and `modules/leave` (most rule-dense, the reference for state machines and ledgers).
A third module that does not look like them is a defect, not a style choice.

**How to use this:** copy everything from the `--- PROMPT BEGINS ---` line to the
`--- PROMPT ENDS ---` line into a fresh session. Fill in the five bracketed blanks in §0 —
including `[ENVIRONMENT]`, since §1's reading list depends on it. Do not summarise it, do
not trim it — the length is what keeps modules identical.

---

--- PROMPT BEGINS ---

## §0 — The job

Build the **[MODULE_NAME]** module in `Fusion-Integrated`, from its specification set at
**[SPEC_FOLDER_PATH]**, to the same standard and the same shape as the existing
`modules/placement` and `modules/leave` modules.

- Specification id prefixes: **[ID_PREFIX]** (e.g. `PC-BR-`, `PC-UC-` for Placement;
  `BR-EL-`, `EL-UC-` for Leave).
- Module code / URL segment: **[module_code]** (lowercase, singular-ish, no underscores).
- Environment: **[ENVIRONMENT]** — `full-platform` or `module-only`. See below; get this
  wrong and §1's reading list sends you after files that do not exist on this machine.

This is production code for an institute that will run it for years. "The tests pass" is
not the finish line — §8 is.

Work in phases. **Do not write a line of application code before Phase 2 is approved by me.**

### Stop conditions

Two rules that sit above everything else in this document, because everything else is
negotiable and these are not.

**Stop and report, do not proceed, when:** a required file or spec document is missing or
unreachable; two spec documents contradict each other; a spec rule and the platform's
architecture conflict (§9 restates this — it is here because it is the most common case);
or you would otherwise have to guess the intended behaviour rather than read it. Guessing
and building on the guess is the failure mode every incident in the appendix traces back to
in the end. Report the specific thing that is missing or contradictory; do not reconstruct
what you think was probably meant.

**The one conflict you resolve yourself, silently, no exception:** if following the spec or
matching the reference modules would weaken security or cross a data-isolation boundary —
expose one person's rows to another, skip a permission gate, write to `fusionlab`, add a
credential to a tracked file — refuse it and say why. This is the only priority ordering in
this document; it does not extend to architecture-vs-spec disagreements, which are always
escalated, never decided.

### Which environment you are building in

Two shapes exist, and they are not a spectrum — check `ls ~/Fusion 2>/dev/null` (or wherever
the repos sit) before assuming either.

**`full-platform`** — `Fusion`, `Fusion-client`, `Fusion_System_Administrator` and
`Fusion-Integrated` all checked out, `fusionlab` restored from a production dump or the full
dev fixture. This is the platform lead's machine. §1's shell-reading list is read as written.

**`module-only`** — only `Fusion_System_Administrator` and `Fusion-Integrated`, and
`fusionlab` restored from nothing but the public `fusion-dev.dump` (`Fusion-README`). This is
the lab. Four things follow, all through the rest of this document:

- **No `Fusion-client`, no `Fusion` (legacy) checkout, ever.** §1 names two files that live
  only in `Fusion-client`; do not try to read them — they are not on this machine. The
  self-contained contract is given in §1 instead of the file paths, so nothing about your
  module's correctness depends on that repo existing here.
- **Fusion-Integrated's own `client/` is the complete way to build and demo a module.** It
  runs standalone (`make dev` + `cd client && npm run dev`), needs no portal, and is not a
  fallback — it is where you will do all of Phase 5 either way. What you cannot do here is
  see your module framed inside the real sidebar; that is a `full-platform`-only check, in
  §6's last item, and it is fine to defer it.
- **`fusionlab` is a fixture, not the ERP.** It carries the ~19 tables `fusion-dev.dump`
  ships (`auth_user`, `globals_*`, `programme_curriculum_{batch,course,curriculum,
  discipline,programme}`, the examination and grade tables — check `\dt` if in doubt) and
  nothing else. A field the IAM projects can legitimately be empty here — an academic
  standing, a resume link, a department — because the synthetic data does not populate it,
  not because your code is wrong. Write for that: never let an absent optional field 500 a
  request. `iam/erp_source.py::all_student_profiles` is the concrete example — it now reads
  two tables this fixture does not carry, and skips each independently rather than failing
  the whole projection.
- **A role your spec needs that the fixture does not have is yours to provision, not to wait
  on.** There is no academic office in a lab. `Fusion_System_Administrator`'s admin console
  creates and assigns a real designation with two calls — see §3's "Where roles and
  permissions live" for the exact endpoints. Nothing about this needs `Fusion-client`.

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

**The shell you are plugging into**
This app draws no sidebar of its own. `Fusion-client` is the shell for every Fusion module
and owns the sidebar, the header and the role switcher; your module contributes pages and
nothing else. What you read depends on §0's environment:

**Always — this repo, always present:**
- `client/src/app/Shell.tsx` — `isEmbedded()`. Framed pages render only `<Outlet/>`; nothing
  else about the shell exists in this repo, and nothing here requires `Fusion-client`:
  ```ts
  export function isEmbedded(): boolean {
    // Being framed is the reliable signal; an internal redirect drops the query.
    try {
      if (window.self !== window.top) return true;
    } catch {
      return true;                 // cross-origin parent; only a frame can throw
    }
    return new URLSearchParams(window.location.search).get("embed") === "1";
  }
  ```
- `Fusion_System_Administrator/Backend/backend/iam/services.py` — `modules_by_designation`
  and `navigation_by_designation`. Both the module list and the sidebar are split **per
  designation**; a person acting as one role must never see another role's screens. The IAM
  is present in both environments.

**`full-platform` only:**
- `Fusion-client/src/ui/nav/navigation.js` — how a plugged module is placed and expanded, and
  where `INTEGRATED_MODULES` lives: a **hand-maintained array**, one entry per module
  (`id`, `label`, `icon`, `to`, `section`), separate from anything your `registry.py`
  publishes. Seeding the IAM makes your module *grantable*; it does not make it appear in the
  real sidebar. That needs this one entry added, by whoever has this repo checked out. Record
  the exact fields for it in the blueprint's (e) so it is ready to hand over — in
  `module-only`, this is the one piece of your module you cannot finish yourself.
- `Fusion-client/src/ui/routing/PluggedModule.jsx` — the iframe that frames your pages and
  appends `?embed=1`.

In `module-only`, treat both of those as read about, not read: this section already tells
you what they do. Verify everything else through this repo's own `client/`, which needs
neither of them.

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
behind, what it returns, and which rule ids it enforces. In `module-only`, also write the
`Fusion-client` sidebar entry this module needs (`id`, `label`, `icon`, `to`, `section`) —
you cannot add it yourself, so it must be a clean, complete instruction someone else can
paste into `INTEGRATED_MODULES` without guessing.

**f. Contracts.** What `modules/[module_code]/contracts.py` will expose to other modules,
and what you need added to theirs. Every getter is **plural** — `get_x(ids: Sequence[int])`
— because a singular getter is the one that ends up inside a loop
(`ops/checks/contracts_are_plural.py` enforces this).

**g. Scheduled work.** Each beat entry, its cadence, and what breaks in the real world if it
does not run.

**h. Open questions.** Anything the spec does not settle. Do not guess and do not build on
a guess.

### Where roles and permissions live — settle this before writing (d)

Your module defines **permissions**. It does not define roles, and it owns no access-control
table of any kind. Three databases, three owners, nothing duplicated:

| Database | Owns | Your module |
|---|---|---|
| `fusionlab` (ERP) | people, and which designations they hold | never writes it, never queries it |
| `fusion_system_db` (IAM) | designation → permission, designation → module, module → nav | seeds rows into it, through the manifest only |
| `fusion_integrated` | your business tables | yours, and **no auth tables in it** |

If you find yourself adding a `Role`, `Permission`, `UserRole` or `ModuleAccess` model, stop:
that table already exists in the IAM and a second copy is the thing this architecture exists
to prevent. The same applies if your module is told to live in `fusionlab` under its own
schema — where the *business* tables sit has no bearing on this; RBAC is the IAM's either way.

Rules that follow from it:

- **Roles are institute-wide, not per-module.** `ROLE_GRANTS` is keyed by designation names
  exactly as `globals_designation` spells them — they are the join key, so a typo is a grant
  that silently reaches nobody. Copy the spelling from the ERP, do not retype it.
- **`student`, `faculty` and `staff` are held by definition**, not assigned, and carry no ERP
  row. Grant to them directly when a permission belongs to everyone of that kind.
- **Requesting a new role and provisioning one for your own testing are different acts.**
  Whether the institute should have a "Leave Grievance Officer" post is not yours to decide —
  raise it as an open question in (h), and in production it is created in the ERP by the
  academic office. But you still need that designation to *exist* to test against it, in
  either environment, and waiting on the academic office is not how you do that in dev.

  The write path is `Fusion_System_Administrator`'s own admin console, not a database edit:
  `POST /api/create-role/` (a new `globals_designation` row, operator account, `is_staff` on
  `system_db`) then `PUT /api/update-user-roles/` (assigns it to any test account). Run
  `sync_identity` — or just log that account back in, since a stale projection now refreshes
  itself on login — and the role is live in its session. This works identically in
  `full-platform` and `module-only`; it needs neither `Fusion-client` nor a real institute.
- **Granting a module is a visibility decision.** Do not grant your module to a role "so they
  can look" — it puts your module in that role's sidebar permanently.
- **Permissions are `<module_code>.<singular_noun>.<verb>`**, the verb from the closed list in
  `docs/02-iam/rbac-model.md`. `manage` is an escape hatch; expect to justify it.
- **Only the acting role counts.** Somebody holding two designations gets the permissions of
  one of them at a time, and the sidebar is built per role from that role's own grants. Design
  for the role, never for the person.
- **Permissions decide the verb, scoping decides the rows.** A coordinator limited to one
  department holds the *same* permissions as an unlimited one; the difference lives in
  `selectors/scoping.py`. Never encode a scope as a permission.
- **Publishing is two steps, and the second is the one people forget.** `make permissions`
  writes `registry/permissions.json`; the IAM only applies it when
  `seed_iam_permissions --manifest <path>` runs. Seeding is authoritative for the modules the
  manifest names — a grant you delete is revoked — and scoped to your publisher, so it cannot
  disturb another service's grants. Read what it prints; it names every revoke.

### ERP facts your module needs — list them in (f)

Your module will need things the ERP owns: a CPI, a department, a batch, the staff
directory. It reads none of them from `fusionlab`. The IAM holds the only connection to
that database, as unmanaged models, and exposes what it projects:

| You need | Ask | Never |
|---|---|---|
| who this is, what they may do | the session on the request | — |
| a person's name, kind, discipline | `get_users`, `search_users` | a join to `auth_user` |
| a student's CPI or result standing | `get_academic_standings` | reading the grade tables |
| the student or staff directory | `academic_directory`, `iter_employees` | a second database alias |
| your own data | your models in `fusion_integrated` | — |

If the field you need is not exposed, **the deliverable is an addition to the IAM's
projection and API**, listed in (f) as a dependency — not a `fusionlab` connection from your
module. Two reasons, and the second is the one that bites: a module with that connection can
write to the ERP, so the ERP ends up with two writers and no owner; and the moment two
services compute the same fact from the same rows, the institute has two answers to a
question that has one. Placement's eligibility rule needs a CPI and asks for it; it does not
know which tables a CPI is made of, and that is deliberate.

In `module-only`, expect every one of these calls to answer with less than
`full-platform` would give — `fusion-dev.dump` is a fixture, not the ERP, and a sparse
answer is correct behaviour for it. Test the absent case deliberately; do not treat "it
returned nothing on my machine" as a bug to route around.

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
  entry has no client route or a route has no nav entry. Two further rules, because the
  IAM now builds each role's sidebar from that role alone:
  - **Every nav item carries a `required_permission`.** An item without one appears for
    every role the module is granted to, which is how student screens reached an office.
  - **`ROLE_GRANTS` is the visibility decision, not a convenience.** A role that should see
    none of your screens does not belong in it — granting it "so they can look" puts your
    module in their sidebar permanently.
  - Icons come from the Phosphor set `Fusion-client` renders. A name from another icon pack
    draws a grey circle and nothing else.
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

**How a test gets a principal.** The suite runs with no network and no IAM: `conftest.py`
gives you `stub_iam`, which swaps the IAM client for an in-memory fake, and `make_session`
/ `make_principal`, which mint a session carrying exactly the `permissions`, `modules`,
`roles` and `active_role` you name. You never seed the IAM to write a test, and a test that
needs a running `Fusion_System_Administrator` is a test written wrong.

That convenience is also the trap, so three rules come with it:

- **Every positive test needs its negative twin.** The fake hands out whatever permission
  set you ask for, so "the coordinator can review" proves nothing on its own. The test that
  matters is the principal *without* the code getting a 403.
- **Permission strings in a test are free-form text.** A typo'd code is granted by the fake
  and denied in production — the test passes and the feature is broken. Assert the codes
  your tests use are the ones `registry.PERMISSIONS` declares, in a test that fails when
  they drift apart.
- **Both gates, separately.** A principal with the module grant but not the permission, and
  one with the permission but not the module grant. They are different refusals and only
  one of them is usually implemented.
- **One test for the role switch**: a principal holding two designations must get the acting
  role's view only. That leak reached production once already.
- When the real `IamClient` grows a method, add it to `FakeIam` in the same commit. A fake
  that has drifted is worse than no fake, because the suite stays green while the seam moves.

Required, not optional:

- **The ordinary case, first and by name.** Before the clever tests, write the one for the
  person the module is actually for: the student who holds nothing but `student`, the
  employee with one posting, the row with no optional fields set. Interesting accounts get
  tested because they are interesting; the plain ones carry the traffic. A rule that reads
  "the first office they hold" looks right against every account you built to exercise it
  and refuses every ordinary user in production.
- **A refusal you add must name who it now refuses.** When you introduce a check that fails
  closed, write down the set it excludes and confirm each is meant to be excluded. Both of
  this platform's fail-closed guards needed a floor: the one that refuses a mass
  deactivation, and the one that decides an acting role. Fail closed on the unknown case,
  not on the empty one.
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

- **Build pages, not an application.** `Fusion-client` supplies the sidebar, the header,
  the role switcher and the profile. Your module renders inside it, so it must not ship a
  second one of any of those — two shells means icons, roles and sections kept in step
  twice, and they drift. Anything the portal already owns (the student profile, the resume,
  the notification bell) is not yours to reimplement.
- Use the shared axios instance `client/src/lib/http.ts`. It already carries the session
  cookie and the CSRF header. Do not create a second one.
- Every page must render a real empty state and a real error state. "Loading…" forever when
  the API 500s is a defect.
- Never render a control the user's permissions do not allow — navigation arrives from the
  server already filtered (ADR-0010), and the same must be true inside the page.
- `make check-client` (`typecheck && test && build`) is this repo's actual client gate —
  run it before every commit. There is no pre-commit hook here to bypass; `--no-verify` is
  a `Fusion-client` habit and does nothing useful in this one.
- **`full-platform` only, and only once code is otherwise done:** confirm the module framed
  inside the real portal, not only in this repo's own `client/`. Add the sidebar entry from
  blueprint (e) to `Fusion-client`'s `INTEGRATED_MODULES`, open it there, and check the icon
  renders (Phosphor, not `react-icons` — a name from the wrong set draws a grey circle) and
  that the role switcher shows only what that role was granted.

---

## §7 — Phase 6: ops, docs and the seams

- `make schema` — regenerate and **commit** `openapi/fusion-integrated.v1.yaml`. CI diffs it.
- `make permissions` — regenerate `registry/permissions.json`, which the IAM seeds from.
  Regenerating is half the job: the IAM only revokes a dropped grant when it is re-seeded
  with `manage.py seed_iam_permissions --manifest <path>`. Run it and read what it says it
  revoked.
- `manage.py check --deploy --fail-level WARNING` runs in CI, so a security warning fails
  the build. If your module needs a setting Django warns about, silence that one check by
  id with the reason on the line above it — do not weaken the setting.
- Migrations: reviewed by hand. A data migration that backfills must be idempotent and must
  state what it does when run against an empty table.
- Deployment order must be documented and must work: `migrate` → `seed_modules` → grants →
  your readiness command. A readiness command that names the **unmet prerequisites** (as
  `leave_readiness` does) is required; "module is not ready" without saying why is not.
- Write the module's docs under `docs/[NN]-[module_code]/`: domain model, state machine,
  and whatever else has a genuine reader. Then generate the teaching reference in the shape
  of `docs/09-leave/ELM_REFERENCE.md` via a script under `ops/docs/`, so that every rule and
  use case links to the code that enforces it and the links are **verified to resolve**.

### Changing anything on a running server

These are not module rules; they are how this platform has actually broken. Each one cost
hours on the day it was learned.

- **Find out what the process loads before you edit a file.** `systemctl show <unit> -p
  Environment` and the unit's `ExecStart` are the only authority. This platform's portal
  runs a settings module in `/etc/fusion` that imports `development.py`, so every edit to
  `production.py` was inert — three rounds of downtime before anybody checked.
- **A service being up is not the service working.** `systemctl status` reported `active
  (running)` while the IAM held a placeholder where its password should be, because the
  master process starts fine and the failure is per request. Verify with a request and read
  the status code. Where the service listens on a unix socket, `curl --unix-socket`; a port
  you assumed is a port you have not checked.
- **Say the rollback out loud before you make the change**, and keep it to one line. A copy
  of the file you are about to replace, taken first, is usually the whole plan.
- **A credential more than one service uses changes everywhere in one pass.** Rotating the
  database role broke the portal and the IAM at different minutes because they were updated
  separately; each looked like a fresh incident. List every consumer first — unit files,
  every `.env`, `.pgpass` — then change them together.
- **Never paste a real secret into a command you did not write yourself.** A placeholder
  copied literally put `<new password>` into a live config, and the test that should have
  caught it used the same placeholder, so it "failed" for the wrong reason and sent the
  diagnosis sideways.

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
10. **No credential in a file the repository tracks** — not a password, key, token or app
    password, not "temporarily", not with a comment saying to change it later. They are read
    from the environment. The legacy portal shipped a database password, a mail password and
    a `SECRET_KEY` this way, and the key signed production's session cookies while sitting in
    a public repo for anyone to read.
11. **The plain user is tested**, not only the one with an interesting set of roles. §5's
    first rule.

---

## §9 — Standing rules for this session

- **Do not commit, push, or open a PR until I explicitly say so.** An instruction to do it
  once does not carry forward to the next piece of work.
- Do not touch `Fusion/FusionIIIT/Fusion/settings/common.py` or anything in the legacy
  Fusion app. Only the active modules are in scope.
- **Your module is `modules/[module_code]/`, `client/src/modules/[module_code]/`, its own
  tests and its own doc folder — nothing else is yours by default.** A change to `core/`, to
  another module, to a shared config file, or to CI itself may be genuinely necessary; when
  it is, name the file and the reason and wait, the same as any other approval gate here. Do
  not fold it into the same commit as your module unasked, however small it looks.
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
| Every nav item needs `required_permission` | Navigation was built from the union of a person's permissions, so somebody who was both a student and an office holder saw My Applications and My Offers while acting as the office. |
| `ROLE_GRANTS` decides visibility | `acadadmin` was granted the placement coordinator's permissions "for review", which put Placement Cell in the academic section's sidebar until it was revoked. |
| Icons from the shell's own set | Module icons were named for `react-icons`; the shell renders Phosphor, so every one of them drew a grey circle. |
| Regenerating the manifest is not seeding | A grant removed from `ROLE_GRANTS` stayed live in the IAM until `seed_iam_permissions` was re-run. |
| One shell, not two | A second sidebar and a second student profile were built here before the portal became the shell; both had already drifted from the originals when they were deleted. |
| `X_FRAME_OPTIONS` and the embed | `DENY` blocks the portal from framing these pages. It works in dev only because the dev server sends no header, so the break appears first in production. |
| Test the ordinary user first | An acting-role rule returned "the first office held". Every test account also held an office, so all of them passed; a student holding only `student` resolved to no role and was refused by 175 endpoints. It reached production. |
| A fail-closed check names who it refuses | Same bug, stated as a design rule: the refusal was correct for an unknown role and wrong for an empty one. |
| Read the unit before editing the config | Production loaded a settings module in `/etc/fusion` that imported `development.py`. Every hardening edit to `production.py` was inert, and it took three outages to notice. |
| `active (running)` proves nothing | systemd reported both services healthy while one had a placeholder for a database password; gunicorn's master starts fine and the failure is per request. |
| Rotate a shared credential in one pass | The database role is used by the portal and by the IAM's two connections. Updated at different times, it looked like three separate incidents. |
| A placeholder copied literally | `<new password>` was written into a live `.env`, and the verification command used the same placeholder, so the failure it produced pointed away from the cause. |
| A fixture is not the ERP | `sync_identity` started reading two tables `fusion-dev.dump` does not carry, called unguarded as its first step, and every login in the lab failed before a single user projected. Fixed by treating an absent projected table as absent data, not a crash. |
| A hardcoded sidebar array is a coordination point, not a self-service step | `INTEGRATED_MODULES` in `Fusion-client` needs a manual entry per module. Seeding the IAM's grants was mistaken for the whole job more than once; it is half of it. |
| `--no-verify` does not generalise | Written for `Fusion-client`'s husky hook, it was carried into this repo's own prompt, which has no pre-commit hook to bypass — the instruction did nothing, and would have hidden a real lint failure had one ever existed. |
| Creating a role was untested since the shadow model was written | `globals_moduleaccess` has two `NOT NULL` columns (`thesis_research`, `database`) the IAM's Django model never declared. Every call to the console's own "create a role" 500'd, on `main`, until a lab need for a new designation actually exercised it. |
| A serializer.is_valid() with no else is a silent partial write | The same endpoint returned `201` whether or not the second of its two rows actually saved, because nothing branched on the second check. The first row — the role itself — was real; the second sometimes was not, and the response could not tell you which. |
