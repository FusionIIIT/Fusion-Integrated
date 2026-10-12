# Employee Leave Management (ELM) — Phase 2 Blueprint

Status: **DRAFT — awaiting assignment-owner approval (Step 3). No application code written.**
Revision 2 — incorporates review findings (classification of every element, entitlement reclassification, permission audit, calendar-constraint reconciliation, requirement-mapping corrections, and an approval gate on the implementation sequence).

Module code: `leave` · ID prefix: `EL-` · Environment: `module-only` · Doc folder: `docs/09-leave/`

> Assignment rule: no application code before this blueprint is approved (`docs/08-delivery/new-module-prompt.md:29-30,252-255,385`;
> `docs/08-delivery/student-assignment-guide.md:99-101`). This document is a design proposal, not implemented behaviour.
> Where the specification does not settle a business rule, it is recorded in Step 3.8 rather than chosen.

## Classification legend (applies to every model, endpoint, permission, task and transition below)

| Tag | Meaning |
|---|---|
| **EXPLICIT** | Stated by the requirements baseline (PS / CFR / AFR / BR / UC / WF v1.6 state-transition tables). |
| **CONVENTION** | Derived from an existing, evidenced platform convention (repo docs or shipped code), not invented here. |
| **PROVISIONAL** | A design choice made to fill a gap; requires owner approval before it can be treated as settled. |
| **BLOCKED** | Cannot be finalised until the cited Step 3.8 unresolved item is ruled on. |

Nothing in this document is claimed to be built, executed, or tested. Every code path, model, endpoint and test is **proposed**.

## Approvals, evidence and authority

| Item | Authority used | Note |
|---|---|---|
| Requirements baseline | PS v1.4, Functional Requirement Specification v1.5 (CFR/AFR), UC v1.4, BR v1.4, RTM v1.5, WF **v1.6 state-transition tables** | Per assignment instruction. WF v1.6 header states its STT "remains authoritative" (`06_ELM_Workflow_Specifications_v1.6_FINAL.docx` ¶4-5). |
| Module code | `leave` | `docs/00-overview/glossary.md:49-51`, `docs/03-platform/platform-structure.md:150,184`, `docs/README.md:113`, `docs/02-iam/permission-catalog.md:145`. |
| Deliberate naming inconsistency | role-assignment-guide example uses `leave_elm` and verbs `apply`/`approve` | `docs/08-delivery/role-assignment-guide.md:99-112`. Treated as **illustrative, not authoritative** (see §0). |
| Blueprint filename / sections | Assignment template `docs/[NN]-[module_code]/[module_code]-blueprint.md`, sections Steps 3.1–3.8 | `new-module-prompt.md:254`. Preserved as `docs/09-leave/leave-blueprint.md`. The alternate `elm-blueprint.md` is **not** the template and is recorded as an inconsistency. |
| Timestamps | `TIME_ZONE="Asia/Kolkata"`, `USE_TZ=True` | `config/settings/base.py:240-245`. Calendar vs fiscal year boundary is **not** settled (Step 3.8 #6). |

### Authoritative requirement registers (ids only; corrected against the bundle)

- **CFR (32):** CFR-EL-001 … CFR-EL-032 as listed in `02_...Functional_Requirement...v1.5_FINAL.xlsx`. Two that matter for this revision: **CFR-EL-024** = *Maintain policy parameters and hierarchy configuration*; **CFR-EL-026** = *Maintain authorized leave records*.
- **BR (38 ids; 36 live):** BR-EL-001 … BR-EL-038. **BR-EL-021** = "RETIRED — Modify Pending Request" (replacement BR-EL-034). **BR-EL-026** = "RETIRED IDENTIFIER" (no replacement). All other BRs are Active.
- **UC (21 ids; 20 live):** EL-UC-001 … EL-UC-021. **EL-UC-006** = RETIRED ("Modify Pending Request").
- **WF (v1.6):** 17 Basis Workflows (`BW-EL-01…17`) + 4 Composite (`CW-EL-01…04`) + `XTP-EL-01`.

> Caution: `CFR-EL-026` (live) and `BR-EL-026` (retired) are different identifiers. All references below are prefixed to avoid confusion.

---

## §0 Module identity and the `leave_elm` inconsistency

- Adopt `module_code = leave` **[CONVENTION]**. This is what the repository's descriptive docs use in every non-illustrative place
  (`glossary.md:50`, `platform-structure.md:150,184`, `event-catalog.md:160` → `leave.*`, `permission-catalog.md:145`).
- `leave_elm` appears **once**, in a code fence labelled "might look like"
  (`role-assignment-guide.md:96-112`). It is not a requirement; it is a template illustration. **Recorded, not adopted.**
- That same example uses `application.apply` / `application.approve`. Neither `apply` nor `schedule`/`self` is in the documented closed verb list (`rbac-model.md:100-101`), yet the live `placement_cell` registry uses the same kinds of non-listed verbs (`modules/placement/registry.py:59-86`). The closed-vocabulary *convention* is therefore **drifted from the implemented manifest** — audited in Step 3.4.
- `ENVIRONMENT = module-only` (`student-assignment-guide.md:76`) → the `Fusion-client` sidebar entry must be supplied as a paste-ready instruction (Step 3.5), and integration reads may answer sparsely (`new-module-prompt.md:338-341,370-373`).

### Exact files to add or mechanically change (Step 3.2 / integration surface) — all **CONVENTION**

| Action | File | Evidence / why |
|---|---|---|
| Add module dir | `modules/leave/` (`__init__.py`, `apps.py`, `contracts.py`, `registry.py`, `schedule.py`, `tasks.py`, `domain/`, `models/`, `selectors/`, `services/`, `api/`, `management/commands/`, `migrations/`, `tests/`) | Layout mandated at `new-module-prompt.md:394-406` |
| Add to settings | `config/settings/base.py:91-93` `DOMAIN_MODULES` += `"modules.leave"` | `PLATFORM_MODULES`/`DOMAIN_MODULES` split, `base.py:85-96` |
| Mount URLs | `config/urls.py:18` add `path("api/v1/leave/", include("modules.leave.api.urls"))` | pattern of `config/urls.py:16-18` |
| Extend import-linter | `.importlinter:14-17` add `modules.leave` to `modules-only-touch-contracts` `source_modules`; add a `modules.leave` layers contract | `new-module-prompt.md:408-410`; actual file currently omits `hr`/`leave`/`academics` (drift from `platform-structure.md:147-151`) |
| Register schedule | `config/celery.py` merge `modules.leave.schedule.BEAT_SCHEDULE` / `TASK_ROUTES` | `new-module-prompt.md:461-464` |
| Client registry | `client/src/app/registry.ts:14-19` add `leave` entry with static `import("../modules/leave/routes")` | `registry.ts:1-20` |
| Frontend module | `client/src/modules/leave/` (`api/types.ts`, `api/hooks.ts`, `components/`, `pages/`, `routes.tsx`) | `new-module-prompt.md:568-577` |
| Generated artefacts (regenerate, do not hand-edit) | `registry/permissions.json` (`make permissions`), `openapi/fusion-integrated.v1.yaml` (`make schema`) | `new-module-prompt.md:329-333,620-629` |
| CI/nav gates (must pass) | `ops/checks/nav_matches_routes.py`, `ops/checks/no_cross_module_fk.py` (`ALLOWED_TARGETS`), `ops/checks/contracts_are_plural.py` (`EXEMPT`) | `new-module-prompt.md:448-450` |
| `Fusion-client` sidebar (module-only, external) | `INTEGRATED_MODULES` entry supplied in Step 3.5(e) | `new-module-prompt.md:338-341,611-614` |

No existing file is changed until Step 1 is authorised (see "Implementation sequence" and "Approval gate"). No auth table, no `Role`/`Permission`/`UserRole`/`ModuleAccess` model is created — RBAC stays in the IAM (`new-module-prompt.md:285-298`).

---

## Step 3.1 (a) — Traceability table

Layer codes: **D** domain, **M** models/DB constraint, **S** services, **X** selectors, **A** api (transport only), **R** registry/permissions, **C** schedule/tasks, **N** notifications. Class tags per the legend.

### Business rules (36 live)

| Id | What it requires | Layer | Enforcement point (planned) | Class | Notes |
|---|---|---|---|---|---|
| BR-EL-001 | Only CL/RH/SCL/EL/COL/VL, applicability per policy | D+S | `domain/rules.py`, `services/apply.py` | EXPLICIT | BR-EL-030 dependency |
| BR-EL-002 | CL 8/yr; unused CL lapses | D+C | `domain/entitlement.py`, year-end task, ledger | EXPLICIT (amount/lapse) · BLOCKED (timing, #7) | Amount 8 explicit; allocation timing/proration unresolved |
| BR-EL-003 | RH 2/yr; RH date must be in effective published calendar; lapses | D+M+C | `domain/entitlement.py`, `models/calendar.py`, year-end | EXPLICIT (amount) · BLOCKED (calendar range, #5/#11) | BR-EL-031 |
| BR-EL-004 | SCL ≤15/yr; admissibility is authority judgment; lapses | D+S+C | `domain`, decision service, year-end | EXPLICIT (cap) · BLOCKED (consumption granularity, #7) | No encoded admissibility rule |
| BR-EL-005 | Non-faculty EL 30/yr credit; carry forward | D+C+M | `domain`, year-end, ledger partial-unique `ANNUAL_CREDIT` | EXPLICIT (amount/carry) · BLOCKED (timing/proration, #7) | `ANNUAL_CREDIT` proves idempotency only |
| BR-EL-006 | Faculty VL 60; only within Academic Calendar vacation period | D+M | `domain`, calendar-ref model, dep contract | EXPLICIT (amount) · BLOCKED (external contract, #2) | |
| BR-EL-007 | Year-end VL→EL at 2:1 incl. fractions; no VL carry | D+C | `domain/conversion.py`, year-end, ledger | EXPLICIT (ratio) · BLOCKED (rounding, #7) | "fractions preserved" explicit; rounding rule not |
| BR-EL-008 | Converted EL credited, carries, usable | D+M | ledger + `domain` | EXPLICIT | |
| BR-EL-009 | COL 20/yr; medical/balance-controlled; evidence where applicable; carries | D+M+C | `domain`, evidence field, year-end, ledger | EXPLICIT (amount/carry) · PROVISIONAL (evidence rule) | |
| BR-EL-010 | Half-day CL first/second; 0.5 day deducted | D | `domain/counting.py` | EXPLICIT | |
| BR-EL-011 | Continuous-day counting for EL/COL/VL; not CL/SCL/RH | D | `domain/counting.py` | EXPLICIT | |
| BR-EL-012 | No impermissible overlap; different CL halves OK | D+X | `domain/overlap.py`, `selectors/requests.py` | EXPLICIT | |
| BR-EL-013 | Station Leave coupled in same application | M | `models/request.py` fields | EXPLICIT (coupling) · PROVISIONAL (field shape) | No separate lifecycle |
| BR-EL-014 | Substitute: one, other employee, not applicant, no overlap | D+X | `domain/substitute.py`, `selectors` | EXPLICIT | |
| BR-EL-015 | Consent gate blocks routing; decline → replace or withdraw | S | `services/substitute.py`, state machine | EXPLICIT | |
| BR-EL-016 | CL/RH Unit Head is final (except Director) | S+R | `services/routing.py`, permission gate | EXPLICIT (rule) · BLOCKED (approver identity, #4) | |
| BR-EL-017 | Higher-sanction: Unit Head records Recommended/Not Recommended; neither is final reject | S | `services/review.py` | EXPLICIT | |
| BR-EL-018 | Higher-sanction routes through configured hierarchy to final authority | S | `services/routing.py` | EXPLICIT (rule) · BLOCKED (source of hierarchy, #4) | |
| BR-EL-019 | Path resolved from applicant/unit/role/category/config; optional Establishment + named roles where configured | S+M | `services/routing.py`, `models/policy.py` | EXPLICIT (rule) · BLOCKED (config source, #4) | |
| BR-EL-020 | Director self-sanction | S | state machine `Awaiting Director Self-Sanction` | EXPLICIT | |
| BR-EL-022 | Immediate withdrawal before final approval; terminal effects | S+M | `services/withdraw.py`, state machine | EXPLICIT | |
| BR-EL-023 | Cancellation pre-start; same hierarchy; approve → Cancelled + restore/adjust; reject → unchanged | S+M | `services/cancellation.py`, ledger | EXPLICIT (rule) · BLOCKED (hierarchy, #4) | |
| BR-EL-024 | Fresh application after cancellation | S | no in-place edit; new request | EXPLICIT | |
| BR-EL-025 | Extension only ongoing EL/COL/VL; approval posts incremental only | S+M | `services/extension.py`, ledger | EXPLICIT | |
| BR-EL-027 | Resumption review for EL/COL/VL by Sanctioning Authority | S+R | `services/resumption.py`, permission | EXPLICIT (rule) · BLOCKED (authority identity, #4) | |
| BR-EL-028 | On/early/late resumption outcome + sync leave/attendance | D+S | `domain/resumption.py`, service; attendance sync | EXPLICIT (outcome) · BLOCKED (attendance contract, #3) | |
| BR-EL-029 | Offline-sanctioned leave synchronization, evidence, no 2nd approval | S+M | `services/offline.py`, no workflow | EXPLICIT | |
| BR-EL-030 | Use current configured policy/hierarchy | M+S | `models/policy.py`, services | BLOCKED (#1) | Model shape not chosen |
| BR-EL-031 | Date/RH validation uses effective published calendar | M+X | `models/calendar.py`, selectors | EXPLICIT (rule) · BLOCKED (range semantics, #5/#11) | Calendar publish lifecycle **is** specified |
| BR-EL-032 | SLA reminder only while pending; log | C+S+N | `tasks.py`, notification | EXPLICIT | |
| BR-EL-033 | SLA escalation while pending; notify/escalate; log; routing change via XTP | C+S+N | `tasks.py`, XTP-EL-01 | EXPLICIT | |
| BR-EL-034 | No in-place modification of a pending request; withdraw+new | A+S | no update route; service guard | EXPLICIT | |
| BR-EL-035 | Notify assignee on actionable task assignment | S+N | task creation → notification | EXPLICIT | |
| BR-EL-036 | Role-based authorization for all ELM actions | R+A | `registry.py` + `HasPermission`/module grant | EXPLICIT | |
| BR-EL-037 | Admin maintenance ≠ sanctioning | S+R | separate service + permission | EXPLICIT (rule) · BLOCKED (role identity, #4) | |
| BR-EL-038 | Configurable SLA thresholds | M+S | `models/sla.py`, config service | EXPLICIT | |

**Retired identifiers (never cited as live, no enforcement point):** `BR-EL-021` (replaced by BR-EL-034), `BR-EL-026` (no replacement), `EL-UC-006` (retired), legacy workflows `WF-EL-02/06/07/08`, and superseded `SRS-EL-055/056/057/058/085/086(partial)/091` (`new-module-prompt.md:692`). They are preserved for traceability only.

### Use cases (20 live)

| Id | What it requires | Layer | Enforcement point (planned) | Class | Supporting CFR / BR |
|---|---|---|---|---|---|
| EL-UC-001 | Apply for Leave | A+S+D | `POST /requests/` → `services/apply.py` | EXPLICIT | CFR-EL-002/003/011/012; BR-EL-001–015 |
| EL-UC-002 | Respond to Substitute Request | A+S | `POST /substitute/{id}/respond` | EXPLICIT | CFR-EL-012; BR-EL-015 |
| EL-UC-003 | Review Leave-Related Request at Unit Head | A+S | `POST /reviews/{id}` | EXPLICIT | CFR-EL-013/014; BR-EL-016–017 |
| EL-UC-004 | Verify and Route Higher-Sanction Request | A+S | `POST /routing/{id}/forward` | EXPLICIT (UC) · BLOCKED (role, #4) | CFR-EL-014; BR-EL-018–019 |
| EL-UC-005 | Make Final Sanctioning Decision | A+S | `POST /decisions/{id}` | EXPLICIT (UC) · BLOCKED (authority, #4) | CFR-EL-014/016; BR-EL-018–020 |
| EL-UC-007 | Withdraw Pending Request | A+S | `POST /requests/{id}/withdraw` | EXPLICIT | CFR-EL-018; BR-EL-022/034 |
| EL-UC-008 | Request Cancellation of Approved Leave | A+S | `POST /cancellations/` | EXPLICIT | CFR-EL-019; BR-EL-023–024 |
| EL-UC-009 | Request Extension of Ongoing Leave | A+S | `POST /extensions/` | EXPLICIT | CFR-EL-020; BR-EL-025 |
| EL-UC-010 | Submit Resumption of Duty | A+S | `POST /resumptions/` | EXPLICIT | CFR-EL-021; BR-EL-027 |
| EL-UC-011 | Review Resumption | A+S | `POST /resumptions/{id}/review` | EXPLICIT (UC) · BLOCKED (attendance, #3) | CFR-EL-021; BR-EL-027–028 |
| EL-UC-012 | View Leave Balances and History | A+X | `GET /balances/self`, `GET /requests/self` | EXPLICIT | CFR-EL-022; BR-EL-002–009 |
| EL-UC-013 | Obtain Printable/Exportable Leave Application | A+X | `GET /requests/{id}/export` | EXPLICIT | CFR-EL-023 |
| EL-UC-014 | Maintain Policy and Hierarchy Configuration | A+S+M | `PUT /policy`, `PUT /hierarchy` | BLOCKED (#1) | CFR-EL-024; BR-EL-030 |
| EL-UC-015 | Maintain and Publish Holiday/RH Calendar | A+S+M | `POST /calendar`, `POST /calendar/{id}/publish` | EXPLICIT (publish) · PROVISIONAL (range, #5/#11) | CFR-EL-025; BR-EL-031 |
| EL-UC-016 | Record Already-Sanctioned Offline Leave | A+S | `POST /offline-records/` | EXPLICIT | CFR-EL-027; BR-EL-029 |
| EL-UC-017 | Maintain Authorized Leave Records | A+S | `PATCH /records/{id}` | EXPLICIT (UC) · PROVISIONAL (method/shape) | **CFR-EL-026; BR-EL-037** (+BR-EL-036). Must not sanction. |
| EL-UC-018 | Configure Workflow SLA Thresholds | A+S+M | `PUT /sla` | EXPLICIT | CFR-EL-029; BR-EL-038 |
| EL-UC-019 | Nominate Replacement Substitute After Decline | A+S | `POST /substitute/{id}/replace` | EXPLICIT | CFR-EL-011; BR-EL-015 |
| EL-UC-020 | Execute Year-End Leave Processing | C+S+M | beat task `leave.year_end` | EXPLICIT (effect) · BLOCKED (boundary, #6) | CFR-EL-028; BR-EL-002–009 |
| EL-UC-021 | Process SLA Threshold Event | C+S+N | beat task `leave.sla_scan` | EXPLICIT | CFR-EL-031/032; BR-EL-032–033 |

> **Correction applied in Revision 2:** the EL-UC-017 endpoint previously cited `026–027, 037`, which read as the retired `BR-EL-026`. The live support is **`CFR-EL-026` + `BR-EL-037`** (administrative maintenance that is not sanctioning), with `BR-EL-036` (authorization). No retired identifier is used as live support anywhere in this table.

---

## Step 3.2 (b) — Domain model

Aggregates and invariants. DB-enforced constraints are marked **DB**; Python-only invariants **PY**. No FK crosses a module boundary (`new-module-prompt.md:419-421`); cross-entity `user_id` is a plain integer (as `core/db/mixins.py::UserScopedModel` already does) **[CONVENTION]**.

### Policy / configuration (`models/policy.py`) — **BLOCKED (#1)**
The specification says leave-policy parameters use the *current configured values with no draft/publish/effective-version lifecycle* (PS §5, PS §12, CFR-EL-024, BR-EL-030); the assignment's platform convention says admin configuration is *effective-dated and never edited* (`new-module-prompt.md:244-248`). These are opposed for policy/hierarchy parameters. **This blueprint does not pick one.** Consequently the model is unresolved and the lifecycle fields are deliberately unspecified:

- `LeaveTypePolicy` — **[BLOCKED]** `code` (CL/RH/SCL/EL/COL/VL), `annual_entitlement` (Decimal), `carry_forward` (bool), `conversion_ratio` (nullable, VL), `applies_to_kind`, and *either* `is_active` (current-only shape) *or* `effective_from`/`effective_to`/`version` (versioned shape). Which set of lifecycle fields is used is the open question.
- `HierarchyStep` — **[BLOCKED (#1) + BLOCKED (#4)]** ordered approval steps (`leave_type`, `step_order`, `required_designation`, `optional_flag` for Establishment). Both the lifecycle and the source of the hierarchy are unresolved.
- `SlaThreshold` — **[EXPLICIT]** `task_class`, `reminder_hours`, `escalation_hours`, `escalation_action`, `is_active` (CFR-EL-029, BR-EL-038).

### Calendar (`models/calendar.py`)
- `HolidayCalendar` — **PROVISIONAL; range/publication semantics defines an unresolved design dependency (#5/#11).** The proposed field set (`label`, `is_published`, `published_at`) does **not** carry the range information that the proposed constraint needs ("at most one published calendar governing a date range"). To be internally consistent the model also needs a governing range and publication provenance, e.g. `effective_from`, `effective_to` (or `governing_year`), `published_by`. **What "governing a date range" means — inclusive endpoints, overlap behaviour, whether a successor may be published before the predecessor's end — is not stated by the specification and is therefore PROVISIONAL / BLOCKED for the constraint.** The publish lifecycle itself **is** specified for the calendar (PS §12 ¶47, CFR-EL-025, BR-EL-031).
- `HolidayCalendarDay` — **EXPLICIT** `calendar`, `date`, `kind` (closed_holiday | restricted_holiday). **DB** unique `(calendar, date, kind)`.

### Leave request aggregate (`models/request.py`)
- `LeaveRequest` — **[EXPLICIT fields; PROVISIONAL constraint]** `id`, `applicant_user_id`, `leave_type`, `start_date`, `end_date`, `half_day` (nullable: first|second), `requested_days` (Decimal), `purpose`, `station_leave_flag`, `station_leave_details`, `state`, `submitted_at`, timestamps. **DB** `CheckConstraint(window_valid)` **[PROVISIONAL]**. `state` constrained to the transition-table vocabulary (Step 3.3) **[CONVENTION]**. **PY** per BR-EL-034 there is *no* update path once `state` is pending **[EXPLICIT]**.
- `LeaveRequestDay` — **[PROVISIONAL]** materialised chargeable days (counting/overlap). **DB** unique `(request, date, half)`.
- `SubstituteAssignment` — **[EXPLICIT rule; PROVISIONAL shape]** `request`, `nominee_user_id`, responsibility window, `state` (awaiting|accepted|declined), `rejection_count`. **DB** at most one `accepted` per request (partial unique) **[PROVISIONAL]**. **PY** nominee ≠ applicant; nominee has no overlapping leave (BR-EL-014).
- `ApprovalTask` — **[CONVENTION]** `subject` (request/cancellation/extension), `step_order`, `assigned_designation`, `assigned_user_id`, `state`, `due_at`. **DB** one open task per `(subject, step_order)` (partial unique) **[PROVISIONAL]**. SLA computed from `created_at`.
- `LeaveDecision` — **[EXPLICIT]** append-only `request`, `actor_user_id`, `decision` (approve|reject|recommend|not_recommend), `decided_at`, `note`.
- `LeaveCancellation`, `LeaveExtension`, `ResumptionReview` — **[EXPLICIT rule; PROVISIONAL shape]** sibling records. **PY** none edits the original `LeaveRequest` in place (BR-EL-023, BR-EL-025, CFR-EL-017).

### Ledger (`models/ledger.py`) — **CONVENTION + EXPLICIT mechanism**
- `LeaveLedgerEntry` — append-only **[CONVENTION]** (`new-module-prompt.md:241-242`). `user_id`, `leave_type`, `entry_kind` (ANNUAL_CREDIT | CONSUMED | CARRY_FORWARD | LAPSE | CONVERSION_OUT | CONVERSION_IN | CANCELLATION_RESTORE | OFFLINE_SYNC | ADJUSTMENT | REVERSAL), `days` (Decimal, signed), `source_type`, `source_id`, `credit_year` (nullable), `reversal_of` (nullable self-ref), `created_at`, `created_by`.
  - **DB** `UniqueConstraint(user_id, leave_type, entry_kind='ANNUAL_CREDIT', credit_year)` **partial** — the idempotency mechanism evidenced at `testing-strategy.md:49-50` **[CONVENTION mechanism]**.
  - **DB/PY** rows are never updated; corrections are `entry_kind='REVERSAL'` referencing `reversal_of` **[CONVENTION]**.
- Balances are **derived** by summing ledger entries (no mutable balance column) **[CONVENTION]**.

> **`ANNUAL_CREDIT` establishes idempotency only.** It proves that an annual credit for a given `(user, leave_type, credit_year)` is applied once. It does **not** define *when* the credit is allocated, *whether* it is prorated, *how* fractions round, or *what* the entitlement amounts are. Those are separated in the entitlement classification below.

### Entitlement classification (finding 4)

| Category | Items |
|---|---|
| **Explicitly specified calculations** | CL = 8/yr (BR-EL-002); RH = 2/yr (BR-EL-003); SCL ≤ 15/yr (BR-EL-004); non-faculty EL = 30/yr (BR-EL-005); faculty VL = 60/yr (BR-EL-006); COL = 20/yr (BR-EL-009); VL→EL = 2:1 (BR-EL-007); half-day CL = 0.5 (BR-EL-010); continuous-day counting (BR-EL-011); carry-forward yes/no per category (BR-EL-002/003/004/005/009); lapse for CL/RH/SCL (BR-EL-002/003/004). |
| **Unresolved — allocation timing** | When within the leave year each category is credited; whether credit is available before the year starts; behaviour for a request that spans the year boundary. Not stated. |
| **Unresolved — proration** | Mid-year joiners/leavers; part-time or change of faculty/staff kind mid-year. Not stated. |
| **Unresolved — rounding** | Rounding of fractional day results beyond a half-day; the "fractional VL→EL conversion preserved" rule (AFR-EL-008.5) does not state the final rounding. Not stated. |
| **Unresolved — SCL consumption granularity** | "SCL ≤ 15" does not state whether consumption is per-day, per-block, or authority-adjudicated. Not stated. |
| **Not a policy** | `ANNUAL_CREDIT` partial unique — idempotency only (**CONVENTION**). |

These unresolved items are Step 3.8 #7 and are **BLOCKED** for `domain/entitlement.py` edge cases and year-end math for partial-year members.

### Auxiliary (`models/offline.py`)
- `OfflineLeaveRecord` — **[EXPLICIT rule; PROVISIONAL shape]** `subject_user_id`, `leave_type`, `period`, `sanction_reference`, `evidence`, `recorded_by`, timestamps; creates ledger entries but **no** approval task (BR-EL-029).

---

## Step 3.3 (c) — State machine (declarative transition table)

Authoritative source: **Workflow Specification v1.6** state-transition tables (STT). Every transition below is **[EXPLICIT]** from that source. Making illegal transitions **inexpressible** (constraining `state` to the enumerated set and routing every move through one service choke point) is **[CONVENTION / PROVISIONAL design]** (`new-module-prompt.md:272-276,432-435`).

### CW-EL-01 — New Leave Processing and Pending Withdrawal (`06_..._v1.6_FINAL.docx` §5) — EXPLICIT
States: `Draft/Not Submitted`, `Awaiting Substitute Response`, `Applicant Action Required`, `Awaiting Unit Head Review`, `Awaiting Establishment Routing`, `Awaiting Final Sanction Decision`, `Awaiting Director Self-Sanction`, `Approved`, `Rejected`, `Withdrawn`.

| From | Event/Guard | Actor | To | BR |
|---|---|---|---|---|
| Draft/Not Submitted | valid; substitute required | Employee | Awaiting Substitute Response | 001–015, 030–031 |
| Draft/Not Submitted | valid; no substitute; applicant is Director | Employee | Awaiting Director Self-Sanction | 001–013, 020, 030–031 |
| Draft/Not Submitted | valid; no substitute; applicant not Director | Employee | Awaiting Unit Head Review | 001–013, 030–031 |
| Awaiting Substitute Response | Accept; Director | Substitute | Awaiting Director Self-Sanction | 014–015, 020 |
| Awaiting Substitute Response | Accept; not Director | Substitute | Awaiting Unit Head Review | 014–015 |
| Awaiting Substitute Response | Decline | Substitute | Applicant Action Required | 014–015 |
| Applicant Action Required | eligible replacement | Employee | Awaiting Substitute Response | 014–015 |
| Awaiting Unit Head Review | CL/RH approve | Unit Head | Approved | 016 |
| Awaiting Unit Head Review | CL/RH reject | Unit Head | Rejected | 016 |
| Awaiting Unit Head Review | higher-sanction; Establishment configured | Unit Head | Awaiting Establishment Routing | 017–019, 030 |
| Awaiting Unit Head Review | higher-sanction; no Establishment | Unit Head | Awaiting Final Sanction Decision | 017–019, 030 |
| Awaiting Establishment Routing | routing context valid | Establishment | Awaiting Final Sanction Decision | 018–019, 030 |
| Awaiting Final Sanction Decision | approve | Sanctioning Authority | Approved | 018–019 (CFR-EL-014) |
| Awaiting Final Sanction Decision | reject | Sanctioning Authority | Rejected | 018–019 (CFR-EL-014) |
| Awaiting Director Self-Sanction | approve / reject | Director | Approved / Rejected | 020 |
| {Awaiting Substitute Response, Applicant Action Required, Awaiting Unit Head Review, Awaiting Establishment Routing, Awaiting Final Sanction Decision, Awaiting Director Self-Sanction} | withdrawal succeeds | Employee | Withdrawn | 022, 034 |

### CW-EL-02 — Approved Leave Cancellation — EXPLICIT
States: `Approved/Not Started`, `Cancellation Pending — Unit Head Review`, `Cancellation Pending — Establishment`, `Cancellation Pending — Final Decision`, `Cancelled`, `Approved/Unchanged`.

| From | Event/Guard | Actor | To | BR |
|---|---|---|---|---|
| Approved/Not Started | eligible | Employee | Cancellation Pending — Unit Head Review | 023 |
| Cancellation Pending — Unit Head Review | UH-final; approve | Unit Head | Cancelled; balance restored/adjusted | 016, 023–024 |
| Cancellation Pending — Unit Head Review | UH-final; reject | Unit Head | Approved/Unchanged | 016, 023 |
| Cancellation Pending — Unit Head Review | higher-sanction; Establishment | Unit Head | Cancellation Pending — Establishment | 017–019, 023, 030 |
| Cancellation Pending — Unit Head Review | higher-sanction; no Establishment | Unit Head | Cancellation Pending — Final Decision | 017–019, 023, 030 |
| Cancellation Pending — Establishment | routing valid | Establishment | Cancellation Pending — Final Decision | 018–019, 023, 030 |
| Cancellation Pending — Final Decision | approve / reject | Sanctioning Authority | Cancelled / Approved/Unchanged | 023 |

### CW-EL-03 — Ongoing Leave Extension — EXPLICIT
States: `Ongoing EL/COL/VL`, `Awaiting Extension Substitute Response`, `Extension Applicant Action Required`, `Awaiting Extension Unit Head Review`, `Extension Pending — Establishment`, `Extension Pending — Final Decision`, `Extended Leave in Effect — Incremental Period Posted`, `Original Ongoing Leave Unchanged`, `Extension Request Withdrawn — Original Leave Unchanged`.

| From | Event/Guard | Actor | To | BR |
|---|---|---|---|---|
| Ongoing EL/COL/VL | valid; substitute required | Employee | Awaiting Extension Substitute Response | 001, 005–015, 025, 030–031 |
| Ongoing EL/COL/VL | valid; no substitute | Employee | Awaiting Extension Unit Head Review | 001, 005–013, 025, 030–031 |
| Awaiting Extension Substitute Response | Accept / Decline | Substitute | Awaiting Extension Unit Head Review / Extension Applicant Action Required | 014–015, 025 |
| Extension Applicant Action Required | eligible replacement | Employee | Awaiting Extension Substitute Response | 014–015 |
| Awaiting Extension Unit Head Review | recommendation; Establishment / none | Unit Head | Extension Pending — Establishment / Extension Pending — Final Decision | 017–019, 025, 030 |
| Extension Pending — Establishment | routing valid | Establishment | Extension Pending — Final Decision | 018–019, 025, 030 |
| Extension Pending — Final Decision | approve / reject | Sanctioning Authority | Extended...Incremental Posted / Original Ongoing Leave Unchanged | 025 |
| {extension pending states} | withdrawal succeeds | Employee | Extension Request Withdrawn — Original Leave Unchanged | 022 |

### CW-EL-04 — Resumption Review — EXPLICIT
States: `Returned from EL/COL/VL`, `Resumption Review Pending`, `Resumption Reviewed — No Adjustment`, `Resumption Reviewed — Early Return Synchronized`, `Resumption Reviewed — Late Return Synchronized`.

| From | Event/Guard | Actor | To | BR |
|---|---|---|---|---|
| Returned from EL/COL/VL | details submitted | Employee | Resumption Review Pending | 027 |
| Resumption Review Pending | actual = approved end | Sanctioning Authority | No Adjustment | 027–028 |
| Resumption Review Pending | actual < approved end | Sanctioning Authority | Early Return Synchronized | 028 · **BLOCKED (#3)** |
| Resumption Review Pending | actual > approved end | Sanctioning Authority | Late Return Synchronized | 028 · **BLOCKED (#3)** |

### XTP-EL-01 — Cross-cutting SLA routing/responsibility escalation — EXPLICIT (transition), PROVISIONAL (config shape)
System transition only when configured escalation changes routing/responsibility; notification-only escalation is **not** a workflow transition (`06_..._v1.6_FINAL.docx` §5, XTP-EL-01).

### Workflow-registry conflict (assignment item 5) — retained
- WF **v1.6** defines **17** Basis Workflows (`BW-EL-01…17`) and 4 Composite (`CW-EL-01…04`), with the v1.6 header stating it "corrects a Basis-Workflow derivation defect in v1.5" and that the STT is authoritative.
- RTM **v1.5** `WF_Registry` defines **19** Basis Workflows with different names/constituents (e.g. RTM `BW-EL-01` = "New Leave — Substitute Consent Accepted (No Loop)" vs v1.6 `BW-EL-01` = "New CL/RH — No Substitute Gate").
- The RTM Summary authority line reads "…WF v1.5"; the assignment mandates v1.6 STT. **Build to v1.6.** Composite workflow *semantics* are identical in both (v1.6 ¶5), so no traceability gap exists at composite level; only the Basis-Workflow decomposition differs.
- **Traceability mapping that cannot be completed without reconciliation**: any artefact pinning a UC sequence to a *numbered* `BW-EL-nn` (RTM v1.5 `WF_Registry` "Constituent / Applies To" and `Legacy_Disposition` "Replacement") cannot be carried across to v1.6 by number and must be re-derived from v1.6 §4/§5 (Step 3.8 #8). **This conflict remains unresolved.**

---

## Step 3.4 (d) — Permission list (`registry.py`)

Design only. **RBAC is the IAM's**; this file declares *permissions* and *grants*, no roles table (`new-module-prompt.md:285-298`). Codes use the repository's implemented `module.resource.verb` shape.

### Permission vocabulary audit (finding 3)

Documented convention (`rbac-model.md:95-105`): exactly three segments; first segment = an existing `registry_module.code`; second = a **singular** resource noun; third from the closed verb list **`view · create · update · delete · approve · publish · review · assign · revoke · export · import · restore · manage`**.

Implemented exceptions actually shipped in `modules/placement/registry.py:59-86` (verbs outside that list): `view_self`, `auto_withdraw`, `schedule`, `issue`, `respond`, `expire`, `debar`, `self`. (System permissions there reuse the same exception verbs: `auto_withdraw`, `expire`.)

Every proposed ELM code is classified below as **documented-convention**, **implemented-exception (precedent exists)**, or **unresolved ELM decision (no documented verb and no shipped precedent — do not assume it will pass the CI regex)**. The first segment is `leave` = the chosen module code (satisfies the first-segment rule). Resource-noun singularness is noted where it fails.

| Proposed code | Verb | Verb class | Assessment |
|---|---|---|---|
| `leave.request.view_self` | view_self | implemented exception | precedent `placement_cell.application.view_self` |
| `leave.request.create` | create | documented convention | — |
| `leave.request.delete` | delete | documented convention | placement uses `delete` for withdrawal |
| `leave.request.view` | view | documented convention | — |
| `leave.request.review` | review | documented convention | — |
| `leave.request.approve` | approve | documented convention | pre-existing intended catalog also has this |
| `leave.substitute.assign` | assign | documented convention | — |
| `leave.substitute.respond` | respond | implemented exception | precedent `placement_cell.offer.respond` |
| `leave.cancellation.create` | create | documented convention | — |
| `leave.cancellation.approve` | approve | documented convention | — |
| `leave.extension.create` | create | documented convention | — |
| `leave.resumption.create` | create | documented convention | — |
| `leave.resumption.review` | review | documented convention | — |
| `leave.application.export` | export | documented convention | **resource-noun inconsistency**: other codes use `request`; pre-existing catalog uses `leave.request.*` |
| `leave.balance.view` | view | documented convention | — |
| `leave.balance.update` | update | documented convention | dangerous candidate; catalog lists it |
| `leave.type.manage` | manage | documented convention | catalog lists it |
| `leave.policy.manage` | manage | documented convention | — |
| `leave.calendar.manage` | manage | documented convention | — |
| `leave.record.manage` | manage | documented convention | — |
| `leave.offline.record` | record | **unresolved ELM decision** | `record` is neither a documented verb nor a shipped verb; `record` appears only as a *resource noun* (`placement_cell.record.manage`) |
| `leave.sla.manage` | manage | documented convention | — |
| `leave.ledger.credit` (system) | credit | **unresolved ELM decision** | no documented verb, no shipped precedent |
| `leave.year_end.run` (system) | run | **unresolved ELM decision** | no documented verb, no shipped precedent; `year_end` is not a singular resource noun |
| `leave.sla.dispatch` (system) | dispatch | **unresolved ELM decision** | no documented verb, no shipped precedent |

**Reconciliation with the pre-existing intended catalog** (`permission-catalog.md:145-155`, self-declared "intended taxonomy… not implemented", absent from `registry/permissions.json`): the catalog lists exactly seven `leave.*` codes — `request.view_self`, `request.create`, `request.delete`, `request.view`, `request.approve`, `balance.update`, `type.manage` — and grants `faculty`/`staff` → `leave.request.create`, `hr_officer` → `leave.request.approve` (`:196-197,201`). It omits `review`, `substitute.*`, `cancellation.*`, `extension.*`, `resumption.*`, `calendar.manage`, `offline.record`, `record.manage`, `sla.manage`. The `hr_officer` approve grant names a role the specification does not describe. **Reconciliation is an owner decision** (Step 3.8 #9). This is **[BLOCKED]** until the vocabulary and the catalog are reconciled.

### Proposed `PERMISSIONS` — **PROVISIONAL / BLOCKED (#9)** — do not treat as final

```python
MODULE = {
    "code": "leave", "label": "Employee Leave", "icon": "CalendarCheck",
    "base_path": "/leave", "nav_section": "People", "sort_order": 40, "status": "active",
}

# Every code below is PROVISIONAL. Columns in the audit table above give the class.
# `view_self` and `respond` have shipped precedents; `offline.record`, `ledger.credit`,
# `year_end.run`, `sla.dispatch` have NO documented verb or shipped precedent.
PERMISSIONS = [
    ("leave.request.view_self", "View own leave requests and balance"),
    ("leave.request.create", "Apply for leave"),
    ("leave.request.delete", "Withdraw own pending request"),
    ("leave.request.view", "View leave requests, within scope"),
    ("leave.request.review", "Record Unit Head review/recommendation"),
    ("leave.request.approve", "Final approve/reject a leave request"),
    ("leave.substitute.assign", "Nominate a substitute"),
    ("leave.substitute.respond", "Accept or decline a substitute request"),
    ("leave.cancellation.create", "Request cancellation of approved leave"),
    ("leave.cancellation.approve", "Approve a leave cancellation"),
    ("leave.extension.create", "Request extension of ongoing leave"),
    ("leave.resumption.create", "Submit resumption of duty"),
    ("leave.resumption.review", "Review a resumption submission"),
    ("leave.application.export", "Export a printable leave application"),
    ("leave.balance.view", "View balances within scope"),
    ("leave.balance.update", "Adjust a leave balance"),            # dangerous candidate
    ("leave.type.manage", "Configure leave types and entitlement rules"),
    ("leave.policy.manage", "Maintain policy parameters and hierarchy"),
    ("leave.calendar.manage", "Maintain and publish holiday/RH calendar"),
    ("leave.record.manage", "Maintain authorized leave records"),
    ("leave.offline.record", "Record already-sanctioned offline leave"),
    ("leave.sla.manage", "Configure SLA thresholds"),
]

SYSTEM_PERMISSIONS = [   # scheduled work; verbs unverified against the vocabulary
    "leave.ledger.credit",
    "leave.year_end.run",
    "leave.sla.dispatch",
]

SCOPE_PERMISSIONS = [...]  # PROVISIONAL
```

### `ROLE_GRANTS` — **BLOCKED (#4)**
Grants must be keyed by the **exact** `globals_designation` spelling (`new-module-prompt.md:302-304`). The specification's actors are named in the UC document (Unit Head; Deputy Registrar (Estt.) / Establishment Processing Role; Sanctioning Authority — Deputy Registrar (Estt.), Dean, Registrar, Director, or other configured competent authority; Leave Administrator; "Authorized administrative role"). **Whether any of these exist as rows in `globals_designation` is unverified; this blueprint does not assert they exist.** `faculty` and `staff` are the two kinds the platform holds by definition (`new-module-prompt.md:305-306`), but even those are conventions of the grant mechanism, not a verified designation list. A role the IAM cannot express is a **blocker** (`new-module-prompt.md:223-225`).

```python
# PROVISIONAL / BLOCKED (#4): every key below except possibly "faculty"/"staff"
# is UNVERIFIED to exist in globals_designation. Do not treat as a grant map yet.
ROLE_GRANTS = {
    # names below are taken from the UC document's Primary Actor column, NOT verified
    "<faculty-alias>": ["leave.request.view_self", "leave.request.create",
                        "leave.request.delete", "leave.cancellation.create",
                        "leave.extension.create", "leave.resumption.create",
                        "leave.application.export", "leave.substitute.assign",
                        "leave.substitute.respond"],
    "<staff-alias>":   ["... same as faculty ..."],
    "Unit Head":                ["leave.request.view", "leave.request.review",
                                 "leave.cancellation.approve"],
    "Deputy Registrar (Estt.)": ["leave.request.view", "leave.resumption.review"],
    "Dean":                     ["leave.request.view", "leave.request.approve"],
    "Registrar":                ["leave.request.view", "leave.request.approve"],
    "Director":                 ["leave.request.view", "leave.request.approve"],
    "Leave Administrator":      ["leave.request.view", "leave.record.manage",
                                 "leave.offline.record", "leave.calendar.manage",
                                 "leave.policy.manage", "leave.sla.manage",
                                 "leave.balance.view", "leave.balance.update"],
}
```

### `NAV_ITEMS` — **PROVISIONAL** (must satisfy `nav_matches_routes.py`)

```python
NAV_ITEMS = [
  {"code": "leave.my_leave", "label": "My Leave", "icon": "CalendarCheck",
   "to": "/leave/mine", "required_permission": "leave.request.view_self", "sort_order": 5},
  {"code": "leave.apply", "label": "Apply for Leave", "icon": "PlusCircle",
   "to": "/leave/apply", "required_permission": "leave.request.create", "sort_order": 10},
  {"code": "leave.approvals", "label": "Approvals", "icon": "Checks",
   "to": "/leave/approvals", "required_permission": "leave.request.review", "sort_order": 20},
  {"code": "leave.substitute", "label": "Substitute Requests", "icon": "UserSwitch",
   "to": "/leave/substitute", "required_permission": "leave.substitute.respond", "sort_order": 25},
  {"code": "leave.config", "label": "Leave Configuration", "icon": "SlidersHorizontal",
   "to": "/leave/config", "required_permission": "leave.policy.manage", "sort_order": 40},
  {"code": "leave.calendar", "label": "Holiday/RH Calendar", "icon": "CalendarDots",
   "to": "/leave/calendar", "required_permission": "leave.calendar.manage", "sort_order": 45},
]
```

### Acting-role hazard — **CONVENTION**
"Only the acting role counts" (`new-module-prompt.md:323-325`); a two-designation holder gets one role's view. `UserRole.is_primary` / `userrole_one_primary_per_scope` (`iam-domain-model.md:301,314-316`) is the deterministic tie-break (H1, `:333-336`). ELM must read the **session's active role**, not aggregate.

---

## Step 3.5 (e) — Endpoint list

All under `/api/v1/leave/`. Every endpoint sits behind **two** gates: **module grant**, then **permission** (`new-module-prompt.md:443-445`) **[CONVENTION]**. Query params are hostile: unparseable → 400 **[CONVENTION]**. Methods/paths are **PROVISIONAL** unless noted.

| Method | Path | Permission | Returns | Support | Class |
|---|---|---|---|---|---|
| GET | `/requests/self` | `leave.request.view_self` | own request list | BR-EL-012/016/022/034 | PROVISIONAL |
| POST | `/requests/` | `leave.request.create` | created request | CFR-EL-002/003; BR-EL-001–015 | EXPLICIT (UC) / PROVISIONAL |
| GET | `/requests/{id}` | `leave.request.view` (scoped) | request detail | BR-EL-036 | PROVISIONAL |
| POST | `/requests/{id}/withdraw` | `leave.request.delete` | withdrawn request | CFR-EL-018; BR-EL-022/034 | EXPLICIT (UC) / PROVISIONAL |
| GET | `/requests/{id}/export` | `leave.application.export` | printable artifact | CFR-EL-023 | EXPLICIT (UC) / PROVISIONAL |
| GET | `/balances/self` | `leave.request.view_self` | own balances | CFR-EL-022; BR-EL-002–009 | EXPLICIT (UC) / PROVISIONAL |
| GET | `/balances` | `leave.balance.view` | scoped balances | BR-EL-036 | PROVISIONAL |
| POST | `/substitute/{id}/respond` | `leave.substitute.respond` | recorded response | CFR-EL-012; BR-EL-015 | EXPLICIT (UC) / PROVISIONAL |
| POST | `/substitute/{id}/replace` | `leave.substitute.assign` | new nomination | CFR-EL-011; BR-EL-015; EL-UC-019 | EXPLICIT (UC) / PROVISIONAL |
| GET | `/approvals` | `leave.request.review` | scoped task queue | CFR-EL-013/014; BR-EL-017 | PROVISIONAL |
| POST | `/reviews/{id}` | `leave.request.review` | recommendation/decision | CFR-EL-013/014; BR-EL-016–017 | EXPLICIT (UC) / PROVISIONAL |
| POST | `/routing/{id}/forward` | `leave.request.review` | routed request | CFR-EL-014; BR-EL-018–019 | **BLOCKED (#4)** |
| POST | `/decisions/{id}` | `leave.request.approve` | final decision | CFR-EL-014/016; BR-EL-018–020 | **BLOCKED (#4)** |
| POST | `/cancellations/` | `leave.cancellation.create` | created cancellation | CFR-EL-019; BR-EL-023–024 | EXPLICIT (UC) / PROVISIONAL |
| POST | `/cancellations/{id}/decide` | `leave.cancellation.approve` | outcome | CFR-EL-014/019; BR-EL-023 | **BLOCKED (#4)** |
| POST | `/extensions/` | `leave.extension.create` | created extension | CFR-EL-020; BR-EL-025 | EXPLICIT (UC) / PROVISIONAL |
| POST | `/extensions/{id}/decide` | `leave.request.approve` | outcome | CFR-EL-020; BR-EL-025 | **BLOCKED (#4)** |
| POST | `/resumptions/` | `leave.resumption.create` | created resumption | CFR-EL-021; BR-EL-027 | EXPLICIT (UC) / PROVISIONAL |
| POST | `/resumptions/{id}/review` | `leave.resumption.review` | reviewed outcome | CFR-EL-021; BR-EL-027–028 | **BLOCKED (#3)** |
| GET/PUT | `/policy` | `leave.policy.manage` | policy params | CFR-EL-024; BR-EL-030 | **BLOCKED (#1)** |
| GET/PUT | `/hierarchy` | `leave.policy.manage` | hierarchy config | CFR-EL-024; BR-EL-018–019/030 | **BLOCKED (#1, #4)** |
| POST | `/calendar`, POST `/calendar/{id}/publish` | `leave.calendar.manage` | calendar | CFR-EL-025; BR-EL-031 | EXPLICIT (publish) / PROVISIONAL (range, #5/#11) |
| POST | `/offline-records/` | `leave.offline.record` | synchronized record | CFR-EL-027; BR-EL-029 | PROVISIONAL |
| PATCH | `/records/{id}` | `leave.record.manage` | allowed correction (never a sanction) | **CFR-EL-026; BR-EL-037** (+BR-EL-036) | EXPLICIT (UC) / PROVISIONAL (method) |
| GET/PUT | `/sla` | `leave.sla.manage` | SLA thresholds | CFR-EL-029; BR-EL-038 | EXPLICIT (UC) / PROVISIONAL |

> The `/records/{id}` row was corrected in Revision 2: it no longer cites retired `BR-EL-026`; its live support is `CFR-EL-026` + `BR-EL-037`. The endpoint must be incapable of sanctioning (BR-EL-037).

**`module-only` sidebar instruction (paste-ready for `Fusion-client` `INTEGRATED_MODULES`)** **[CONVENTION]**, e.g.:
`{ id: "leave", label: "Employee Leave", icon: "CalendarCheck", to: "/leave", section: "People" }`
(`new-module-prompt.md:338-341`). No nav entry may exist without a client route and vice-versa.

---

## Step 3.6 (f) — Contracts

`modules/leave/contracts.py` would expose (plural getters only, `ops/checks/contracts_are_plural.py`) **[CONVENTION + PROVISIONAL]**:
- `get_leave_status(user_ids: Sequence[int], on_date) -> Mapping[int, str]` **[PROVISIONAL]** — for attendance/HR awareness.
- `get_active_leave(user_ids: Sequence[int], within) -> Mapping[int, Sequence[LeaveWindow]]` **[PROVISIONAL]** — for HR/placement conflict checks.

ELM needs (`new-module-prompt.md:350-368`) — each is a dependency on an IAM/academics projection, **not** an ERP connection:

| ELM needs | Asked of | Status | Evidence |
|---|---|---|---|
| Who the user is; kind; designation(s); org unit; active role | session + IAM | partially available; authority/hierarchy resolution **not confirmed exposed** | `new-module-prompt.md:355-359`; `iam-domain-model.md` |
| Unit Head of an org unit | IAM/HR | **not evidenced (BLOCKED #4)** | PS §7 (`line 30`) |
| Employee list / directory | IAM `iter_employees` / `academic_directory` | available (platform) | `new-module-prompt.md:359` |
| Academic Calendar vacation periods (VL applicability) | academics/ERP | **missing contract (BLOCKED #2)** | PS §12 `line 48`; CFR-EL-008 |
| Attendance records (resumption sync) | academics/ERP | **missing contract (BLOCKED #3)** | CFR-EL-021; `current-state-assessment.md:59` |
| Employment facts (`hr.contracts.get_employments`) | `modules.hr` | **module unbuilt (BLOCKED)** | `roadmap-and-phases.md:175` |

Every missing item is a dependency to be added to a projection and API, never an ERP connection from ELM (`new-module-prompt.md:362-366`). In `module-only`, sparse answers are correct; the absent case is tested deliberately.

---

## Step 3.7 (g) — Scheduled work

`schedule.py` would export `BEAT_SCHEDULE`; merged into `config/celery.py` **[CONVENTION]**. Task names are **PROVISIONAL**.

| Task | Cadence | Support | Class | If it does not run |
|---|---|---|---|---|
| `leave.year_end` | Annual at configured boundary (TZ `Asia/Kolkata`) | EL-UC-020; CFR-EL-028; BR-EL-002–009 | mechanism CONVENTION · boundary **BLOCKED (#6)** | CL/RH/SCL never lapse; VL never converts; balances drift one full year. |
| `leave.sla_scan` | Periodic (hourly/day) | EL-UC-021; CFR-EL-031/032; BR-EL-032–033 | EXPLICIT (behaviour) / PROVISIONAL (cadence) | No reminders/escalations; SLA obligations unfulfilled. |

Each task is intended to be idempotent (`credit_year` partial unique; SLA fires only while pending) **[CONVENTION]**. The boundary definition (calendar vs fiscal; exact instant) is **BLOCKED (#6)**.

---

## Step 3.8 (h) — Open questions / unresolved-decisions register

Format: **issue — what is blocked — status**. No business outcome is chosen here. All items remain open.

1. **Policy-configuration lifecycle conflict [P0].** Specification: leave-policy parameters use *current configured values, no draft/publish/effective-version lifecycle* (PS §5 ¶23, PS §12 ¶46, **CFR-EL-024** + AFR-EL-024.4, BR-EL-030, EL-UC-014). Platform convention: admin config is *effective-dated and never edited* (`new-module-prompt.md:244-248`). Opposed for policy/hierarchy parameters (for the **holiday/RH calendar** both agree on a publish lifecycle: PS §12 ¶47, CFR-EL-025, BR-EL-031, EL-UC-015). **Blocks**: `LeaveTypePolicy`/`HierarchyStep` shape; `/policy`, `/hierarchy`; "no seeded policy must not 500". **Not resolved.**
2. **Academic Calendar contract missing [P0].** VL applicability (BR-EL-006, CFR-EL-008) needs published vacation periods from an external service (PS §12 ¶48). No platform ACL/contract exists (only the *results* snapshot pattern, `academic-snapshot-integration.md`). **Blocks**: VL validation; unavailable-data behaviour. **Not resolved.**
3. **Employee-attendance contract missing [P0].** BR-EL-028 / CFR-EL-021 require synchronising attendance after early/late resumption. Attendance lives in the live ERP app `academic_information` (`current-state-assessment.md:59`); no integration contract exists. **Blocks**: resumption review completion effects. **Not resolved.**
4. **Approver/authority identity and routing source [P0].** BR-EL-016–020 need Unit Head resolution and a configurable hierarchy. The **source of the hierarchy configuration** and whether `Unit Head` / `Deputy Registrar (Estt.)` / `Dean` / `Registrar` / `Director` / `Leave Administrator` exist in `globals_designation` are **unconfirmed**. `new-module-prompt.md:223-225` makes an inexpressible role a **blocker**. **Blocks**: `services/routing.py`, `ROLE_GRANTS` keys, approval-queue scoping.
   - 4b. **Approver behaviour gaps**: the spec requires routing to a "resolved final Sanctioning Authority" but does not state who configures/resolves it, fallback when unresolved, or self-approval prevention. **Blocks**: routing + escalation correctness.
5. *(folded into #4.)*
6. **Year-end boundary definition [P1].** "Configured year-end boundary" (PS §13, CFR-EL-028) is not given a concrete rule (calendar vs fiscal year; exact instant). Repo supplies only the TZ (`base.py:240-245`). **Blocks**: `leave.year_end` schedule entry.
7. **Entitlement allocation timing / proration / rounding [P1].** Explicit amounts exist (see entitlement classification). **Not stated**: when within the year credit is allocated; proration for mid-year joiners/leavers; rounding of fractional results beyond a half-day (incl. the final rounding of the "fractional VL→EL conversion"); SCL consumption granularity. **Blocks**: `domain/entitlement.py` edge cases; year-end math for partial-year members. (`ANNUAL_CREDIT` is idempotency only.)
8. **Workflow-registry reconciliation (v1.6 vs RTM v1.5) [P1].** v1.6 STT is used; numbered `BW-EL-nn` cross-references from RTM v1.5 cannot be mapped by number. **Blocks**: any artefact keyed to v1.5 Basis-Workflow numbers. Composite-level traces are safe. **Retained / unresolved.**
9. **Permission vocabulary and catalog reconciliation [P1].** Documented closed verb list (`rbac-model.md:100-101`) omits verbs the shipped `placement_cell` manifest already uses (`view_self`, `auto_withdraw`, `schedule`, `issue`, `respond`, `expire`, `debar`, `self`). Four proposed ELM codes have *no* documented verb and *no* shipped precedent (`leave.offline.record`, `leave.ledger.credit`, `leave.year_end.run`, `leave.sla.dispatch`); one uses a resource noun that conflicts with the catalog (`leave.application.export` vs `leave.request.*`). The catalog's `hr_officer → leave.request.approve` names a role the spec does not describe. **Blocks**: exact `registry.py` codes, `make permissions`, CI permission-string test. **Not resolved.**
10. **Missing G-01…G-18 adjudication record [P1].** The 18 adjudications are referenced throughout but the record itself is **not in the bundle**. **Blocks**: independent verification that a rule was faithfully carried (not build-time, since the baseline already reflects them). Cited by the Step 8 requirement "No retired id is cited" (`new-module-prompt.md:692`).
11. **Academic Calendar vs holiday/RH calendar ownership [P2].** Two distinct calendars exist: the ELM-maintained holiday/RH calendar (BR-EL-031) and the external Academic Calendar for VL vacation periods (#2). Their relationship is unstated. **Blocks**: calendar-model design at the seam and the "governing date range" constraint (#5).

---

## Implementability classification (assignment item 8)

| Class | Items |
|---|---|
| **Implementable from explicit requirements** | CL/RH/SCL/EL/COL **flat entitlement amounts and carry/lapse flags** (BR-EL-002–009); half-day CL (010); continuous-day counting (011); overlap + half-day exception (012); Station Leave coupling (013); substitute eligibility + consent gate (014–015); Unit-Head-final CL/RH and recommendation logic (016–017); Director self-sanction (020); withdrawal (022, 034); cancellation mechanics (023–024); extension mechanics (025); resumption normal/early/late outcomes (027–028); offline synchronization (029); SLA reminder/escalation pending-only logic (032–033, 038); notifications on assignment/decision (035); the full CW-EL-01…04 state machine (WF v1.6 STT). |
| **Implementable only via existing platform conventions** | Append-only ledger (`new-module-prompt.md:241-242`); idempotent `ANNUAL_CREDIT` partial unique (`testing-strategy.md:49-50`) — **idempotency only**; `select_for_update` choke points; outbox/idempotent consumers (`event-catalog.md:30,67`); notifications as data (`event-catalog.md:205-220`); IAM permission format + two-gate enforcement; `TimeStampedModel`/`UserScopedModel`. |
| **Partially implementable — missing portion identified** | Entitlement work is split: **explicit amounts** can be built; **allocation timing, proration, rounding, SCL granularity remain blocked (#7)**. Routing/authority (#4); VL vacation applicability (#2); resumption attendance sync (#3); year-end scheduling (#6); policy/hierarchy model (#1). |
| **Not implementable as written without clarification** | EL-UC-014 `/policy` `/hierarchy` model (#1); `services/routing.py` final-authority resolution (#4); VL applicability gate (#2); resumption completion effects (#3); `leave.year_end` boundary (#6); entitlements for partial-year members (#7). |

---

## Implementation sequence (assignment item 9) — **post-approval only; does not authorise any application-code change now**

> **Approval gate (finding 10).** Steps 1–8 below are a *proposed* order for work **after** the assignment owner approves this blueprint. **Nothing in this section authorises creating application code, migrations, tests, configuration changes, or frontend files before that approval.** The safe work available *before* approval is planning-only and is listed separately at the end.

1. **Module skeleton + integration only** — `modules/leave/` layout, `apps.py`, `DOMAIN_MODULES`/`.importlinter`, urls, empty `registry.py`, `schedule.py`, client registry entry. (No business logic.)
2. **`domain/` rules that need no unresolved input** — explicit entitlement amounts, half-day, continuous counting, overlap, substitute eligibility, VL→EL ratio arithmetic, resumption date comparison. Unit tests would be *written* here but the assignment forbids systematic functional testing during the experiment (see integrity note).
3. **`models/` + ledger** — policy (**shape BLOCKED #1** → interim placeholder only), calendar (**range semantics PROVISIONAL #5/#11**), request/decision/task, ledger with the `ANNUAL_CREDIT` partial unique. Migrations.
4. **`services/` + state machine for the contract-free flows** — apply (non-VL), review, withdrawal, cancellation, substitution, resumption state moves, year-end math (mechanism only).
5. **`api/` transport + two gates** for the contract-free endpoints.
6. **Notifications + SLA tasks**; leave `leave.year_end` **wiring disabled until #6 is ruled**.
7. **Blocked flows, only after owner rulings** — VL applicability (#2), routing/resolution (#4), resumption attendance sync (#3), policy/hierarchy versioning (#1), entitlement timing/proration/rounding (#7), calendar range (#5/#11).
8. **Frontend pages**, then ops/docs `make schema`/`make permissions`, readiness command.

### Safe planning-only activities before approval (no code)
- Refine this blueprint and the unresolved-decisions register.
- Prepare the owner-question list for items #1–#11.
- Draft (but do not create in the repo) the module's file tree and naming notes for review.
- **Do not create** `modules/leave/`, change `config/settings/base.py`, `.importlinter`, `config/urls.py`, `client/src/app/registry.ts`, `registry/permissions.json`, or `openapi/fusion-integrated.v1.yaml` until the blueprint is approved.

---

## Traceability: requirements → components → **planned** tests (none executed — assignment item 10)

Tests are **planned only**; none has run and none is claimed to pass. Test files would mirror `modules/placement/tests/` (`new-module-prompt.md:478-480,516-562`).

| Requirement | Component | Planned test |
|---|---|---|
| BR-EL-002–009 explicit entitlement amounts | `domain/entitlement.py`, ledger | `test_entitlements.py` (amounts/carry/lapse) |
| **Unresolved** entitlement timing/proration/rounding (#7) | `domain/entitlement.py`, `services/year_end.py` | not plannable until #7 ruled |
| `ANNUAL_CREDIT` idempotency | ledger | `test_concurrency.py` (double-credit, `select_for_update`) |
| BR-EL-005/007 year-end + VL→EL | `services/year_end.py`, `domain/conversion.py` | `test_year_end.py` (ratio; final rounding **blocked #7**) |
| BR-EL-010 half-day | `domain/counting.py` | `test_counting.py` |
| BR-EL-011 continuous days | `domain/counting.py` | `test_counting.py` |
| BR-EL-012 overlap | `domain/overlap.py` | `test_overlap.py` (half-day exception) |
| BR-EL-014–015 substitute | `services/substitute.py` | `test_substitute.py` |
| BR-EL-016–020 routing | `services/routing.py` | `test_routing.py` — **blocked (#4)** |
| BR-EL-022/034 withdraw/no-modify | `services/withdraw.py`, api | `test_withdrawal.py` (no update route) |
| BR-EL-023–025 cancellation/extension | services, ledger | `test_cancellation.py`, `test_extension.py` |
| BR-EL-027–028 resumption | `domain/resumption.py` | `test_resumption.py` — attendance part **blocked (#3)** |
| BR-EL-029 offline | `services/offline.py` | `test_offline.py` (no workflow created) |
| BR-EL-030/031 policy/calendar | models | `test_config.py` (policy **blocked #1**), `test_calendar.py` (range **blocked #5/#11**) |
| BR-EL-032–033/038 SLA | `tasks.py`, schedule | `test_sla.py` (pending-only), `test_schedule.py` |
| BR-EL-035 notifications | services | `test_notifications.py` |
| BR-EL-036 authorization | `registry.py`, api | `test_privilege_escalation.py`, `test_registry_codes.py` |
| BR-EL-037 maintenance≠sanctioning; **EL-UC-017** | services, api | `test_record_maintenance.py` — must not sanction |
| State machine (CW-EL-01…04) | `domain/state_machine.py` | `test_state_machine.py` (enumerate illegal transitions) |
| CFR-EL-022 scoping | `selectors/scoping.py` | `test_scoping_isolation.py` (own rows only; 404 not 403) |
| All list endpoints | selectors | `test_query_budgets.py` |

---

## Assignment rule 10 / integrity

- **No application code, migrations, tests, config changes, frontend files, or specification edits were made.** The only artefact created/edited is this document. **No test has been executed and none is claimed to pass.**
- Retired identifiers (`BR-EL-021`, `BR-EL-026`, `EL-UC-006`, `WF-EL-02/06/07/08`, superseded SRS ids) are preserved for traceability and are **never cited as live requirements** — including the corrected EL-UC-017 support.
- Submitted pending requests are never modified in place; the specified route is withdrawal → new application (BR-EL-034, CFR-EL-017).
- No business rule was invented to complete the design; no conflicting lifecycle was selected; every gap is in Step 3.8.
- Every model, endpoint, permission, scheduled task and state transition above carries a class tag (**EXPLICIT / CONVENTION / PROVISIONAL / BLOCKED**).

## Approval blockers (must be ruled before implementation can be complete)

- **P0:** #1 policy/hierarchy lifecycle; #2 Academic Calendar contract; #3 attendance contract; #4 approver identity + routing source (incl. 4b semantics).
- **P1:** #6 year-end boundary; #7 entitlement timing/proration/rounding; #8 WF v1.6↔RTM v1.5 mapping; #9 permission vocabulary + catalog reconciliation; #10 G-01…G-18 adjudication record.
- **P2:** #11 holiday/RH vs Academic Calendar ownership and the "governing date range" constraint.
- **Identity confirmations:** module code `leave` (vs the illustrative `leave_elm`); blueprint filename (assignment template `leave-blueprint.md`).
