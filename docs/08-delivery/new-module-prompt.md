# New module — the starting prompt

One module is already built to this shape: `modules/placement` — the reference. A new
module that does not look like it is a defect, not a style choice.

**How to use this:** copy everything from the `--- PROMPT BEGINS ---` line to the
`--- PROMPT ENDS ---` line into a fresh session. Fill in the five bracketed blanks in §0 —
including `[ENVIRONMENT]`, since §1's reading list depends on it. Do not summarise it, do
not trim it — the length is what keeps modules identical. Every phase below is a numbered
sequence of steps — work top to bottom, do not skip ahead, and do not start a phase's
steps before the previous phase's approval gate (where one exists) has actually cleared.

---

--- PROMPT BEGINS ---

## §0 — The job

Build the **[MODULE_NAME]** module in `Fusion-Integrated`, from its specification set at
**[SPEC_FOLDER_PATH]**, to the same standard and the same shape as the existing
`modules/placement` module.

### Step 0.1 — Confirm what you are building

- Specification id prefixes: **[ID_PREFIX]** (e.g. `PC-BR-`, `PC-UC-` for Placement).
- Module code / URL segment: **[module_code]** (lowercase, singular-ish, no underscores).

This is production code for an institute that will run it for years. "The tests pass" is
not the finish line — §8 is. Work in phases. **Do not write a line of application code
before Phase 2 is approved by me.**

### Rules that sit above every step in this document

Two rules sit above everything else here, because everything else is negotiable and these
are not. They are not a step in the sequence — they apply at every step, in every phase.

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

### Step 0.2 — Determine which environment you are building in

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
  creates and assigns a real designation with two calls — see Step 3.4's "Where roles and
  permissions live" for the exact endpoints. Nothing about this needs `Fusion-client`.

---

## §1 — Phase 0: read, before anything else

Read these in this order and do not skim. You are being asked to match an existing house
style precisely, and you cannot match what you have not read.

### Step 1.1 — Read the platform's own rules

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
this document for shape. If you spot a specific drift, list it at the end of Step 1.4 — do
not fix it mid-task.

### Step 1.2 — Read the reference implementations

- `modules/placement/` in full — this is the shape you are copying. Read
  `domain/clearance.py`, `services/offers.py` and `selectors/` closely even if your module
  has nothing like them yet — they demonstrate the choke-point pattern you will need.
- `core/` in full — `api/exceptions.py`, `api/pagination.py`, `api/csrf.py`,
  `api/throttling.py`, `db/mixins.py`. Anything already here you must reuse, not reinvent.
- `client/src/modules/placement/` — the frontend shape.

### Step 1.3 — Read the shell you are plugging into

This app draws no sidebar of its own. `Fusion-client` is the shell for every Fusion module
and owns the sidebar, the header and the role switcher; your module contributes pages and
nothing else. What you read depends on §0 Step 0.2's environment:

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
  the exact fields for it in the blueprint's Step 3.5 (e) so it is ready to hand over — in
  `module-only`, this is the one piece of your module you cannot finish yourself.
- `Fusion-client/src/ui/routing/PluggedModule.jsx` — the iframe that frames your pages and
  appends `?embed=1`.

In `module-only`, treat both of those as read about, not read: this section already tells
you what they do. Verify everything else through this repo's own `client/`, which needs
neither of them.

### Step 1.4 — Read and inventory the specification

Read every document in the spec folder. Build an inventory before you interpret anything:

1. How many business rules exist, and **which ids the spec explicitly retires**. Retired ids
   are a trap: some retirements moved the behaviour to a requirement id rather than dropping
   the behaviour. Record which is which.
2. How many use cases, and which are retired.
3. The workflow ids (basis and composite) and their current naming.
4. The requirement ids, if the spec has a separate requirements layer.
5. Whether the traceability matrix's mapping columns are actually populated. If they are
   empty, say so and derive coverage by reading each rule — never by trusting the matrix.
6. **Every actor named anywhere in the business rules, use cases, and workflows** — this
   inventory is what Step 2.4 builds the role list from if no role list is handed to you
   directly, so build it carefully here even if you think you already know the roles.

### Step 1.5 — Report back

At the end of Phase 0, tell me: the artefact counts, the retired ids with their
replacements, any internal contradiction between two spec documents, and any rule that
cannot be implemented as written. **Do not invent an id that the spec does not contain**,
and do not cite a retired id as if it were live.

---

## §2 — Phase 1: the questions that must be answered before code

Some specs are written against assumptions Fusion does not hold. Surface these now, not in
review. Answer what you can from the code; ask me the rest as a short numbered list.

### Step 2.1 — Is this one bounded context?

If the answer is "mostly", it is two modules.

### Step 2.2 — What does it need from other modules?

Every answer becomes a function on *their* `contracts.py`, agreed with them. A long list
means the boundary is wrong.

### Step 2.3 — Identity

Fusion's identity lives in a *different database*, reached over HTTP
(`fusion_auth/client.py`), projected locally by `modules/directory`. If a spec says
"foreign key to Employee" or "request.user.employee", it is describing a system we do
not have. Every person reference in your module is a **plain integer `user_id`**
(`core/db/mixins.py::UserScopedModel`). No exceptions.

### Step 2.4 — Who decides, and who may see

List every role in the spec and map it to a designation as it actually exists in
`globals_designation`, plus the basic `student` / `faculty` / `staff` kinds.

- **If the role list is given to you** — by the spec, by whoever assigned you the module, or
  by me directly — use it as given. Do not second-guess a given role list against the use
  cases; that is relitigating a decision that was already made.
- **If it is not given to you, derive it yourself** from the actor inventory you built in
  Step 1.4.6: read every business rule, use case, and workflow document, and list every
  actor named as performing or approving a step — "the coordinator reviews",
  "the employee submits", "HR escalates" each name a role. Build the role list from that
  inventory, not from guessing what a module like this "usually" needs. **Cite the BR/UC/
  workflow id next to every role you derive this way** — a role with no citation is a role
  you invented, not one you read.
- Either way, a role the IAM cannot express is a blocker, not a detail. Surface it here, in
  Phase 1's questions — do not quietly invent a designation that does not exist in
  `globals_designation`, and do not carry an unresolved role into Step 3.4's permission list.

### Step 2.5 — Scope

For each read endpoint: whose rows does this person see? The answer becomes
queryset narrowing in `selectors/scoping.py`, which yields **404, never 403** — a 403
confirms the row exists to someone who should not know that.

### Step 2.6 — Time

Does anything expire, escalate, credit annually, or advance on a date? That is
a Celery beat entry in `schedule.py`, and beat *must* be running in production. If
nothing in the module needs a clock, say so explicitly.

### Step 2.7 — Money / quota / balance

If the module counts anything a person can spend, it is an **append-only ledger**, not a
balance column. Corrections are reversing entries, never an edit to a past row.

### Step 2.8 — Policy

Anything an administrator configures is **effective-dated and never edited** — superseded by
a new version. A module with no seeded policy must not 500 on first use; it must say what is
missing, and that gap belongs in the blueprint's Step 3.8 (h) open questions.

---

## §3 — Phase 2: the blueprint (deliverable, needs my approval)

Write `docs/[NN]-[module_code]/[module_code]-blueprint.md` **before any code**. Each step
below is one section of that document, in this order.

### Step 3.1 (a) — Traceability table

One row per live business rule and per live use case:

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |

The "layer" column is the design decision. A rule that lands in `api/` is almost always
misplaced — API is transport, not policy.

### Step 3.2 (b) — Domain model

Entities, their fields, their invariants. Name the constraints you will push into the
database (`UniqueConstraint`, `CheckConstraint`, partial unique indexes) as opposed to
enforcing in Python. Anything that must hold under concurrency belongs in the database.

### Step 3.3 (c) — State machine, if the module has one

A **declarative transition table** — a data structure listing (state, event, actor) → state.
Not a chain of `if` statements. An illegal transition must be *inexpressible*, not merely
rejected.

### Step 3.4 (d) — Permission list

The exact `registry.py` content: `MODULE`, `PERMISSIONS`, `SYSTEM_PERMISSIONS` (bare
strings, for scheduled work no human holds), `SCOPE_PERMISSIONS`, and `ROLE_GRANTS` keyed
by real designation names, built from Step 2.4's role list (given or derived — either way,
every role here should trace back to that step, with citations if it was derived).

**Settle this before writing Step 3.4.** Your module defines **permissions**. It does not
define roles, and it owns no access-control table of any kind. Three databases, three
owners, nothing duplicated:

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
  raise it as an open question in Step 3.8 (h), and in production it is created in the ERP by
  the academic office. But you still need that designation to *exist* to test against it, in
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

### Step 3.5 (e) — Endpoint list

Method, path under `/api/v1/[module_code]/`, the two gates it sits behind, what it returns,
and which rule ids it enforces. In `module-only`, also write the `Fusion-client` sidebar
entry this module needs (`id`, `label`, `icon`, `to`, `section`) — you cannot add it
yourself, so it must be a clean, complete instruction someone else can paste into
`INTEGRATED_MODULES` without guessing.

### Step 3.6 (f) — Contracts

What `modules/[module_code]/contracts.py` will expose to other modules, and what you need
added to theirs. Every getter is **plural** — `get_x(ids: Sequence[int])` — because a
singular getter is the one that ends up inside a loop
(`ops/checks/contracts_are_plural.py` enforces this).

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
projection and API**, listed here in Step 3.6 as a dependency — not a `fusionlab` connection
from your module. Two reasons, and the second is the one that bites: a module with that
connection can write to the ERP, so the ERP ends up with two writers and no owner; and the
moment two services compute the same fact from the same rows, the institute has two answers
to a question that has one. Placement's eligibility rule needs a CPI and asks for it; it does
not know which tables a CPI is made of, and that is deliberate.

In `module-only`, expect every one of these calls to answer with less than `full-platform`
would give — `fusion-dev.dump` is a fixture, not the ERP, and a sparse answer is correct
behaviour for it. Test the absent case deliberately; do not treat "it returned nothing on my
machine" as a bug to route around.

### Step 3.7 (g) — Scheduled work

Each beat entry, its cadence, and what breaks in the real world if it does not run.

### Step 3.8 (h) — Open questions

Anything the spec does not settle, including any role from Step 2.4 the IAM cannot express
and any policy from Step 2.8 with nothing seeded yet. Do not guess and do not build on a
guess.

Stop here. Wait for my approval before Step 4.1.

---

## §4 — Phase 3: backend, in layer order

Build strictly bottom-up. Each layer below is one step, and each step must be complete and
tested before the next one starts.

```
modules/[module_code]/
├── __init__.py  apps.py  contracts.py  registry.py  schedule.py  tasks.py
├── domain/          framework-free Python: rules, state machine, calculations
├── models/          Django models, one file per aggregate, package not module
├── selectors/        all reads, including scoping.py
├── services/         all writes, one file per use-case family
├── api/              views.py serializers.py urls.py (+ permissions.py if it needs
│                    its own gate classes if it needs one)
├── management/commands/
├── migrations/
└── tests/
```

Layer rules, enforced by `.importlinter` (add your module to the existing contracts — the
`domain-is-pure-python` and `modules-only-touch-contracts` contracts each list modules
explicitly, and a module you forget to add is a module that is **never checked**):

### Step 4.1 — `domain/`

Imports no Django, no DRF, no Celery. Pure functions and dataclasses. It may raise plain
exceptions; the **service layer** translates them into `core.api.exceptions` types. Never
import `core.api.exceptions` from `domain/`.

### Step 4.2 — `models/`

May import `domain/`. No `ForeignKey` crosses a module boundary, ever
(`ops/checks/no_cross_module_fk.py`). Use `TimeStampedModel` / `UserScopedModel`.

### Step 4.3 — `selectors/`

Returns querysets and read DTOs. No writes. `scoping.py` owns visibility and every list
endpoint starts from it.

### Step 4.4 — `services/`

Owns every write. Rules:

- One transactional choke point per state change. If there is a workflow, *all* movement
  goes through one function that takes `select_for_update`, refuses a terminal source
  state, refuses the wrong actor, writes the audit trail, and emits any ledger entry — in
  one transaction. Two paths into the same state is how the rules drift apart.
- Raise `DomainError` subclasses from `core/api/exceptions.py` with a `code=`. The message
  is read by a person at IIITDMJ; write it as a sentence that tells them what to do next.
- **Order the refusals deliberately.** When two checks can both fail, the one whose message
  is more useful goes first.

### Step 4.5 — `api/`

Transport only: parse, delegate, serialise. Two gates on every endpoint — the module grant
first, then the permission. Query parameters are hostile input: an unparseable `?year=abc`
is a **400, never a 500**.

### Step 4.6 — `registry.py`

As designed in Step 3.4. `nav_matches_routes.py` will fail CI if a nav entry has no client
route or a route has no nav entry. Two further rules, because the IAM now builds each
role's sidebar from that role alone:

- **Every nav item carries a `required_permission`.** An item without one appears for
  every role the module is granted to, which is how student screens reached an office.
- **`ROLE_GRANTS` is the visibility decision, not a convenience.** A role that should see
  none of your screens does not belong in it — granting it "so they can look" puts your
  module in their sidebar permanently.
- Icons come from the Phosphor set `Fusion-client` renders. A name from another icon pack
  draws a grey circle and nothing else.

### Step 4.7 — `schedule.py`

Exports `BEAT_SCHEDULE` and `TASK_ROUTES`; register both in `config/celery.py`. Each module
owns its own timers so a module stays removable.

### Step 4.8 — Management commands

For anything an operator must do: seeding policy, a readiness check, a manual run of each
scheduled task. Never name a flag `--version` — it collides with Django's own and the
command becomes uninvokable at parser construction.

Comments: **single line only, and only where the reason is not obvious from the code.**
If it will not fit on one line it belongs in `docs/`. This applies to `#`, `//`, JSX
comments and docstrings alike. A docstring that restates the function name is noise.

---

## §5 — Phase 4: tests that would actually catch a bug

Mirror `modules/placement/tests/` — one file per concern, named for the concern.

### Step 5.1 — Set up how a test gets a principal

The suite runs with no network and no IAM: `conftest.py` gives you `stub_iam`, which swaps
the IAM client for an in-memory fake, and `make_session` / `make_principal`, which mint a
session carrying exactly the `permissions`, `modules`, `roles` and `active_role` you name.
You never seed the IAM to write a test, and a test that needs a running
`Fusion_System_Administrator` is a test written wrong.

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

### Step 5.2 — Write the ordinary case first, by name

Before the clever tests, write the one for the person the module is actually for: the
student who holds nothing but `student`, the employee with one posting, the row with no
optional fields set. Interesting accounts get tested because they are interesting; the
plain ones carry the traffic. A rule that reads "the first office they hold" looks right
against every account you built to exercise it and refuses every ordinary user in
production.

### Step 5.3 — Domain tests

With no database. Every branch of every rule.

### Step 5.4 — State machine tests

Assert that every illegal transition is *refused*, enumerated from the transition table
rather than hand-picked.

### Step 5.5 — Privilege escalation tests (`test_privilege_escalation.py`)

For each endpoint, a principal who should not reach it, asserting 403 or 404 as designed.

### Step 5.6 — Scoping isolation tests (`test_recruiter_isolation.py` is the model)

Person A must not see person B's rows, including through a filter, a search and an export.

### Step 5.7 — Concurrency tests

For anything that credits, allocates, or must happen once. Run real threads against the
real database. Green single-threaded tests prove nothing here — a double-credit bug in
leave survived 631 passing tests and was only ever found this way.

### Step 5.8 — Query budget tests (`test_query_budgets.py`)

Assert a maximum query count per list endpoint so an N+1 fails CI instead of production.

### Step 5.9 — Schedule tests

Assert every beat entry your module registers is actually present in `config/celery.py`'s
merged schedule.

### Step 5.10 — Write down a refusal's excluded set

A refusal you add must name who it now refuses. When you introduce a check that fails
closed, write down the set it excludes and confirm each is meant to be excluded. Both of
this platform's fail-closed guards needed a floor: the one that refuses a mass
deactivation, and the one that decides an acting role. Fail closed on the unknown case,
not on the empty one.

### Step 5.11 — Adversarial pass

Before you tell me it is done, spend a deliberate pass trying to break your own module as a
malicious insider. Specifically ask: can an approver approve their own record? Can a thing
appear in its own approval queue? Can a balance go negative? Can something be back-dated
without limit? Can a required third party be someone who is themselves unavailable? Each of
those five was a real hole in leave that the test suite did not see.

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

### Step 6.1 — Build pages, not an application

`Fusion-client` supplies the sidebar, the header, the role switcher and the profile. Your
module renders inside it, so it must not ship a second one of any of those — two shells
means icons, roles and sections kept in step twice, and they drift. Anything the portal
already owns (the student profile, the resume, the notification bell) is not yours to
reimplement.

### Step 6.2 — Use the shared HTTP client

Use the shared axios instance `client/src/lib/http.ts`. It already carries the session
cookie and the CSRF header. Do not create a second one.

### Step 6.3 — Render real empty and error states

Every page must render a real empty state and a real error state. "Loading…" forever when
the API 500s is a defect.

### Step 6.4 — Never render a control permissions do not allow

Navigation arrives from the server already filtered (ADR-0010), and the same must be true
inside the page.

### Step 6.5 — Run the client gate before every commit

`make check-client` (`typecheck && test && build`) is this repo's actual client gate — run
it before every commit. There is no pre-commit hook here to bypass; `--no-verify` is a
`Fusion-client` habit and does nothing useful in this one.

### Step 6.6 — Confirm inside the real portal (`full-platform` only, once code is otherwise done)

Confirm the module framed inside the real portal, not only in this repo's own `client/`.
Add the sidebar entry from the blueprint's Step 3.5 (e) to `Fusion-client`'s
`INTEGRATED_MODULES`, open it there, and check the icon renders (Phosphor, not
`react-icons` — a name from the wrong set draws a grey circle) and that the role switcher
shows only what that role was granted.

---

## §7 — Phase 6: ops, docs and the seams

### Step 7.1 — Regenerate and commit the API schema

`make schema` — regenerate and **commit** `openapi/fusion-integrated.v1.yaml`. CI diffs it.

### Step 7.2 — Regenerate and seed permissions

`make permissions` — regenerate `registry/permissions.json`, which the IAM seeds from.
Regenerating is half the job: the IAM only revokes a dropped grant when it is re-seeded
with `manage.py seed_iam_permissions --manifest <path>`. Run it and read what it says it
revoked.

### Step 7.3 — Clear the deploy-check gate

`manage.py check --deploy --fail-level WARNING` runs in CI, so a security warning fails
the build. If your module needs a setting Django warns about, silence that one check by
id with the reason on the line above it — do not weaken the setting.

### Step 7.4 — Review migrations by hand

A data migration that backfills must be idempotent and must state what it does when run
against an empty table.

### Step 7.5 — Document and prove the deployment order

Deployment order must be documented and must work: `migrate` → `seed_modules` → grants →
your readiness command. A readiness command that names the **unmet prerequisites** is
required; "module is not ready" without saying why is not.

### Step 7.6 — Write the module's docs

Write the module's docs under `docs/[NN]-[module_code]/`: domain model, state machine,
and whatever else has a genuine reader. Then generate a teaching reference tracing every
rule and use case to the code that enforces it, via a script under `ops/docs/`, so that
every link is **verified to resolve**.

### Changing anything on a running server

These are not steps in the module's own sequence; they are how this platform has actually
broken, and they apply any time this phase touches a live service. Each one cost hours on
the day it was learned.

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
5. The adversarial pass in Step 5.11 is done and its findings are either fixed or written
   down.
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
11. **The plain user is tested**, not only the one with an interesting set of roles. Step
    5.2's rule.

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
  Step 3.8 (h), not a decision.

--- PROMPT ENDS ---

---
