---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Data Ownership & Synchronization

**The governing rule: every fact has exactly one writer.** Everything else is a projection, a
snapshot or a cache — and is labelled as such, so nobody mistakes a copy for the truth.

---

## 1. Ownership table

| Fact | Authoritative store | Written by | Copies exist in | Copy freshness |
|---|---|---|---|---|
| Username, email, display name, account status | `iam.identity_user` | IAM only | `auth_user` (ERP), `directory_userref` (platform) | event-driven, < 30 s |
| Password hash, MFA secrets | `iam.identity_credential`, `iam.identity_mfa_factor` | IAM only | **none** — never copied anywhere | — |
| Sessions, refresh tokens | `iam.identity_session`, `iam.identity_refresh_token` | IAM only | Redis denylist of revoked `sid` | immediate |
| Roles, permissions, role→permission | `iam.rbac_*` | IAM only | `globals_designation` (ERP, names only) | event-driven, < 30 s |
| Who holds which role | `iam.rbac_user_role` | IAM only | `globals_holdsdesignation` (ERP, **lossy** — see §3) | event-driven, < 30 s |
| Module registry, role→module grants | `iam.registry_*` | IAM only | `globals_moduleaccess` (ERP), access-token `mod` claim | ≤ 10 min (token TTL) |
| `erp_user_id` ↔ IAM user id mapping | `iam.identity_user.erp_user_id` | IAM only | `directory_userref.user_id` | event-driven |
| **`auth_user` row existence and PK** | **ERP** `auth_user` | IAM projector (inserts/updates), legacy admin tooling | — | — |
| Everything academic — students, courses, grades, curricula, results | **ERP** | legacy monolith only | `academics_resultsnapshot` (immutable snapshot) | at declaration only |
| Declared academic standing | `academics_studentacademicstanding` (platform) | platform ingest only | — | derived from snapshots |
| Non-academic domain data — placement, HR, leave | `fusion_nonacad` | platform only | — | — |
| Backups, archives, batch onboarding | `fusion_system_db` schema `public` | sysadmin console only | — | — |

### The one deliberate exception

`auth_user` is owned by the **ERP**, not by IAM, even though IAM owns identity. This is the central
trade-off of the whole design: ~424 legacy models have foreign keys into `auth_user`, and relocating
it would mean editing every one of them against live production data.

So IAM owns *identity* (who you are, what you may do) while the ERP owns the *row* that 424 foreign
keys point at. IAM writes `auth_user` on user creation and status change; it never deletes. There is no
cross-database foreign key in either direction — IAM holds `erp_user_id` as a plain integer with a
uniqueness constraint. → [ADR-0002](adr/0002-separate-iam-service-and-database.md)

**Consequence to internalize:** a user "existing" is a two-step fact. IAM creates
`identity_user`, then projects an `auth_user` row. Until the projection lands, the user can
authenticate at `/app/` but the legacy monolith does not know them. User creation therefore
projects **synchronously** — it is the only projection that does — and fails the whole operation if
the ERP write fails. Everything else is eventual.

---

## 2. Projection mechanics (IAM → ERP)

```
IAM service function
 ┌─ transaction.atomic() (iam DB) ─────────────────────────┐
 │  rbac_user_role.objects.create(...)                     │
 │  audit_event.objects.create(...)                        │
 │  outbox_event.objects.create(topic="iam.role.assigned", │
 │                              dedupe_key=...)            │
 └─────────────────────────────────────────────────────────┘
        │ committed
        ▼
 publish_outbox (beat, 5 s) → project_role_assignment.delay(event_id)
        │
        ▼  connection: iam_erp_projector (narrow write grants)
 ┌─ transaction.atomic(using="erp") ───────────────────────┐
 │  upsert globals_designation                             │
 │  upsert globals_holdsdesignation   ← subject to H1      │
 │  upsert globals_moduleaccess       ← subject to H2      │
 └─────────────────────────────────────────────────────────┘
        │
        ▼
 mark outbox_event.consumed_at
```

**Properties:**

- **Idempotent.** Every projection is an upsert keyed by natural key. Replaying an event is a no-op,
  so `acks_late` redelivery is safe.
- **Ordered per user.** Tasks are routed by `user_id` so two role changes for the same person cannot
  interleave. Order across different users does not matter.
- **Pausable.** `IAM_IS_ROLE_WRITER=off` stops the projector without losing anything — events accrue
  in `outbox_event` and drain when it is re-enabled. This is the Phase 4 rollback.
- **Never destructive beyond its grants.** The projector's Postgres role can touch exactly three
  tables. A bug cannot delete a student.

### Reconciler

A nightly job (`iam.reconcile_erp_projection`) recomputes the expected ERP state for all users and
diffs it against actual.

| Mode | Behaviour | Active in |
|---|---|---|
| `report` | Log and alert on drift; change nothing | Phases 2–3 |
| `enforce` | Correct drift, writing an `audit_event` per correction | Phase 4 onward |

Expected drift (multi-holder roles suppressed by H1) is **allowlisted explicitly**, so the report is
empty in the steady state and a non-empty report is always a real problem. Alert: `reconcile drift > 0`.

---

## 3. Where the projection is lossy — and what we do about it

This is the honest part. The legacy schema cannot represent the new model, and pretending otherwise
would produce silent authorization bugs.

| New concept | Legacy equivalent | Loss | Handling |
|---|---|---|---|
| Scoped role assignment `(role, department=CSE)` | none | **total** | Only `scope_type IS NULL` assignments project. Scoped ones exist in IAM only, and the module is granted to the unscoped role so the legacy sidebar still works. |
| Multiple holders of one role | `unique_together ('working','designation')` — **one holder institute-wide** | **total beyond the first** | Project only the `is_primary` holder. Others are recorded in an explicit allowlist as intentional drift. **This needs a decision with the academic office before Phase 4** — see H1 below. |
| `valid_from` / `valid_to` on an assignment | none | total | Project only currently-valid assignments; a beat task re-projects at expiry boundaries. |
| `assignment_kind` = permanent / officiating / delegated | `user` (permanent) vs `working` (acting) | partial | permanent → both columns; officiating → `working` = actor, `user` = permanent holder; delegated → does **not** project. |
| Role inheritance | none | total | Flatten to effective module grants before projecting. Legacy sees the result, not the structure. |
| Permissions | none — legacy has no permission concept | total | Not projected. Legacy authorization stays designation-name-based, which is exactly what it does today. |

### H1 — the blocker

```sql
-- applications/globals/models.py:166
unique_together = [['user', 'designation'], ['working', 'designation']]
```

Only one person, institute-wide, can be the working holder of a designation. Two placement
coordinators cannot both be projected.

Three options, requiring an institutional decision, not an engineering one:

| Option | Cost | Consequence |
|---|---|---|
| **A** — drop the `('working','designation')` constraint in legacy | one migration on a live table; audit legacy code that assumes uniqueness | full fidelity; the cleanest end state |
| **B** — project only `is_primary`, allowlist the rest as drift *(default)* | none | the legacy sidebar is correct for the primary holder only; secondary holders use `/app/` exclusively |
| **C** — do not project multi-holder roles at all | none | those roles are `/app/`-only, and the legacy sidebar never shows them |

**Default is B.** Recorded as an open decision in
[risk-register.md](../08-delivery/risk-register.md) (R-H1) and it gates Phase 4.

### H2 — column drift

Production has columns added by raw `ALTER TABLE` from
`Fusion_System_Administrator/Backend/backend/api/views/schema.py:12-52` that no monolith migration
knows about: `globals_designation.{basic, category, dept_if_not_basic_id}` and
`globals_moduleaccess.inventory_management`. The legacy model declares 20 boolean fields; the console's
shadow model declares 21 (has `inventory_management`, lacks `database`). All three disagree.

Handling:

1. The projector writes through a shadow model **generated at startup from `information_schema`**, so
   it always matches the live table rather than a stale Python class.
2. A CI check compares every `registry_module.legacy_column_name` against the live column list and
   fails on a mismatch.
3. Phase 2 reconciles the drift into real monolith migrations, so `makemigrations` stops wanting to
   drop production columns.

### H3 — width mismatch

`ExtraInfo.last_selected_role` is `max_length=20`; `Designation.name` is 50 and
`ModuleAccess.designation` is 155. Long role names cannot round-trip through `PATCH /api/update-role/`.
Phase 0 widens the column; until then IAM enforces a 20-character cap on
`rbac_role.legacy_designation_name` (validated at role creation, not silently truncated).

---

## 4. Snapshots vs projections vs caches

Three different things, deliberately different words. Confusing them is how stale data gets trusted.

| | Projection | Snapshot | Cache |
|---|---|---|---|
| Example | `directory_userref`, `globals_holdsdesignation` | `academics_resultsnapshot` | `iam:perms:<role>:<pv>` |
| Tracks the source? | yes, continuously | **no — frozen at a point in time** | yes, until superseded |
| Mutable? | yes | **no** (`UPDATE`/`DELETE` revoked in Postgres) | replaced, never edited |
| Rebuildable? | yes, from the source | only by re-pulling the same declaration | yes, trivially |
| If it disagrees with source | it is stale — a bug | **it does not disagree; it is a historical record** | miss and recompute |

A snapshot is not stale data. `ResultSnapshot` records what the ERP computed at the moment of
declaration, which is precisely the value the eligibility decision was made against. If the ERP's grade
data changes afterwards, the snapshot is still the right answer to "what did we decide on, and why".

That is also why `UPDATE` and `DELETE` are revoked on that table for `platform_app` — immutability is
a database guarantee, not a code convention.

---

## 5. Academic data flow

```
ERP (authoritative, we never write)
  online_cms_student_grades  ─┐
  programme_curriculum_course ├─► calculate_cpi_for_student()   ← the ONLY CPI implementation
  academic_procedures         │        (examination/api/views.py:134)
    course_replacement       ─┘
  examination_resultannouncement ─► _is_result_published_for()  ← publication gate (views.py:3324)
                     │
                     │ declaration event + internal snapshot endpoint
                     ▼
Platform (modules/academics)
  ResultDeclaration          one row per (batch, semester, semester_type)
  ResultSnapshot             IMMUTABLE, one row per (declaration, student)
  StudentAcademicStanding    one row per student — latest declared, via a guarded upsert
                     │
                     │ academics.standing.changed
                     ▼
  modules/placement          EligibilityEvaluation invalidated by inputs_version
```

The advance rule is a single atomic statement whose `WHERE` clause is the entire safety guarantee:

```sql
ON CONFLICT (user_id) DO UPDATE SET ... , standing_version = standing_version + 1
WHERE  EXCLUDED.declared_seq >  studentacademicstanding.declared_seq
   OR (EXCLUDED.declared_seq = studentacademicstanding.declared_seq
       AND EXCLUDED.declared_at > studentacademicstanding.declared_at);
```

An older or provisional declaration can never overwrite a newer declared one; a re-declaration of the
same semester (a correction) does win; out-of-order event delivery is harmless. There is no
read-modify-write, so there is no race. Detail:
[academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md).

---

## 6. Consistency guarantees, stated plainly

| Between | Guarantee | Bound | If violated |
|---|---|---|---|
| IAM ↔ its own tables | strongly consistent | — | — |
| Platform ↔ its own tables | strongly consistent, one Postgres transaction per service call | — | — |
| IAM → access-token claims | **eventually consistent** | ≤ 10 min (access-token TTL) | a revoked role can act for up to 10 min. Mitigation: revocation adds `sid` to a Redis denylist, so a *revoked session* dies immediately; a *changed role* waits for token refresh. |
| IAM → ERP projection | eventually consistent | < 30 s typical, alert at 300 s | legacy sidebar briefly stale. Never a security hole: legacy authorization reads the projected table, which is fail-closed until the grant lands. |
| IAM → `directory_userref` | eventually consistent | < 30 s | a display name is briefly stale |
| ERP → academic snapshot | **point-in-time by design** | at declaration only | not a violation — see §4 |
| Platform stats snapshots | eventually consistent | ≤ 15 min, or 60 s after an offer event | dashboard slightly behind. Documented on the page itself. |

**The 10-minute window is the one to internalize.** It is the cost of local token validation, and it
buys the property that IAM going down does not log everyone out. If a role must be revoked
*instantly*, revoke the **session** (immediate, Redis denylist) rather than the role.

---

## 7. Backup and restore ordering

Databases are backed up independently but **restored in dependency order**, because IAM holds
`erp_user_id` references into the ERP:

```
1. fusion_newui_prod   (ERP — the reference target)
2. fusion_system_db    (IAM + console)
3. fusion_nonacad      (platform)
4. run iam.reconcile_erp_projection --mode=enforce
5. run academics.verify_snapshots --full
```

Restoring `fusion_system_db` to an **earlier** point than the ERP leaves IAM referencing
`erp_user_id`s that exist, which is safe. Restoring it **later** than the ERP can leave IAM
referencing rows that do not exist yet — which is why the ERP is restored first and the reconciler runs
last. A dangling `erp_user_id` is detected by the reconciler and reported, never silently ignored.

Full procedure, with the elapsed time measured on real hardware:
[restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md).

---

## 8. Rules for reviewers

Reject a change if it:

- reads `iam.*` tables from outside IAM, or `globals_*` from outside `modules/academics` and the
  projector;
- writes to any ERP table other than the projector's three;
- adds a foreign key across a module boundary (CI catches this, but catch it in review first);
- copies a fact into a second table without labelling it a projection, a snapshot or a cache, and
  saying who keeps it current;
- introduces a second writer for any fact in the §1 table;
- trusts `Student.cpi` or `academic_information.Spi` — both are dead;
- reimplements CPI, SPI or credit arithmetic anywhere. → [NG5](../00-overview/vision-and-scope.md#non-goals)
