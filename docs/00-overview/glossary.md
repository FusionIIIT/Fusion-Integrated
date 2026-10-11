---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Glossary

The project's ubiquitous language. These words mean **exactly** this in code, in documents, in API
field names and in conversation. Where a term collides with a legacy Fusion word that means something
different, the collision is called out — those are the ones that cause bugs.

---

## Identity & access

**Principal** — the authenticated actor on a request. Either a human (`identity_user`) or a service
(`kind = service`). Code says `request.principal`, never `request.user`, in the new services, so it is
obvious when something is relying on Django's stock user.

**IAM** — `fusion-iam`, the central identity service. Sole authority on credentials, sessions, roles,
permissions, module grants and audit.

**ERP** — the legacy Fusion monolith and its database (`fusion_newui_prod` in production, `fusionlab`
in development). Holds `auth_user` and all 424 legacy models. The platform reads it; only the
projector writes to a narrow allowlist of its tables.

**Permission** — an atomic capability, coded `<module>.<resource>.<action>`, e.g.
`placement.offer.issue`. Permissions are the only thing authorization checks look at. They are
declared in code and catalogued in [permission-catalog.md](../02-iam/permission-catalog.md).

**Role** — a named bundle of permissions, e.g. `placement_coordinator`. Roles may inherit from other
roles. Users hold roles; users never hold permissions directly.

**Designation** *(legacy)* — the ERP's word for a role (`globals_designation`). Not the same thing as
a Role: a Designation is a name string with no permissions attached, and
`globals_holdsdesignation` has a `unique_together ('working', 'designation')` constraint meaning
**only one person institute-wide can hold a given designation**. Use "Role" for the new model and
"Designation" only when talking about the legacy table. See
[legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md).

**Active role** — the single role a user is currently acting as. A user may hold several
(`student` and `placement_coordinator`); the sidebar and the permission set are derived from the
active one. Switching is a server operation (`PATCH /me/active-role`) that re-validates the holding —
the client cannot grant itself a role by asking.

**Scope** — an optional qualifier on a role assignment: `(scope_type, scope_id)`, e.g.
`('department', 'CSE')`. A scoped role's permissions apply only to objects inside that scope. The
legacy Designation model has no equivalent, which is the root of hazard **H1**.

**Officiating** — an `assignment_kind` for someone temporarily holding a role for its permanent
holder. Mirrors the ERP's `HoldsDesignation.user` (permanent) vs `working` (currently acting)
distinction, which legacy code applies inconsistently.

**Module** — a top-level functional area that appears as a sidebar section: `placement_cell`, `hr`,
`leave`, `sysops`. Registered in `registry_module`. A module is granted to a role; a module granted
to nobody is invisible **and unroutable** — the frontend produces no route for it at all.

**Module grant** — a `(role, module)` row saying "this role may see and enter this module". Replaces
the legacy `globals_moduleaccess` one-boolean-column-per-module table.

**Permission version (`pv`)** — a monotonic counter bumped whenever anything affecting a user's
effective permissions changes. It is embedded in cache keys and in the access token, so
invalidation is free: a new version simply misses the old key. Never delete a permission cache entry.

**Projection** — the one-way write of IAM state into the legacy `globals_*` tables so the untouched
monolith keeps working. IAM → ERP only. Never the reverse.

**Reconciler** — the nightly job that diffs IAM against the ERP projection and reports (later
enforces) drift.

---

## Academic integration

These five terms are the most bug-prone in the whole system. Read
[academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md) before using
any of them.

**Declaration** — the administrative act of publishing a semester's results for a batch. In the ERP
it is an `examination.ResultAnnouncement` row keyed `(batch, semester, semester_type)` with
`announced = True`, optionally narrowed to an explicit roll-number allow-list
(`PublishedResultStudent`). **A declaration is the only event that makes a CPI usable by Placement.**

**Declared** vs **provisional** — a grade exists in the ERP the moment a professor uploads it, and the
ERP's CPI function does not filter on `verified`. So a CPI can exist for a semester nobody has
declared. Placement **only ever** sees declared values. "Provisional" is anything not covered by an
announced declaration.

**Snapshot** — an immutable `academics.ResultSnapshot` row: one student's SPI, CPI, credits and
backlogs *as computed by the ERP at the moment of declaration*. Postgres `UPDATE`/`DELETE` privileges
are revoked on this table for the application role. Snapshots are the audit trail behind every
eligibility decision.

**Standing** — `academics.StudentAcademicStanding`, one row per student, holding the values from
their **latest declared** semester. This is the only thing eligibility rules read. Derived from
snapshots; never written by hand.

**`declared_seq`** — the total ordering key for declarations: `semester * 10 + {Odd: 0, Even: 1,
Summer: 2}`. It exists because the ERP stores **summer semesters under an even semester number** and
labels them `Summer {semester // 2}` — so `(4, "Summer Semester")` renders as "Summer 2" and is a
*different* declaration from `(4, "Even Semester")` = "Semester 4". Ordering by `semester` alone
cannot tell them apart. `declared_seq` reproduces the ERP's own `semester_type_order` ordering.

**Retraction** — un-declaring a result (`announced` set back to `False`, or the announcement deleted).
Standing is recomputed from the highest non-retracted declaration and affected in-flight applications
are **flagged for human review, never auto-rejected**.

**Grade semantics** (the ERP's, which we adopt verbatim and must not "fix"):

| Grade | Grade points | Counts toward earned credits? | In the CPI average? |
|---|---|---|---|
| `O`, `A+` | 10.0 | yes | yes |
| `A` … `D` | 9.0 … 3.0 | yes | yes |
| **`F`** | **2.0** | **yes** | **yes** |
| `S` | — | **yes** | **no** |
| `X`, `CD`, `I`, `AU` | — | **no** | **no** |

`S` is a pass/fail credit. `X`/`CD` are absent from the ERP's `grade_conversion` dict and therefore
excluded from everything. **`F` is not zero** — it earns 2.0 points and contributes its credit to the
denominator. Any downstream system that assumes F is zero will disagree with Fusion.

**Earned credits** (`total_unit`) — credits including `S`-graded courses. **CPI denominator credits**
(`total_credits`) — credits excluding `S` and `X`. Both are stored; they are different numbers and
conflating them produces a wrong CPI.

**Batch** — a cohort, keyed `(programme name, discipline, admission year)` in
`programme_curriculum.Batch`, e.g. "B.Tech - CSE 2023". Declarations are per-batch. Note the ERP trap:
`Student.batch_id` is a **foreign key to Batch** (column `batch_id_id`), while `Student.batch` is an
unrelated integer holding the admission year.

---

## Placement

**Placement year** — a season, e.g. `2026-27`. Every posting, registration, offer and record belongs
to exactly one. Policy is set per year.

**Placement policy** — the per-year rule set: how many offers a student may hold, what happens to
them after their first offer, the dream-offer threshold, the minimum CPI to register.

**Registration** — a student opting in to a placement year. A precondition for applying to anything.

**Posting** (`JobPosting`) — one advertised opportunity from one company in one placement year:
title, CTC, seats, eligibility rule, application window. Not the same as a "drive".

**Drive** — informal, and therefore **avoided in code**. In conversation it usually means "a company's
on-campus process", which in the model is a Posting plus its `SelectionRound` rows. Prefer "posting"
or "the rounds for a posting".

**Eligibility rule** — a small JSON AST on a posting (`{"all": [{"gte": ["cpi", 7.0]}, …]}`)
evaluated against a student's Standing, UserRef and Registration. **Fail-closed**: unknown field,
missing standing or evaluation error ⇒ ineligible with an explicit reason. Frozen
(`eligibility_rule_locked_at`) when the posting is published — rules cannot change after applications
open.

**Evaluation** — a cached `(posting, student) → eligible?` result plus the per-rule failure list, so
the student is told *"CPI 6.8 < 7.0 required"* rather than "not eligible". Keyed by `inputs_version`,
so a standing change invalidates it automatically.

**Application** — a student's submission to a posting. Has a strict state machine; every transition
appends an `ApplicationTransition` audit row.

**Round** (`SelectionRound`) — one stage of a posting's process (test, GD, technical, HR), with a
sequence number, a mode and a schedule. **Participation** is a student's outcome in a round.

**Shortlisting** — a coordinator promoting applications from `UNDER_REVIEW` to `SHORTLISTED`.

**Offer** — a company's job offer to a student for a posting, carrying its CTC, tier and a response
deadline.

**Tier** — a company classification with a **rank**, where a *lower rank number means a better
company* (rank 1 is the top tier). Used by the tier-upgrade offer policy. Set on `Company`, copied
onto the `Offer` at issue time so a later re-tiering cannot retroactively change past decisions.

**Dream offer** — an offer at or above the placement year's `dream_threshold_lpa`. Under the
`dream_only` policy, an already-placed student may accept a second offer **only** if it is a dream
offer and they do not already hold one.

**Supersede** — what happens to a previously accepted offer when a student legitimately upgrades. The
old offer moves to `superseded` and its `PlacementRecord` is deactivated. The student is never
recorded as holding two active records — a partial unique index enforces it in the database.

**Placement record** — the canonical "this student is placed at this company for this year" fact. At
most one active row per `(user, placement_year)`.

**Debarred** — a registration status blocking a student from accepting anything, usually for a
policy violation. Distinct from `opted_out`, which is voluntary.

**Policy decision** — the machine-readable `Decision` object persisted on every offer acceptance
attempt (`allow`/`deny`, a reason code, and the numbers involved). Exists so an appeal can be
answered from data instead of from memory.

---

## Platform mechanics

**Module** *(backend sense)* — a bounded context under `services/platform/modules/`. Same word as the
sidebar sense above, and deliberately so: they are one-to-one.

**Contracts** (`contracts.py`) — a module's **only** public surface to other modules. Functions are
**plural by signature** (`get_employments(user_ids)`, not `get_employment(user_id)`) so an N+1 is
impossible to write.

**Selector** — a read function. Owns its `select_related`/`prefetch_related`. Never writes.

**Service** — a write function. Owns the transaction boundary and emits events. Never called from
another module directly.

**Domain** — pure Python: entities, value objects, rules, state machines. Importing Django from
`domain/` fails CI. This is what keeps the rules unit-testable at 90%.

**Shared kernel** (`core/`) — the small set of genuinely universal utilities. Admission is
deliberately hard; see [shared-kernel-reference.md](../03-platform/shared-kernel-reference.md).

**ACL (anti-corruption layer)** — `modules/academics`, which translates ERP concepts into platform
concepts and is the *only* place ERP shadow models may be imported.

**Outbox / inbox** — the transactional event pattern. A write and its event commit in one
transaction (`outbox_event`); a consumer records `dedupe_key` before acting (`inbox_event`), making
redelivery a no-op.

**`UserRef`** — `modules/directory`'s local projection of IAM users (id, username, name, kind,
department, batch). Lets the platform join on users without a cross-database foreign key.

**Version-in-key caching** — cache keys embed a version (`pv`, `inputs_version`, `standing_version`)
and entries are **never deleted**. Removes the "forgot to invalidate" bug class entirely.

---

## Frontend

**Shell** — `apps/shell`, the single SPA. Owns login, layout, routing and the module registry.

**Manifest** — a frontend module's declaration: its code, base path, lazy loader and index
permission. Its `code` **must** equal the backend `registry_module.code`.

**Navigation contract** — the `navigation` array in the `/me` response, already filtered and already
in render shape. The client does **zero** filtering. See
[navigation-contract.md](../05-frontend/navigation-contract.md).

**`packages/ui`** — the design system extracted verbatim from the `Fusion_System_Administrator`
client. `AppShellLayout.module.css` is a byte-identical copy of the original and **is** the visual
contract; Playwright screenshot baselines prove it.

---

## Words we do not use

| Avoid | Use instead | Why |
|---|---|---|
| "drive" (in code) | "posting", "rounds for a posting" | Ambiguous; means different things to different offices |
| "user" (in new services) | "principal" | Distinguishes the new model from Django's stock `auth_user` |
| "designation" (for new roles) | "role" | Reserved for the legacy table, which has different semantics |
| "CPI" unqualified | "declared CPI (Sem N)" | An unqualified CPI is ambiguous between provisional and declared |
| "sync" (for IAM→ERP) | "projection" | "Sync" implies bidirectional. It is strictly one-way. |
| "microservice" | "service" or "deployable" | We have two deployables and no microservice architecture |
| "SPI" as a synonym for CPI | keep them distinct | SPI is one semester; CPI is cumulative. The ERP computes them differently — SPI does no dedup and no replacement handling. |
