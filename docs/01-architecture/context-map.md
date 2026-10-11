---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Context Map

The bounded contexts and, for each pair that touches, the **relationship pattern**. The pattern is
what tells you who is allowed to break whom, and therefore what a change to one side obliges you to
do on the other.

## Patterns used here

| Pattern | Meaning in practice |
|---|---|
| **Published Language** | Upstream publishes a versioned, documented contract. Downstream depends on the contract, never on internals. Breaking it is a versioned event. |
| **Anti-Corruption Layer (ACL)** | Downstream wraps a messy upstream and translates its concepts. Nothing outside the ACL may know the upstream's vocabulary. |
| **Conformist** | Downstream accepts upstream's model as-is, with no translation, because translating would cost more than it is worth. |
| **Customer/Supplier** | Two teams; downstream's needs are negotiated into upstream's plan. Here it means: one module may ask another to add a `contracts.py` function. |
| **Shared Kernel** | A small body of code both sides own jointly. Changing it requires agreement from both. Kept deliberately tiny. |

## The map

```
                              ┌──────────────────────┐
                              │       IAM            │  upstream of everything
                              │  identity · RBAC ·   │
                              │  modules · audit     │
                              └───┬──────────┬───────┘
              Published Language  │          │  Projection (one-way, ACL on write)
                                  ▼          ▼
                       ┌────────────────┐   ┌───────────────────────────┐
                       │   DIRECTORY    │   │  LEGACY ERP (globals_*)   │
                       │  UserRef proj. │   │  Conformist, write-narrow │
                       └───┬────────────┘   └───────────────────────────┘
                           │ Published Language (contracts.py)
        ┌──────────────────┼───────────────────┬──────────────────┐
        ▼                  ▼                   ▼                  ▼
  ┌───────────┐     ┌────────────┐      ┌───────────┐      ┌───────────┐
  │ PLACEMENT │◄────│ ACADEMICS  │      │    HR     │◄─────│   LEAVE   │
  │           │     │   (ACL)    │      │           │      │           │
  └───────────┘     └─────┬──────┘      └───────────┘      └───────────┘
                          │ ACL over a messy upstream
                          ▼
              ┌────────────────────────────────┐
              │  LEGACY ERP (examination,      │
              │  academic_information, ocms)   │  READ-ONLY
              └────────────────────────────────┘

        all of the above ──── Shared Kernel ────► core/ + fusion_contracts
```

---

## Context inventory

| Context | Home | Owns the answer to |
|---|---|---|
| **IAM** | `services/iam` | Who is this? What roles do they hold? What may they do? Which modules do they see? |
| **Directory** | `modules/directory` | Within the platform, who is user 1234 — name, kind, department, batch? |
| **Academics** | `modules/academics` | What is this student's *declared* academic standing? |
| **Placement** | `modules/placement` | Companies, postings, eligibility, applications, rounds, offers, records, statistics |
| **HR** | `modules/hr` | Employees, appointments, employment status |
| **Leave** | `modules/leave` | Leave types, balances, requests, approvals |
| **Legacy ERP** | the monolith | Everything academic. Authoritative and untouched. |
| **Sysops** | `services/sysops` (Phase 7) | Backups, archives, batch onboarding, schema operations |

---

## Relationships, pair by pair

### IAM → everything · **Published Language**

IAM publishes three contracts and nothing else:

1. **The access token** — RS256 JWT with claims `sub`, `erp_uid`, `sid`, `rol`, `mod`, `pv`, `amr`,
   `aud`, `exp`, `iat`, `kid`. Validated locally against JWKS.
2. **`GET /api/iam/v1/me`** — the session payload, including navigation in render shape.
3. **Events** — `iam.user.*`, `iam.role.*`, `iam.module.*`, `iam.session.*`.

Consumers **MUST NOT** read `iam.*` tables directly, ever, even though the platform could reach them
over the same Postgres cluster. Adding a claim is backwards-compatible; removing or re-typing one is a
new token version and a coordinated release.

### IAM → Legacy ERP `globals_*` · **Projection, one-way, ACL on the write side**

IAM writes `globals_designation`, `globals_holdsdesignation` and `globals_moduleaccess` so the
untouched monolith keeps working. This is **Conformist**: IAM accepts the legacy schema exactly as it
is and does not ask it to change.

Three hazards make this the most fragile edge in the map, and all three are properties of the legacy
schema rather than of our design:

- **H1** — `unique_together ('working','designation')` allows only one holder per designation
  institute-wide, so scoped and multi-holder roles cannot be represented.
- **H2** — production has columns added by raw DDL that no monolith migration knows about.
- **H3** — `ExtraInfo.last_selected_role` is `max_length=20` while role names may be longer.

Fully specified, with the projection rules and the reconciler, in
[legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md).

> **Direction is absolute.** ERP → IAM never happens. If someone edits
> `globals_holdsdesignation` by hand, the nightly reconciler reports it as drift and (from Phase 4)
> overwrites it. That is the intended behaviour, and it is why the console's write endpoints return
> `410 Gone` from Phase 4 onward.

### Academics → Legacy ERP · **Anti-Corruption Layer**

The most important ACL in the system, because the upstream vocabulary is genuinely hostile:

| ERP concept | Why it needs translating | Platform concept |
|---|---|---|
| CPI recomputed per request from `online_cms.Student_grades`, with `S` earning credit but not average, `X`/`CD` excluded entirely, and **`F` worth 2.0 points** | Any reimplementation would disagree | `ResultSnapshot`, pulled from the ERP's own function |
| `Student.cpi` — permanently `0.0` | A trap that already caught the old placement module | never read |
| `Spi` table — zero writers | Empty | never read |
| Summer semesters stored under **even** `semester` numbers, labelled `Summer sem//2` | Ordering by `semester` cannot distinguish them | `declared_seq = semester*10 + {Odd:0,Even:1,Summer:2}` |
| `ResultAnnouncement.created_at` is *creation* time, not declaration time | Misleading name | `declared_at`, captured at the event |
| `semester_type` nullable ⇒ the unique constraint does not dedupe NULLs on Postgres | Legacy rows never match a typed lookup | explicit handling + a data-quality report |
| `Student.batch_id` is an FK to `Batch`; `Student.batch` is an unrelated integer year | Actively confusing | `batch_erp_id` + `batch_label` |
| Publication gated by `announced` **plus** an optional per-student allow-list, with `_is_result_published_for` not itself checking `announced` | Two-part condition that every ERP call site re-ANDs by hand | one boolean: is there a non-retracted `ResultDeclaration` covering this student? |

**Rules for this ACL, enforced in CI:**

- ERP shadow models (`managed = False`) may be imported **only** inside `modules/academics/erp/`. An
  `import-linter` contract forbids them anywhere else.
- The connection uses the `platform_erp_ro` role. A write attempt fails at the database.
- No other module may name an ERP concept. Placement asks
  `academics.contracts.get_standings(user_ids)` and receives platform vocabulary.

### Academics → Placement · **Published Language** (via `contracts.py`)

```python
# modules/academics/contracts.py
def get_standings(user_ids: Sequence[int]) -> dict[int, StandingDTO]: ...
def get_standing_history(user_id: int) -> list[SnapshotDTO]: ...
```

Plus the event `academics.standing.changed`, which Placement consumes to invalidate cached
eligibility. Placement **never** reads `academics_*` tables and never joins to them.

`StandingDTO` carries provenance as first-class data — `cpi`, `semester`, `semester_type`,
`declared_at`, `standing_version` — because a CPI without its provenance is not a usable number.

### Directory → all modules · **Published Language**

```python
# modules/directory/contracts.py
def get_users(user_ids: Sequence[int]) -> dict[int, UserRefDTO]: ...
def search_users(q: str, kind: str | None, limit: int) -> list[UserRefDTO]: ...
```

`UserRef` is a projection of IAM, kept current by `iam.user.*` events plus a nightly full reconcile.
It exists so the platform can join on users without a cross-database foreign key.

### Leave → HR · **Customer/Supplier**

Leave needs employment facts (is this person employed, on what appointment, from when) to compute
entitlements. HR supplies `get_employments(user_ids)`. Leave may **request** new contract functions;
HR owns whether and how to expose them. Neither reads the other's tables.

### Placement ↔ HR, Placement ↔ Leave · **no relationship**

Deliberately. If a need appears, it goes through `contracts.py` — never a direct import, never a join.

### All modules → `core/` and `fusion_contracts` · **Shared Kernel**

The kernel is small on purpose: request context, the error envelope, pagination, outbox/inbox
plumbing, file validators, the rule engine, PII field classes, and the pydantic event schemas.

Admission test (from [shared-kernel-reference.md](../03-platform/shared-kernel-reference.md)): a thing
belongs in `core/` only if **three or more modules need it**, it has **no domain semantics**, and
changing it would be reviewed by whoever owns the affected modules. "Two modules need it" means
duplicate it and wait.

### Shell → IAM, Platform, Sysops · **Published Language, via generated client**

The shell never hand-writes a request path. `packages/api-client` is generated by `orval` from the
committed OpenAPI schemas, and CI runs `git diff --exit-code openapi/` so the schema cannot drift from
the code. A backend field rename therefore surfaces as a **TypeScript compile error**, not as a
runtime `undefined` in production.

---

## Change-impact rules

| If you change… | You must… |
|---|---|
| An IAM token claim | Bump the token version; deploy validators (platform, legacy) **before** the issuer. Two signing keys coexist, so this needs no downtime. |
| A `contracts.py` signature | Update every caller in the same PR. `import-linter` and `mypy` will find them. |
| An event payload | Update the `fusion_contracts` pydantic model; contract tests fail on **both** producer and consumer until both are updated. Additive fields are safe; removals are a new topic version. |
| An ERP table the ACL reads | Update `modules/academics/erp/` only. A CI check compares shadow models against `information_schema` and fails on drift. |
| A `registry_module` code | It is the join key between the backend registry and the frontend manifest. A CI check asserts the two sets match exactly. |
| A permission code | Regenerate [permission-catalog.md](../02-iam/permission-catalog.md); the committed diff must be empty. Renaming a permission is a data migration on `rbac_role_permission`, not just a code change. |
| Anything in `core/` | Get review from an owner of each affected module. Kernel changes are the highest-blast-radius edits in the repo. |

## Reading the map when adding a module

1. Which context does this belong to? If the answer is "a bit of two", it is two modules.
2. What does it need from other contexts? Each answer is a `contracts.py` function on **their** side,
   plural by signature.
3. What does it publish? Each answer is an event in [event-catalog.md](event-catalog.md) with a
   pydantic schema.
4. Does it need anything from the ERP? If yes, it goes through `modules/academics` — never directly.
5. Are you tempted to add a foreign key to another module's table? That is the signal that the
   boundary is in the wrong place. Move the boundary; do not add the key.
