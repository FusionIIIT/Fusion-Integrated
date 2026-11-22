# MMS Module Blueprint — Review Draft

**Module:** MMS (Mess Management System) — ENTIRE module  
**Repository:** Fusion-Integrated  
**Branch:** `assignment-9-mms` (clean working tree; no commits; no production code modified)  
**Pair ID:** `16B`  
**Student 1 / Builder:** Vishvajeet  
**Student 2 / Independent reviewer & tester:** Shaheen  
**Environment:** `module-only`  
**Spec source:** `../specifications/` — five `.docx` files (Problem Statement, CFR/AFR Registry, Use Cases, Business Rules, Workflows)  
**Status:** Review draft awaiting blueprint approval from Shaheen before any implementation  
**Artifact type:** Temporary review artifact. Final location: `docs/[NN]-mms/[module_code]-blueprint.md` (NN and module_code proposed below, unconfirmed)

---

## Proposed identifiers (UNCONFIRMED — must be approved before use)

| Placeholder | Proposed value | Basis | Confirmation needed |
|-------------|---------------|-------|---------------------|
| `[module_code]` | `mms` | Lowercase, singular-ish, no underscores; matches spec family token `MMS`. URL segment `/api/v1/mms/`, client basePath `/mms`, registry code `mms`, permission prefix `mms.` | **UNCONFIRMED** — not found in repo or assignment docs |
| `[NN]` | `09` | Next free docs folder number after existing `00`–`08` | **UNCONFIRMED** — not assigned by mentor; do not create `docs/09-mms/` until confirmed |
| `[ID_PREFIX]` | `MMS` | Spec family token. Actual ID forms vary: `BR-MMS-`, `MMS-UC-`, `BW-MMS-`, `CW-MMS-`, `CFR-MMS-`, `AFR-MMS-` | **UNCONFIRMED** — read off spec documents; no single `PC-` style prefix exists in MMS specs |
| `[MODULE_NAME]` | Mess Management System (MMS) | PS §3.1 | Confirmed from assignment |

**Designation spellings (UNCONFIRMED):** `Mess Admin`, `Mess Caretaker`, `Mess Warden` — PS actor labels. Exact `globals_designation` spellings not found in repository (only `mess_committee` appears as a functional-role example in `docs/02-iam/rbac-model.md:53`). Must be confirmed against ERP/fixture before `ROLE_GRANTS` keys are written.

**Decision-period value (UNCONFIRMED):** PS §3.3.7 mentions "12 hours as intended" but explicitly leaves the value institution-defined (ISS-MMS-013). Model as a configurable effective-dated policy; do not seed a default.

---

## Assignment context

This draft follows Steps 3.1–3.8 of `docs/08-delivery/new-module-prompt.md` (the official Assignment 9 build prompt). It covers the FULL MMS module: all 22 CFRs, 101 AFRs, 31 UCs, 41 active BRs, 16 basis workflows, 5 composite workflows. Retired IDs `BR-MMS-037` and `MMS-FR-102` are excluded and must not be cited in code.

Approval gates before implementation:
1. Shaheen (Student 2) approves this blueprint in writing (online-ai-assignment-guide.md; new-module-prompt.md §0/§3.8).
2. Every known gap, shared-file change, and new dependency approved in writing and recorded in the quality report.
3. Review rounds until `VERDICT: 10/10 in all nine dimensions` (module-review-prompt.md §3).

Strictly NOT done yet: no Django models, migrations, APIs, frontend, module registration, commits, pushes, or PRs.

---

## Step 3.1 (a) — Traceability table

One row per live ID. Layer = where the rule is enforced (`domain/`, `models/`, `selectors/`, `services/`, `api/`, `schedule.py`, `frontend/`, `none` for boundary/scope rules). Enforcement point = planned file/function. "Derived" means the mapping was obtained by reading rule text, not from a populated spec matrix (the CFR/AFR mapping columns are empty in the supplied registry). "Blocked" means an authoritative ruling is required before implementation.

### CFRs (22 — all active)

| Id | What it requires | Layer | Enforcement point (planned) | Tests | Notes |
|----|------------------|-------|-----------------------------|-------|-------|
| CFR-MMS-001 | Module scope boundary: only mess-management functions + explicit integrations/notification triggers; exclude payment/accounting/payroll/procurement/inventory and institutional policy definition | domain + api | `modules/mms/domain/rules.py`; every view; `BR-MMS-001`, `BR-MMS-036` checks | test_domain, test_privilege_escalation | Full coverage |
| CFR-MMS-002 | Mess Admin assigns/reassigns exactly one active Caretaker + one active Warden for specified durations; mid-cycle changes immediate; pending Caretaker work handoff | domain + services | `modules/mms/domain/state_machine.py`; `services/roles.py` | test_domain, test_privilege_escalation, test_journeys (UC-001) | UC-001 not workflow-grounded (isolated service) |
| CFR-MMS-003 | Mess Admin restricted from operational mess data (student requests, billing, rebates, special food, vacation responses, feedback) | selectors + api | `selectors/scoping.py`; every detail/list view | test_recruiter_isolation (as Mess Admin), test_privilege_escalation | Full coverage |
| CFR-MMS-004 | Caretaker-controlled registration windows; students submit only while open; Caretaker approves/rejects | domain + services + api | `state_machine.py`; `services/registration.py`; `api/views.py` | test_domain, test_journeys (UC-002,003,004), BW-MMS-01/02 | Full coverage |
| CFR-MMS-005 | Student deregistration anytime; Caretaker approves/rejects; decision recorded; approved effect from next calendar day | domain + services + schedule | `services/deregistration.py`; `schedule.py` (UC-027 event) | test_domain, test_schedule, test_journeys (UC-005,006,027), BW-MMS-03/04 | Full coverage |
| CFR-MMS-006 | Warden views operational student requests for oversight only; cannot decide | selectors + api | `scoping.py` Warden read-only scope; no decision endpoints for Warden | test_recruiter_isolation (Warden), test_privilege_escalation | Full coverage; UC-007 not workflow-grounded |
| CFR-MMS-007 | Student-visible request status/history; submission + decision notifications for registration/deregistration | services + api + notifications | `services/notifications.py` topics; `selectors/scoping.py` own-requests-only | test_notification_worker, test_query_budgets, test_journeys | Full coverage; BR-MMS-042 own-request |
| CFR-MMS-008 | Day-wise + meal-wise weekly menu; authorized viewing; Caretaker maintains items; student notifications on update; Mess Admin visibility unresolved | models + services + api + notifications | `models/menu.py`; `services/menu.py`; `api/views.py`; notification topic `menu.updated` | test_domain, test_privilege_escalation, test_journeys (UC-008,009) | **Partial coverage**; BR-MMS-038 Needs Clarification |
| CFR-MMS-009 | Monthly bills on calendar-month cycle from served-day + special-meal + rebate components; Caretaker review/finalize/publish; students view published bills + balances; no payment settlement | services + schedule + api | `services/billing.py`; `schedule.py` (UC-030 event); `api/views.py` | test_domain, test_schedule, test_journeys (UC-010,011,030), BW-MMS-16 | Full coverage; CW-MMS-03/05 related |
| CFR-MMS-010 | Accept + store student text feedback; Caretaker + Warden view; no formal resolution workflow | models + services + api | `models/feedback.py`; `services/feedback.py`; `api/views.py` | test_domain, test_privilege_escalation, test_journeys (UC-012,013) | Full coverage |
| CFR-MMS-011 | Student rebate submission with reason + dates; reason rules, min duration, lead-time, non-overlap | domain + services + api | `domain/rules.py` rebate validation; `services/rebate.py` | test_domain, test_journeys (UC-014), BW-MMS-05/06/07 | Full coverage |
| CFR-MMS-012 | Caretaker approves/rejects rebate; may modify dates before approval where external policy permits; approved dates drive billing; students track status; notifications | domain + services + api + notifications | `state_machine.py` rebate; `services/rebate.py`; `services/billing.py` adjustment | test_domain, test_schedule, test_journeys (UC-015,026,030), BW-MMS-05/06/07 | Full coverage; BR-MMS-025 external-policy boundary not defined |
| CFR-MMS-013 | Caretaker creates vacation survey for currently registered students; sets deadline; survey-creation notification; reminders without inventing cadence | models + services + schedule + notifications | `services/survey.py`; `schedule.py` (UC-031 reminder, cadence unspecified) | test_domain, test_schedule, test_journeys (UC-016,031), BW-MMS-08/09/10 | Full coverage; reminder cadence unspecified (ISS-MMS-019) |
| CFR-MMS-014 | Yes/No vacation responses only; default No for non-responding registered students at deadline; Caretaker views summary | domain + services + schedule + api | `domain/rules.py` response options; `schedule.py` (UC-028 default No); `selectors/scoping.py` summary | test_domain, test_schedule, test_journeys (UC-017,028,018), BW-MMS-08/09/10 | Full coverage |
| CFR-MMS-015 | Student submits special-food request for illness/personal event only with lead time; submission notification | domain + services + api + notifications | `domain/rules.py` lead-time (BR-MMS-028); `services/special_food.py`; notification topic `special_food.submitted` | test_domain, test_journeys (UC-019), BW-MMS-11..15 | Full coverage |
| CFR-MMS-016 | Caretaker approves/rejects special-food within decision period; auto-reject undecided on expiry; decision notification | domain + services + schedule + notifications | `state_machine.py` special food; `schedule.py` (UC-029 default reject); notification topics | test_domain, test_schedule, test_journeys (UC-020,029), BW-MMS-11/12 | Full coverage; decision period institution-defined (ISS-MMS-013) |
| CFR-MMS-017 | Special-food status/history Requested→Approved→Rejected→Served→Cancelled; Served/Cancelled only after Approved; fulfillment notifications; approved charges to billing; fulfillment-actor and cancellation-billing unresolved | models + domain + services + api + billing | `state_machine.py`; `services/special_food.py`; `services/billing.py` charge link | test_domain, test_schedule, test_journeys (UC-019,020,021,029), BW-MMS-11..16 | **Partial coverage**; ISS-MMS-014/015 unresolved |
| CFR-MMS-018 | Caretaker or Warden publish announcements; student notifications; announcement history; MMS actors view per access rights | models + services + api + notifications | `models/announcement.py`; `services/announcement.py`; notification topic `announcement.published` | test_domain, test_privilege_escalation, test_journeys (UC-022,023) | Full coverage |
| CFR-MMS-019 | Warden views/searches registered-student lists, rebate summaries, vacation response summaries | selectors + api | `scoping.py` Warden supervisory scope; report endpoints | test_recruiter_isolation (Warden), test_query_budgets | Full coverage |
| CFR-MMS-020 | Caretaker generates registration-trend, special-meal logs, billing-summary reports | selectors + api | `scoping.py` Caretaker operational scope; report endpoints | test_query_budgets | Full coverage |
| CFR-MMS-021 | Reporting limited to MMS operational/supervisory info; exclude external financial/payroll/procurement/inventory reports | api + domain | report endpoints; `BR-MMS-001`/`BR-MMS-036` boundary checks | test_privilege_escalation | Full coverage |
| CFR-MMS-022 | Notifications only for explicitly listed PS events; MMS does not own email delivery infrastructure | services + notifications | `services/notifications.py` TOPICS allowlist; outbox delivery | test_notification_worker | Full coverage; BR-MMS-035 |

### AFRs (101 — all active; MMS-FR-102 retired)

Listed compactly under their parent CFR. Each AFR is a row in the master traceability; here grouped for readability with the enforcement point and test named once per AFR cluster. `Mapped UC/BR/WF` columns are empty in the supplied registry; all mappings below are **derived** by reading rule text.

| CFR | AFR IDs | What it requires | Enforcement point (planned) | Tests | Notes |
|-----|---------|------------------|-----------------------------|-------|-------|
| CFR-MMS-001 | AFR-MMS-001, AFR-MMS-100, AFR-MMS-101 | Mess-management only; no payment/accounting/payroll/procurement/inventory; no institutional policy definition | `domain/rules.py` scope checks; every view | test_domain, test_privilege_escalation | Full |
| CFR-MMS-002 | AFR-MMS-002, 003, 004, 005, 006, 096, 097, 098, 099 | Assign Caretaker; assign Warden; reassign mid-cycle; exactly one active Caretaker; exactly one active Warden; time-bound assignments; immediate reassignment effect; pending-request handoff; consume employee identities only | `services/roles.py`; `state_machine.py` role cardinality | test_domain, test_privilege_escalation, test_schedule, test_journeys (UC-001) | Full |
| CFR-MMS-003 | AFR-MMS-007 | Prevent Mess Admin access to operational mess data | `scoping.py` (empty scope for Mess Admin); api 404 | test_recruiter_isolation, test_privilege_escalation | Full |
| CFR-MMS-004 | AFR-MMS-012, 013, 015 | Open registration window; accept registration only while open; Caretaker approves/rejects registration | `services/registration.py`; `state_machine.py` | test_domain, test_journeys (UC-002,003,004), BW-MMS-01/02 | Full |
| CFR-MMS-005 | AFR-MMS-014, 016, 017, 018 | Deregister anytime; Caretaker approves/rejects; record decision; next-calendar-day effect | `services/deregistration.py`; `schedule.py` UC-027 | test_domain, test_schedule, test_journeys (UC-005,006,027), BW-MMS-03/04 | Full |
| CFR-MMS-006 | AFR-MMS-019, 020 | Warden views operational requests; Warden cannot decide | `scoping.py` Warden read-only; no Warden decision endpoints | test_recruiter_isolation, test_privilege_escalation | Full |
| CFR-MMS-007 | AFR-MMS-011, 021, 022, 023 | Student tracks own status/history; maintain registration/deregistration status+history; submission + decision notifications | `selectors/scoping.py` own-requests; `services/notifications.py` | test_query_budgets, test_notification_worker, test_journeys (UC-026) | Full |
| CFR-MMS-008 | AFR-MMS-008, 024, 025, 026, 027, 028, 029, 030, 031, 032 | Student/Caretaker/Warden view menu; day-wise+meal-wise storage; Caretaker add/delete/modify; Mess Admin visibility conflict; menu-update notifications | `models/menu.py`; `services/menu.py`; notification topic | test_domain, test_privilege_escalation, test_journeys (UC-008,009) | Partial; AFR-MMS-028 blocked (BR-MMS-038 conflict) |
| CFR-MMS-009 | AFR-MMS-009, 033, 034, 035, 036, 037, 038, 039, 040, 041, 042, 043 | Student view bills; calendar-month billing; served-day charges; special-meal charges; rebate deductions; Caretaker review; Caretaker finalize; Caretaker publish; student view published bill; student view balance; no payment settlement; publication notification | `services/billing.py`; `schedule.py` UC-030; `api/views.py` finalize/publish | test_domain, test_schedule, test_journeys (UC-010,011,030), BW-MMS-16 | Full |
| CFR-MMS-010 | AFR-MMS-044, 045, 046, 047, 048 | Student submit feedback; Caretaker view feedback; Warden view feedback; store feedback; no resolution workflow | `models/feedback.py`; `services/feedback.py` | test_domain, test_privilege_escalation, test_journeys (UC-012,013) | Full |
| CFR-MMS-011 | AFR-MMS-049, 050, 051, 052, 053, 054 | Student submit rebate; reason+start+end captured; reason enum + explanation for Other; duration >= 3 days; >= 1 day lead-time; no overlap | `domain/rules.py` rebate validation; `services/rebate.py` | test_domain, test_journeys (UC-014), BW-MMS-05/06/07 | Full |
| CFR-MMS-012 | AFR-MMS-055, 056, 057, 058, 059, 060, 061 | Caretaker approve/reject rebate; modify dates before approval where external policy permits; approved dates for billing; students track Pending/Approved/Rejected; auto-apply rebate adjustments; submission + decision notifications | `state_machine.py` rebate; `services/rebate.py`; `services/billing.py`; notifications | test_domain, test_schedule, test_journeys (UC-015,026,030), BW-MMS-05/06/07 | Full; AFR-MMS-056 external-policy range undefined |
| CFR-MMS-013 | AFR-MMS-062, 063, 065, 068, 069 | Caretaker create vacation survey; only currently registered students; set deadline; survey-creation notification; reminders without invented cadence | `services/survey.py`; `schedule.py` UC-031; notifications | test_domain, test_schedule, test_journeys (UC-016,031), BW-MMS-08/09/10 | Full; reminder cadence unspecified |
| CFR-MMS-014 | AFR-MMS-064, 066, 067 | Yes/No response only; default No at deadline for non-responders; Caretaker views summary | `domain/rules.py` response options; `schedule.py` UC-028; `selectors/scoping.py` | test_domain, test_schedule, test_journeys (UC-017,028,018), BW-MMS-08/09/10 | Full |
| CFR-MMS-015 | AFR-MMS-070, 071, 075 | Student submit special-food; accept only >= 1 calendar day before requested date; submission notification | `domain/rules.py` lead-time; `services/special_food.py`; notifications | test_domain, test_journeys (UC-019), BW-MMS-11..15 | Full |
| CFR-MMS-016 | AFR-MMS-072, 073, 076 | Caretaker approve/reject within decision period; auto-reject undecided on expiry; decision notification | `state_machine.py` special food; `schedule.py` UC-029; notifications | test_domain, test_schedule, test_journeys (UC-020,029), BW-MMS-11/12 | Full; decision period institution-defined |
| CFR-MMS-017 | AFR-MMS-074, 077, 078, 079, 080 | Status/history through 5 states; Served/Cancelled only after Approved; fulfillment notifications; approved charges to monthly bill | `state_machine.py`; `services/special_food.py`; `services/billing.py` charge | test_domain, test_schedule, test_journeys (UC-019,020,021,029), BW-MMS-11..16 | Partial; ISS-MMS-014/015 unresolved |
| CFR-MMS-018 | AFR-MMS-010, 081, 082, 083, 084, 085 | Student view announcements; Caretaker publish; Warden publish; publication notification; announcement history; actors view per rights | `models/announcement.py`; `services/announcement.py`; notifications | test_domain, test_privilege_escalation, test_journeys (UC-022,023) | Full |
| CFR-MMS-019 | AFR-MMS-086, 087, 088 | Warden view/search registered-student lists; rebate summaries; vacation response summaries | `scoping.py` Warden supervisory scope; report endpoints | test_query_budgets | Full |
| CFR-MMS-020 | AFR-MMS-089, 090, 091 | Caretaker registration-trend reports; special-meal logs; billing-summary reports | `scoping.py` Caretaker operational scope; report endpoints | test_query_budgets | Full |
| CFR-MMS-021 | AFR-MMS-092, 093 | Reports limited to MMS info; no external financial/payroll/procurement/inventory reports | report endpoints; boundary checks | test_privilege_escalation | Full |
| CFR-MMS-022 | AFR-MMS-094, 095 | Notifications only for listed PS events; no email infrastructure ownership | `services/notifications.py` TOPICS allowlist | test_notification_worker | Full |

### Use Cases (31 — none retired)

| Id | What it requires | Layer | Enforcement point | Tests | Notes |
|----|------------------|-------|-------------------|-------|-------|
| MMS-UC-001 | Assign/reassign Caretaker+Warden; exactly one active each; immediate mid-cycle effect; pending-request handoff; no operational data access | domain + services | `services/roles.py`; `state_machine.py` cardinality | test_domain, test_privilege_escalation, test_journeys | Not workflow-grounded |
| MMS-UC-002 | Open registration window | services | `services/registration.py` open_window | test_domain, test_journeys | BW-MMS-01/02 |
| MMS-UC-003 | Submit registration during open window | domain + services + api | `services/registration.py`; window-open guard | test_domain, test_journeys | BW-MMS-01/02 |
| MMS-UC-004 | Approve/reject registration; decision notification | services + notifications | `services/registration.py` decide; notification | test_domain, test_journeys | BW-MMS-01/02 |
| MMS-UC-005 | Submit deregistration anytime | services | `services/deregistration.py` submit | test_domain, test_journeys | BW-MMS-03/04 |
| MMS-UC-006 | Approve/reject deregistration; record decision; approved → Awaiting Effective Date | services + schedule | `services/deregistration.py`; `schedule.py` UC-027 | test_domain, test_schedule, test_journeys | BW-MMS-03/04 |
| MMS-UC-007 | Warden views operational requests oversight-only | selectors + api | `scoping.py` Warden scope | test_recruiter_isolation | Not workflow-grounded |
| MMS-UC-008 | Publish/update weekly menu; menu-update notifications | services + notifications | `services/menu.py`; notification topic | test_domain, test_journeys | No workflow mapping |
| MMS-UC-009 | View weekly menu per access rights | selectors + api | `scoping.py` menu scope | test_domain, test_query_budgets | BR-MMS-038 conflict |
| MMS-UC-010 | Review/finalize/publish monthly bills | services + api | `services/billing.py` finalize/publish | test_domain, test_journeys | BW-MMS-16 |
| MMS-UC-011 | View monthly bills + outstanding balances | selectors + api | `scoping.py` own bills | test_domain, test_query_budgets | |
| MMS-UC-012 | Submit text feedback | services | `services/feedback.py` submit | test_domain, test_journeys | |
| MMS-UC-013 | View feedback (Caretaker/Warden) | selectors + api | `scoping.py` | test_domain, test_privilege_escalation | |
| MMS-UC-014 | Submit rebate with reason + dates; validate duration/lead-time/overlap | domain + services + api | `domain/rules.py`; `services/rebate.py` | test_domain, test_journeys | BW-MMS-05/06/07 |
| MMS-UC-015 | Approve/reject rebate; modify dates before approval where policy permits; billing adjustment; notification | domain + services + api + billing | `state_machine.py`; `services/rebate.py`; `services/billing.py` | test_domain, test_journeys | BW-MMS-05/06/07 |
| MMS-UC-016 | Create vacation survey for registered students; set deadline; creation notification | services + notifications | `services/survey.py`; notification | test_domain, test_journeys | BW-MMS-08/09/10 |
| MMS-UC-017 | Respond Yes/No to vacation survey | domain + services | `domain/rules.py` Yes/No; `services/survey.py` respond | test_domain, test_journeys | BW-MMS-08/09 |
| MMS-UC-018 | View vacation survey response summary (Caretaker) | selectors + api | `scoping.py` | test_domain, test_query_budgets | Not workflow-grounded |
| MMS-UC-019 | Submit special-food request with reason + requested date; validate lead time; record Requested; submission notification | domain + services + api + notifications | `domain/rules.py` lead-time; `services/special_food.py`; notification | test_domain, test_journeys | BW-MMS-11..15 |
| MMS-UC-020 | Approve/reject Requested special-food within decision period; decision notification; prevent second decision | domain + services + api + notifications | `state_machine.py`; `services/special_food.py` decide | test_domain, test_journeys | BW-MMS-11..15; period institution-defined |
| MMS-UC-021 | Record Served/Cancelled for Approved special-food; fulfillment notification | domain + services + api + notifications | `state_machine.py` Approved→{Served,Cancelled}; `services/special_food.py` | test_domain, test_journeys | BW-MMS-14/15; actor unresolved (ISS-MMS-014) |
| MMS-UC-022 | Publish announcement (Caretaker/Warden); publication notification | services + notifications | `services/announcement.py`; notification | test_domain, test_journeys | No workflow mapping |
| MMS-UC-023 | View announcement history | selectors + api | `scoping.py` announcement history | test_domain, test_query_budgets | No workflow mapping |
| MMS-UC-024 | Warden view/search supervisory reports | selectors + api | `scoping.py` Warden supervisory | test_query_budgets | Not workflow-grounded |
| MMS-UC-025 | Caretaker generate operational reports | selectors + api | `scoping.py` Caretaker operational | test_query_budgets | Not workflow-grounded |
| MMS-UC-026 | Student view own request status/history | selectors + api | `scoping.py` own-requests-only (BR-MMS-042) | test_recruiter_isolation, test_query_budgets | Informational; not workflow-grounded |
| MMS-UC-027 | Event: activate approved deregistration next calendar day | schedule + services | `schedule.py` task; `services/deregistration.py` | test_schedule, test_journeys | Event-triggered; BW-MMS-03 |
| MMS-UC-028 | Event: default No for non-responding registered students at deadline | schedule + services | `schedule.py` task; `services/survey.py` | test_schedule, test_journeys | Event-triggered; BW-MMS-10 |
| MMS-UC-029 | Event: default-reject undecided special-food after decision period | schedule + services | `schedule.py` task; `services/special_food.py` | test_schedule, test_journeys | Event-triggered; BW-MMS-12; period institution-defined |
| MMS-UC-030 | Event: generate monthly bills calendar-month | schedule + services | `schedule.py` task; `services/billing.py` | test_schedule, test_journeys | Event-triggered; BW-MMS-16; day/time within month unspecified |
| MMS-UC-031 | Event: send vacation survey reminder | schedule + notifications | `schedule.py` task; notifications | test_schedule | Event-triggered; cadence unspecified |

### Business Rules (41 active; BR-MMS-037 retired — do not cite)

| Id | What it requires | Layer | Enforcement point | Tests | Notes |
|----|------------------|-------|-------------------|-------|-------|
| BR-MMS-001 | MMS limited to mess-management functions + explicit integrations/notifications | domain + api | `domain/rules.py` scope boundary | test_domain, test_privilege_escalation | Active |
| BR-MMS-002 | Use employee identities for Caretaker/Warden assignment only; do not own master data | services | `services/roles.py`; employee identity via session/contracts only | test_domain, test_privilege_escalation | Active |
| BR-MMS-003 | Exactly one active Caretaker at a time | models | partial unique index `mms_role_assignment_active_caretaker` | test_domain | Active |
| BR-MMS-004 | Exactly one active Warden at a time | models | partial unique index `mms_role_assignment_active_warden` | test_domain | Active |
| BR-MMS-005 | Mess Admin no operational data access | selectors + api | `scoping.py` empty scope for Mess Admin | test_recruiter_isolation, test_privilege_escalation | Active |
| BR-MMS-006 | Mid-cycle reassignment immediate from recorded time | services + schedule | `services/roles.py` reassignment; visibility handoff | test_domain, test_schedule | Active |
| BR-MMS-007 | Pending operational requests visible/actionable by new Caretaker after reassignment | selectors + services | `scoping.py` role-based request scope; `services/roles.py` handoff | test_domain | Active |
| BR-MMS-008 | Only active Caretaker opens registration window | services | `services/registration.py` actor check | test_domain, test_privilege_escalation | Active; BW-MMS-01/02 |
| BR-MMS-009 | Registration requests only while window open | domain + services | `domain/rules.py` window-open guard | test_domain | Active; BW-MMS-01/02 |
| BR-MMS-010 | Only active Caretaker approves/rejects registration+deregistration; Warden oversight-only | services + selectors | `services/registration.py`/`deregistration.py` actor check; Warden no decision endpoints | test_domain, test_privilege_escalation | Active; BW-MMS-01..04 |
| BR-MMS-011 | Warden views operational requests; no decide authority | selectors + api | `scoping.py` Warden read-only | test_recruiter_isolation | Active |
| BR-MMS-012 | Deregistration anytime | services | `services/deregistration.py` submit (no window) | test_domain | Active; BW-MMS-03/04 |
| BR-MMS-013 | Approved deregistration effective next calendar day | schedule + models | `schedule.py` UC-027; `effective_date` field | test_schedule, test_domain | Active; BW-MMS-03 |
| BR-MMS-014 | Weekly menu day-wise + meal-wise (breakfast/lunch/dinner) | models | `models/menu.py` day+meal structure; CheckConstraint | test_domain | Active |
| BR-MMS-015 | Menu-update notifications to students | services + notifications | `services/menu.py`; notification topic `menu.updated` | test_notification_worker | Active; not workflow-grounded |
| BR-MMS-016 | Monthly calendar billing cycle | schedule + services | `schedule.py` UC-030 monthly tick | test_schedule, test_domain | Active; BW-MMS-16 |
| BR-MMS-017 | Billing = daily-rate × served days + approved special meals − approved rebates | services + domain | `services/billing.py` computation; `domain/rules.py` | test_domain | Active; rates are external inputs |
| BR-MMS-018 | Caretaker review+finalize before bill publish | services + api | `services/billing.py` finalize/publish state machine | test_domain, test_privilege_escalation | Active; BW-MMS-16 |
| BR-MMS-019 | Rebate deductions only for approved rebates | services + domain | `services/billing.py`; `domain/rules.py` | test_domain | Active; BW-MMS-16/CW-MMS-03 |
| BR-MMS-020 | Store student feedback; visible to Caretaker+Warden; no resolution workflow | models + selectors | `models/feedback.py`; `scoping.py` Caretaker+Warden | test_domain, test_privilege_escalation | Active |
| BR-MMS-021 | Reject rebate duration < 3 days | domain | `domain/rules.py` min duration | test_domain | Active; BW-MMS-05/06/07 |
| BR-MMS-022 | Reject rebate not submitted >= 1 day before start date | domain | `domain/rules.py` lead-time | test_domain | Active; BW-MMS-05/06/07 |
| BR-MMS-023 | Prevent overlapping rebate requests | domain + models | `domain/rules.py` overlap check; partial unique index per student+date-range | test_domain | Active; BW-MMS-05/06/07 |
| BR-MMS-024 | Rebate requires reason; explanation when Other | domain + api serializer | `domain/rules.py`; serializer validation | test_domain | Active; BW-MMS-05/06/07 |
| BR-MMS-025 | Caretaker may modify rebate dates before approval only where external policy permits; approved dates used for billing | services + domain | `services/rebate.py` date modification (no invented range) | test_domain | Active; external-policy range undefined |
| BR-MMS-026 | Vacation surveys only to currently registered students | services + selectors | `services/survey.py` audience; `scoping.py` | test_domain, test_recruiter_isolation | Active; BW-MMS-08/09/10 |
| BR-MMS-027 | Default No for registered non-responders at deadline | schedule + services | `schedule.py` UC-028; `default_no` response | test_schedule, test_domain | Active; BW-MMS-10 |
| BR-MMS-028 | Special-food only >= 1 calendar day before requested date | domain + api | `domain/rules.py` lead-time; serializer | test_domain | Active; BW-MMS-11/12/13/14/15 |
| BR-MMS-029 | Auto-reject special-food if undecided within decision period | schedule + services | `schedule.py` UC-029; `decision_due_at` | test_schedule, test_domain | Active; period institution-defined (ISS-MMS-013) |
| BR-MMS-030 | Approved special-food chargeable; added to monthly bill | services + billing | `services/billing.py` charge line item | test_domain | Active; cancellation treatment unresolved (ISS-MMS-015) |
| BR-MMS-031 | Special-food states Requested/Approved/Rejected/Served/Cancelled; Served/Cancelled only after Approved | domain + models | `state_machine.py`; model CheckConstraint | test_domain | Active; BW-MMS-11..16; CW-MMS-05 |
| BR-MMS-032 | Only active Caretaker or Warden publish announcements | services + api | `services/announcement.py` actor check | test_domain, test_privilege_escalation | Active |
| BR-MMS-033 | Maintain announcement history; actors view per access rights | models + selectors | `models/announcement.py` history; `scoping.py` | test_domain, test_query_budgets | Active |
| BR-MMS-034 | Supervisory reports to Warden; operational reports to Caretaker | selectors | `scoping.py` role-based report scope | test_recruiter_isolation | Active; BW-MMS-N/A |
| BR-MMS-035 | Notifications only for listed PS events; external delivery outside MMS | services + notifications | `services/notifications.py` TOPICS allowlist; outbox | test_notification_worker | Active; all workflows |
| BR-MMS-036 | No institutional policy definition (rates, vacations, employee appointment); use only explicitly provided values | domain | `domain/rules.py` policy boundary | test_domain, test_privilege_escalation | Active |
| BR-MMS-038 | Students/Caretaker/Warden view weekly menu; Mess Admin visibility unresolved (PS conflict) | selectors + api | `scoping.py` menu scope; Mess Admin NOT granted menu until ruling | test_domain, test_privilege_escalation | **Needs Clarification** — blocked pending ruling |
| BR-MMS-039 | Only Caretaker add/delete/modify menu items | services + api | `services/menu.py` actor check | test_domain, test_privilege_escalation | Active |
| BR-MMS-040 | Students view only own bills + balances | selectors + api | `scoping.py` own billing scope | test_recruiter_isolation | Active |
| BR-MMS-041 | Vacation responses restricted to Yes/No | domain | `domain/rules.py` response options | test_domain | Active; BW-MMS-08/09 |
| BR-MMS-042 | Student views status/history only for own submitted requests | selectors + api | `scoping.py` own-requests-only (404 for foreign) | test_recruiter_isolation | Active; all workflows |

**Retired (excluded):** BR-MMS-037 (retired; "system is not a primary actor" modeling convention), MMS-FR-102 (retired).

### Workflows (21 — none retired)

| Id | What it requires | Layer | Enforcement point | Tests | Notes |
|----|------------------|-------|-------------------|-------|-------|
| BW-MMS-01 | Registration — Approved: open window → student submit → caretaker approve | domain + services | `state_machine.py` registration transitions | test_domain, test_state_machine, test_journeys | Basis |
| BW-MMS-02 | Registration — Rejected: open window → submit → caretaker reject | domain + services | `state_machine.py` registration reject transition | test_domain, test_state_machine, test_journeys | Basis |
| CW-MMS-01 | Registration lifecycle composite (approve + reject) | domain + services | `state_machine.py` both outcomes | test_domain, test_state_machine | Composite; constituents BW-MMS-01/02 |
| BW-MMS-03 | Deregistration — Approved: submit → caretaker approve → system next-day effective | domain + services + schedule | `state_machine.py`; `schedule.py` UC-027 | test_domain, test_schedule, test_state_machine | Basis |
| BW-MMS-04 | Deregistration — Rejected: submit → caretaker reject | domain + services | `state_machine.py` deregistration reject | test_domain, test_state_machine, test_journeys | Basis |
| CW-MMS-02 | Deregistration lifecycle composite | domain + services + schedule | `state_machine.py`; `schedule.py` UC-027 | test_domain, test_schedule, test_state_machine | Composite |
| BW-MMS-05 | Rebate — Approved as submitted | domain + services | `state_machine.py` rebate approve | test_domain, test_state_machine, test_journeys | Basis |
| BW-MMS-06 | Rebate — Dates modified then approved | domain + services | `state_machine.py` rebate approve with modified dates | test_domain, test_state_machine | Basis |
| BW-MMS-07 | Rebate — Rejected | domain + services | `state_machine.py` rebate reject | test_domain, test_state_machine, test_journeys | Basis |
| CW-MMS-03 | Rebate lifecycle composite | domain + services | `state_machine.py` three outcomes | test_domain, test_state_machine | Composite |
| BW-MMS-08 | Vacation — Yes response | domain + services | `domain/rules.py` Yes/No; `services/survey.py` | test_domain, test_journeys | Basis |
| BW-MMS-09 | Vacation — No response | domain + services | `domain/rules.py` Yes/No; `services/survey.py` | test_domain, test_journeys | Basis |
| BW-MMS-10 | Vacation — Default No | schedule + services | `schedule.py` UC-028 | test_schedule, test_domain | Basis |
| CW-MMS-04 | Vacation response lifecycle composite | domain + services + schedule | `domain/rules.py`; `schedule.py` UC-028 | test_domain, test_schedule, test_state_machine | Composite |
| BW-MMS-11 | Special Food — Rejected by Caretaker | domain + services + api | `state_machine.py`; `services/special_food.py` decide | test_domain, test_state_machine, test_privilege_escalation, test_journeys | Basis |
| BW-MMS-12 | Special Food — Default Rejected | schedule + services | `schedule.py` UC-029 | test_schedule, test_domain | Basis |
| BW-MMS-13 | Special Food — Approved, Awaiting Fulfillment | domain + services | `state_machine.py` Requested→Approved | test_domain, test_state_machine, test_journeys | Basis |
| BW-MMS-14 | Special Food — Served | domain + services + notifications | `state_machine.py` Approved→Served; notification | test_domain, test_state_machine | Basis |
| BW-MMS-15 | Special Food — Cancelled | domain + services + notifications | `state_machine.py` Approved→Cancelled; notification | test_domain, test_state_machine | Basis |
| CW-MMS-05 | Special food lifecycle composite | domain + services + schedule | `state_machine.py` all outcomes; `schedule.py` UC-029 | test_domain, test_schedule, test_state_machine | Composite |
| BW-MMS-16 | Monthly Billing — Generated to Published | schedule + services + api | `schedule.py` UC-030 generate; `services/billing.py` finalize/publish | test_schedule, test_domain, test_journeys | Basis |

---

## Step 3.2 (b) — Domain model

### Entities, fields, invariants

All models in `modules/mms/models/`, one file per aggregate. No cross-module foreign keys; person references are plain `user_id` integers (`UserScopedModel`). `created_at`/`updated_at` via `TimeStampedModel`. All `Meta.db_table` prefixed `mms_`. Every index named in `Meta.indexes` and matched to a real query shape. Database constraints for anything that must hold under concurrency.

**1. `mms_role_assignment`** (role management, BR-MMS-002/003/004/006/007; UC-001)
- `id` PK, `designation` (`caretaker` \| `warden`), `employee_user_id` int (indexed, not FK), `effective_from` datetime, `effective_until` datetime nullable, `is_active` bool, `assigned_by_user_id` int, `created_at`, `updated_at`
- Invariants: exactly one active caretaker (partial unique index on `(designation)` where `designation='caretaker'` AND `is_active`); exactly one active warden (partial unique index where `designation='warden'` AND `is_active`); `effective_until` NULL or > `effective_from`; mid-cycle reassignment sets new row active and previous row `effective_until` = reassignment time.

**2. `mms_registration_window`** (registration; BR-MMS-008/009; UC-002)
- `id` PK, `cycle_or_period` text, `opens_at` datetime, `closes_at` datetime, `is_open` bool, `opened_by_user_id` int, `created_at`, `updated_at`
- Invariant: window open check `opens_at <= now <= closes_at` enforced in domain; only caretaker may set `is_open=True`.

**3. `mms_registration`** (registration lifecycle; BR-MMS-009/010/012; UC-003/004; BW-MMS-01/02)
- `id` PK, `student_user_id` int (indexed), `status` (`pending` \| `approved` \| `rejected`), `submitted_at` datetime, `decided_at` datetime nullable, `decided_by_user_id` int nullable, `created_at`, `updated_at`
- Invariant: one pending registration per student per open window (partial unique index where status='pending'); decision only from `pending`; `decided_at`/`decided_by_user_id` both set or both null (CheckConstraint).

**4. `mms_deregistration`** (deregistration lifecycle; BR-MMS-012/013; UC-005/006/027; BW-MMS-03/04)
- `id` PK, `student_user_id` int (indexed), `status` (`pending` \| `approved_awaiting_effective_date` \| `rejected`), `effective_date` date nullable, `submitted_at`, `decided_at`, `decided_by_user_id`, `created_at`, `updated_at`
- Invariant: one pending deregistration per student; approved → `effective_date` = next calendar day (set by UC-027 scheduled task); decision only from `pending`.

**5. `mms_menu_item`** (menu; BR-MMS-014/015/038/039; UC-008/009)
- `id` PK, `day` date (indexed), `meal` (`breakfast` \| `lunch` \| `dinner`), `item` text, `published_at` datetime nullable, `created_by_user_id` int, `created_at`, `updated_at`
- Invariant: day-wise + meal-wise structure (CheckConstraint on `meal` enum); only caretaker add/delete/modify; Mess Admin visibility blocked until BR-MMS-038 ruling.

**6. `mms_special_food_request`** (special food; BR-MMS-028/029/030/031; UC-019/020/021/029; BW-MMS-11..15)
- `id` PK, `student_user_id` int (indexed), `reason` text not blank, `requested_date` date (indexed), `status` (`requested` \| `approved` \| `rejected` \| `served` \| `cancelled`) default `requested`, `decision_due_at` datetime (indexed), `decided_at` datetime nullable, `decided_by_user_id` int nullable, `decision_note` text blank, `created_at`, `updated_at`
- Invariants: `requested_date >= submitted local date + 1 day` (domain; stored `submitted_on` date for constraint); `decision_due_at = submitted_at + decision_period` from policy; status transitions only via state machine (Requested→{Approved,Rejected}; Approved→{Served,Cancelled}); terminal states Rejected/Served/Cancelled have no outgoing transitions; `decided_at`/`decided_by_user_id` both set or both null; `status` in terminal ⇒ `decided_at` not null (CheckConstraint); one decision per request (partial unique index on `(student_user_id)`? no — per request: unique `(id)` where status in terminal is implicit since one row per request; enforce no second decision via state machine refusal + `select_for_update`).

**7. `mms_special_food_transition`** (audit trail; BR-MMS-031; UC-019/020/021/029)
- `id` PK, `request_id` int (indexed, not FK to another module — same module FK allowed), `from_status`, `to_status`, `actor_user_id` int nullable (system for UC-029), `occurred_at` datetime, `note` text blank
- Invariant: append-only audit row per transition; unique `(request_id, to_status)` to prevent duplicate terminal decision (partial unique index where `to_status` in terminal states).

**8. `mms_rebate_request`** (rebate; BR-MMS-021..025; UC-014/015; BW-MMS-05/06/07)
- `id` PK, `student_user_id` int (indexed), `reason` enum (`medical` \| `institute_leave` \| `family_function` \| `other`), `explanation` text blank (required if `other`), `start_date` date, `end_date` date, `status` (`pending` \| `approved` \| `rejected`), `approved_start_date` date nullable, `approved_end_date` date nullable, `decided_at`, `decided_by_user_id`, `created_at`, `updated_at`
- Invariants: `end_date - start_date >= 3 days`; `submitted_at local date + 1 day <= start_date`; no overlapping approved/pending date ranges for same student (partial unique index with exclusion on date overlap — PostgreSQL `EXCLUDE` using `range` type or domain-level check with `select_for_update`); decision only from `pending`; date modification only before approval; approved dates drive billing.

**9. `mms_vacation_survey`** (vacation; BR-MMS-026/027; UC-016/028; BW-MMS-08/09/10)
- `id` PK, `vacation` text, `response_deadline` datetime (indexed), `is_open` bool, `created_by_user_id` int (caretaker), `created_at`, `updated_at`
- Invariant: deadline in future when created; only caretaker creates.

**10. `mms_vacation_response`** (vacation response; BR-MMS-027/041; UC-017/028; BW-MMS-08/09/10)
- `id` PK, `survey_id` int (indexed), `student_user_id` int (indexed), `response` (`yes` \| `no` \| `default_no`), `responded_at` datetime nullable
- Invariants: one response per student per survey (unique `(survey_id, student_user_id)`); `response` in yes/no/default_no; explicit yes/no set `responded_at`; default_no set by UC-028 scheduled task with `responded_at` = deadline; students without response at deadline get default_no row.

**11. `mms_announcement`** (announcements; BR-MMS-032/033; UC-022/023)
- `id` PK, `title` text, `body` text, `publisher_user_id` int (caretaker/warden), `published_at` datetime, `created_at`, `updated_at`
- Invariant: publisher must be caretaker or warden (domain check); history is append-only (no delete endpoint).

**12. `mms_feedback`** (feedback; BR-MMS-020; UC-012/013)
- `id` PK, `student_user_id` int (indexed), `text` text not blank, `created_at`, `updated_at`
- Invariant: text not empty; viewable by caretaker + warden only; no resolution workflow fields.

**13. `mms_monthly_bill`** (billing; BR-MMS-016/017/018/019/030; UC-010/011/030; BW-MMS-16)
- `id` PK, `student_user_id` int (indexed), `month` date (first of month, indexed), `state` (`generated` \| `finalized` \| `published`), `served_day_charges` decimal, `special_meal_charges` decimal, `rebate_deductions` decimal, `total` decimal, `generated_at` datetime, `finalized_at` datetime nullable, `published_at` datetime nullable, `finalized_by_user_id` int nullable, `created_at`, `updated_at`
- Invariants: one bill per student per month (unique `(student_user_id, month)`); state progression generated→finalized→published only; publish requires finalized; students view own published bills.

**14. `mms_special_food_charge`** (billing link; BR-MMS-030; UC-020/030; BW-MMS-13/14/15/CW-MMS-05)
- `id` PK, `request_id` int (indexed), `student_user_id` int (indexed), `month` date, `amount` decimal, `created_at`
- Invariant: created only when special-food request approved; cancellation-billing treatment unresolved (ISS-MMS-015) — no reversal logic implemented; charge not removed on cancel.

**15. `mms_notification_outbox`** (notifications; BR-MMS-035/022; CFR-MMS-015/016/017/018/022)
- `id` PK, `topic` text (indexed, allowlisted), `dedupe_key` text unique, `recipient_user_id` int nullable (indexed), `recipient_email` text blank, `subject` text, `body` text, `payload` JSON default `{}`, `status` (`pending` \| `sending` \| `sent` \| `failed` \| `suppressed`), `attempts` int default 0, `last_error` text blank, `sent_at` datetime nullable, `claimed_at` datetime nullable, `created_at`, `updated_at`
- Indexes: `(status, created_at)`, `(recipient_user_id, -created_at)`. Delivery by Celery task; external email infra outside MMS (console backend default).

---

## Step 3.3 (c) — State machines

Declarative transition tables in `modules/mms/domain/state_machine.py` (pure Python, no Django/DRF/Celery). Single `resolve(frm, to, actor_kind)` lookup; illegal transitions raise `InvalidTransition` (inexpressible, not merely rejected). Actor kinds: `student`, `caretaker`, `warden`, `mess_admin`, `system`.

### Registration (BW-MMS-01/02, CW-MMS-01; BR-MMS-008/009/010)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| window_closed | window_open | `mms.registration.window.manage` | {caretaker} | (window_info_complete) |
| window_open | registration_pending | `mms.registration.create` | {student} | (window_open) |
| registration_pending | registration_approved | `mms.registration.review` | {caretaker} | () |
| registration_pending | registration_rejected | `mms.registration.review` | {caretaker} | () |

### Deregistration (BW-MMS-03/04, CW-MMS-02; BR-MMS-012/013)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| student_registered | deregistration_pending | `mms.deregistration.create` | {student} | (student_registered) |
| deregistration_pending | deregistration_approved_awaiting_date | `mms.deregistration.review` | {caretaker} | () |
| deregistration_pending | deregistration_rejected | `mms.deregistration.review` | {caretaker} | () |
| deregistration_approved_awaiting_date | student_deregistered | `mms.deregistration.activate` | {system} | (next_calendar_day) |

### Rebate (BW-MMS-05/06/07, CW-MMS-03; BR-MMS-021..025)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| no_rebate | rebate_pending | `mms.rebate.create` | {student} | (reason_complete, duration>=3, lead_time>=1day, no_overlap) |
| rebate_pending | rebate_approved | `mms.rebate.review` | {caretaker} | () |
| rebate_pending | rebate_approved_modified_dates | `mms.rebate.review` | {caretaker} | (dates_modified_permitted_by_external_policy) |
| rebate_pending | rebate_rejected | `mms.rebate.review` | {caretaker} | () |

### Vacation response (BW-MMS-08/09/10, CW-MMS-04; BR-MMS-026/027/041)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| survey_not_created | survey_open | `mms.survey.create` | {caretaker} | (vacation_identified, deadline_set, registered_students_only) |
| survey_open | response_yes | `mms.survey.respond` | {student} | (registered, open, before_deadline) |
| survey_open | response_no | `mms.survey.respond` | {student} | (registered, open, before_deadline) |
| survey_open | response_default_no | `mms.survey.default_no` | {system} | (deadline_reached, no_explicit_response) |

### Special food (BW-MMS-11..15, CW-MMS-05; BR-MMS-028/029/030/031)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| no_request | requested | `mms.special_food.create` | {student} | (lead_time>=1_calendar_day) |
| requested | rejected | `mms.special_food.review` | {caretaker} | (within_decision_period) |
| requested | rejected_default | `mms.special_food.default_reject` | {system} | (decision_period_expired, still_requested) |
| requested | approved | `mms.special_food.review` | {caretaker} | (within_decision_period) |
| approved | served | `mms.special_food.fulfill` | {caretaker} | (current_state==approved) |
| approved | cancelled | `mms.special_food.fulfill` | {caretaker} | (current_state==approved) |

Terminal states: rejected, rejected_default, served, cancelled. No transitions out of terminal.

### Monthly billing (BW-MMS-16; BR-MMS-016/017/018/019/030)
| frm | to | permission | actors | guards |
|-----|----|------------|--------|--------|
| bill_not_generated | bill_generated | `mms.billing.generate` | {system} | (calendar_month_event, billing_inputs_available) |
| bill_generated | bill_published | `mms.billing.publish` | {caretaker} | (reviewed_and_finalized) |

### Role management (UC-001; BR-MMS-002..007)
Not workflow-grounded (isolated service). Implemented as service methods with DB cardinality constraints, not a state machine table.

---

## Step 3.4 (d) — Permission list

Exact `registry.py` content (designation keys = exact `globals_designation` spellings, UNCONFIRMED; proposed values shown).

```python
MODULE = {
    "code": "mms",
    "label": "Mess Management System",
    "icon": "FaCircle",
    "base_path": "/mms",
    "nav_section": "MMS",
    "sort_order": 20,
    "status": "planned",
}
```

`PERMISSIONS` (`mms.<singular_noun>.<verb>`, verb from closed list):
- `mms.role.assign` — Mess Admin assign/reassign Caretaker/Warden
- `mms.registration.window.manage` — Caretaker open registration window
- `mms.registration.create` — Student submit registration
- `mms.registration.review` — Caretaker approve/reject registration
- `mms.deregistration.create` — Student submit deregistration
- `mms.deregistration.review` — Caretaker approve/reject deregistration
- `mms.menu.view` — Student/Caretaker/Warden view menu
- `mms.menu.manage` — Caretaker add/delete/modify menu items
- `mms.billing.view_self` — Student view own bills/balances
- `mms.billing.review` — Caretaker review monthly bills
- `mms.billing.finalize` — Caretaker finalize monthly bills
- `mms.billing.publish` — Caretaker publish monthly bills
- `mms.rebate.create` — Student submit rebate
- `mms.rebate.review` — Caretaker approve/reject rebate
- `mms.survey.create` — Caretaker create vacation survey
- `mms.survey.respond` — Student respond to vacation survey
- `mms.survey.view_summary` — Caretaker view vacation response summary
- `mms.special_food.create` — Student submit special-food request
- `mms.special_food.review` — Caretaker approve/reject special-food
- `mms.special_food.fulfill` — Caretaker record Served/Cancelled
- `mms.announcement.publish` — Caretaker/Warden publish announcement
- `mms.announcement.view` — MMS actors view announcement history
- `mms.feedback.create` — Student submit feedback
- `mms.feedback.view` — Caretaker/Warden view feedback
- `mms.report.supervisory` — Warden view supervisory reports
- `mms.report.operational` — Caretaker generate operational reports
- `mms.request.view_self` — Student view own request status/history

`SYSTEM_PERMISSIONS` (no designation holds; service/scheduled only):
- `mms.registration.activate` (UC-027), `mms.survey.default_no` (UC-028), `mms.special_food.default_reject` (UC-029), `mms.billing.generate` (UC-030), `mms.survey.reminder` (UC-031), `mms.notification.deliver` (outbox drain)

`SCOPE_PERMISSIONS` (unenforced; widens queryset): none beyond per-endpoint scoping in `selectors/scoping.py`.

`ROLE_GRANTS` (keyed by exact `globals_designation` spellings — UNCONFIRMED):
```python
_STUDENT = [
    "mms.registration.create",
    "mms.deregistration.create",
    "mms.menu.view",
    "mms.billing.view_self",
    "mms.rebate.create",
    "mms.survey.respond",
    "mms.special_food.create",
    "mms.announcement.view",
    "mms.feedback.create",
    "mms.request.view_self",
]
_CARETAKER = [
    "mms.registration.window.manage",
    "mms.registration.review",
    "mms.deregistration.review",
    "mms.menu.view",
    "mms.menu.manage",
    "mms.billing.review",
    "mms.billing.finalize",
    "mms.billing.publish",
    "mms.rebate.review",
    "mms.survey.create",
    "mms.survey.view_summary",
    "mms.special_food.review",
    "mms.special_food.fulfill",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.operational",
    "mms.request.view_self",
]
_WARDEN = [
    "mms.menu.view",
    "mms.billing.view_self",
    "mms.survey.view_summary",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.supervisory",
    "mms.request.view_self",
]
_MESS_ADMIN = [
    "mms.role.assign",
]
ROLE_GRANTS = {
    "student": _STUDENT,
    "Mess Caretaker": _CARETAKER,
    "Mess Warden": _WARDEN,
    "Mess Admin": _MESS_ADMIN,
}
```

`student` granted by definition (basic kind). `faculty`/`staff` get nothing unless holding a designation above. A role with no screens is not granted (no "look" grants). Every permission declared is either granted or in `SYSTEM_PERMISSIONS` (enforced by `permission_manifest --check`).

---

## Step 3.5 (e) — Endpoint list

Base path `/api/v1/mms/`. Two gates on every endpoint: `HasModuleGrant("mms")` then `HasPermission(<code>)`. Out-of-scope rows → 404. All writes carry `throttle_scope`. All serializers explicit `fields`; server-owned fields read-only. `@extend_schema` with request/response examples on every endpoint.

| Method | Path | Gates | Returns | Rule ids |
|--------|------|-------|---------|----------|
| POST | /special-food-requests | module + `mms.special_food.create` | SpecialFoodRequest (201) | BR-MMS-028, BR-MMS-035, CFR-MMS-015 |
| GET | /special-food-requests | module + `mms.special_food.create`/`.review`/`.view_self` | Page (student own; caretaker all) | BR-MMS-042, CFR-MMS-015/016/017 |
| GET | /special-food-requests/{id} | module + same | SpecialFoodRequest detail (404 foreign) | BR-MMS-042 |
| POST | /special-food-requests/{id}/decision | module + `mms.special_food.review` | updated request | BR-MMS-029/031/035, CFR-MMS-016 |
| POST | /rebate-requests | module + `mms.rebate.create` | RebateRequest (201) | BR-MMS-021..025, CFR-MMS-011 |
| GET | /rebate-requests | module + `.create`/`.review`/`.view_self` | Page | CFR-MMS-011/012 |
| POST | /rebate-requests/{id}/decision | module + `mms.rebate.review` | updated rebate | BR-MMS-025, CFR-MMS-012 |
| POST | /registration-requests | module + `mms.registration.create` | Registration (201) | BR-MMS-008/009, CFR-MMS-004 |
| GET | /registration-requests | module + `.review`/`.view_self` | Page | BR-MMS-042 |
| POST | /registration-requests/{id}/decision | module + `mms.registration.review` | updated | BR-MMS-010, CFR-MMS-004 |
| POST | /deregistration-requests | module + `mms.deregistration.create` | Deregistration (201) | BR-MMS-012, CFR-MMS-005 |
| POST | /deregistration-requests/{id}/decision | module + `mms.deregistration.review` | updated | BR-MMS-010/013, CFR-MMS-005 |
| GET | /menu | module + `mms.menu.view` | day-wise+meal-wise items | BR-MMS-014, CFR-MMS-008 |
| POST/PUT/DELETE | /menu/items | module + `mms.menu.manage` | item | BR-MMS-039, CFR-MMS-008 |
| GET | /bills | module + `mms.billing.view_self` | Page own bills | BR-MMS-040, CFR-MMS-009 |
| POST | /bills/generate | module + system perm `mms.billing.generate` | bills generated | BR-MMS-016/017, CFR-MMS-009, UC-030 |
| POST | /bills/{id}/finalize | module + `mms.billing.finalize` | bill finalized | BR-MMS-018, CFR-MMS-009, UC-010 |
| POST | /bills/{id}/publish | module + `mms.billing.publish` | bill published | BR-MMS-018, CFR-MMS-009, UC-010 |
| POST | /feedback | module + `mms.feedback.create` | feedback (201) | BR-MMS-020, CFR-MMS-010 |
| GET | /feedback | module + `mms.feedback.view` | Page caretaker+warden | BR-MMS-020 |
| POST | /surveys | module + `mms.survey.create` | survey (201) | BR-MMS-026, CFR-MMS-013 |
| POST | /survey-responses | module + `mms.survey.respond` | response | BR-MMS-027/041, CFR-MMS-014 |
| GET | /survey-summary | module + `mms.survey.view_summary` | summary | BR-MMS-026, CFR-MMS-014 |
| POST | /announcements | module + `mms.announcement.publish` | announcement (201) | BR-MMS-032/035, CFR-MMS-018 |
| GET | /announcements/history | module + `mms.announcement.view` | Page | BR-MMS-033, CFR-MMS-018 |
| GET | /reports/supervisory | module + `mms.report.supervisory` | report data | BR-MMS-034, CFR-MMS-019 |
| GET | /reports/operational | module + `mms.report.operational` | report data | BR-MMS-034, CFR-MMS-020 |
| POST | /roles/assign | module + `mms.role.assign` | assignment recorded | BR-MMS-002..007, CFR-MMS-002 |
| GET | /roles | module + `mms.role.assign` | current caretaker/warden | CFR-MMS-002 |
| GET | /requests | module + `mms.request.view_self` | own status/history | BR-MMS-042, CFR-MMS-007, UC-026 |

Client routes (module-only sidebar entry to hand over — `id`, `label`, `icon`, `to`, `section`; icon must be a Phosphor name; expected to draw a circle in this repo's client):
- `mms.special-food-request`, label "Special Food Request", to `/mms/special-food`, permission `mms.special_food.create` (student)
- `mms.my-requests`, label "My Requests", to `/mms/requests`, permission `mms.request.view_self` (student)
- `mms.my-bills`, label "My Bills", to `/mms/bills`, permission `mms.billing.view_self` (student)
- `mms.menu`, label "Weekly Menu", to `/mms/menu`, permission `mms.menu.view` (student/caretaker/warden)
- `mms.feedback`, label "Feedback", to `/mms/feedback`, permission `mms.feedback.create` (student)
- `mms.registration-approvals`, label "Registration Approvals", to `/mms/registration-approvals`, permission `mms.registration.review` (caretaker)
- `mms.deregistration-approvals`, label "Deregistration Approvals", to `/mms/deregistration-approvals`, permission `mms.deregistration.review` (caretaker)
- `mms.rebate-approvals`, label "Rebate Approvals", to `/mms/rebate-approvals`, permission `mms.rebate.review` (caretaker)
- `mms.special-food-approvals`, label "Special Food Approvals", to `/mms/special-food-approvals`, permission `mms.special_food.review` (caretaker)
- `mms.menu-management`, label "Menu Management", to `/mms/menu-management`, permission `mms.menu.manage` (caretaker)
- `mms.billing-review`, label "Billing Review", to `/mms/billing-review`, permission `mms.billing.review` (caretaker)
- `mms.survey-management`, label "Vacation Survey", to `/mms/survey`, permission `mms.survey.create` (caretaker)
- `mms.survey-summary`, label "Survey Summary", to `/mms/survey-summary`, permission `mms.survey.view_summary` (caretaker)
- `mms.announcements`, label "Announcements", to `/mms/announcements`, permission `mms.announcement.publish` (caretaker/warden)
- `mms.announcement-history`, label "Announcement History", to `/mms/announcements/history`, permission `mms.announcement.view` (all MMS actors)
- `mms.feedback-review`, label "Feedback Review", to `/mms/feedback-review`, permission `mms.feedback.view` (caretaker/warden)
- `mms.supervisory-reports`, label "Supervisory Reports", to `/mms/reports/supervisory`, permission `mms.report.supervisory` (warden)
- `mms.operational-reports`, label "Operational Reports", to `/mms/reports/operational`, permission `mms.report.operational` (caretaker)
- `mms.role-assignment`, label "Role Assignment", to `/mms/role-assignment`, permission `mms.role.assign` (Mess Admin)

Every route guarded with `RequirePermission` matching its nav item's `required_permission`. Detail opens in drawer/modal on list page (no standalone detail routes). Mess Admin gets role-assignment only; no operational-data routes (BR-MMS-005). Mess Admin menu view NOT granted until BR-MMS-038 ruling.

---

## Step 3.6 (f) — Contracts

`modules/mms/contracts.py` — plural getters only, read-only, no cross-module internals (only `modules.directory.contracts`):

- `get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]` — names/kind/emails for notification recipients and display (via `modules.directory.contracts.get_users`).
- `get_special_food_charges(student_ids, month) -> dict[int, list[SpecialFoodChargeDTO]]` — for billing display.
- `get_menu_for_period(start, end) -> dict[date, dict[meal, list[MenuItemDTO]]]` — menu read.
- `get_vacation_survey_summary(survey_ids) -> dict[int, SurveySummaryDTO]` — yes/no/default counts.

MMS needs nothing added to other modules' contracts. No `IamClient` method additions needed (session principal + directory `get_users` suffice), so `conftest.py` change is not required. No `fusionlab` connection. No second database alias. MMS reads its own tables only.

---

## Step 3.7 (g) — Scheduled work

Clock needed (Step 2.6): event-triggered UCs. `modules/mms/schedule.py` exports `BEAT_SCHEDULE` + `TASK_ROUTES`; merged into `config/celery.py` (pre-approved). All tasks idempotent, `acks_late`, `expires` < interval, run manually once verified.

| Beat entry | Task | Schedule | Expires | Queue | What breaks if not run |
|------------|------|----------|---------|-------|------------------------|
| mms.deliver-notifications | `mms.deliver_notifications` | 60s | 55 | notifications | Notification backlog; students never receive submission/decision emails |
| mms.default-reject-special-food | `mms.default_reject_special_food` | policy-driven (decision_period) | policy-derived | default | Undecided special-food requests never auto-rejected (BR-MMS-029, UC-029) |
| mms.default-vacation-response | `mms.default_vacation_response` | per-survey deadline polling (e.g. 5 min) | 240 | default | Non-responding students never get default No (BR-MMS-027, UC-028) |
| mms.activate-deregistration | `mms.activate_deregistration` | daily (next calendar day) | 3600 | default | Approved deregistrations never take effect (BR-MMS-013, UC-027) |
| mms.generate-monthly-bills | `mms.generate_monthly_bills` | monthly calendar event (day/time unspecified — model as monthly tick) | 3600 | billing | Monthly bills never generated (BR-MMS-016, UC-030, BW-MMS-16) |
| mms.send-vacation-reminder | `mms.send_vacation_reminder` | institution-defined reminder event (cadence unspecified — no schedule invented) | — | default | Reminder emails never sent (UC-031; cadence blocked pending ruling) |

Decision period for special food: loaded from an effective-dated `mms_special_food_policy` table (single row, `decision_period_hours`); `readiness()` reports missing if no row. Not seeded; do not invent 12h.

---

## Step 3.8 (h) — Open questions (blocked pending authoritative ruling)

Each question: spec reference, repository support, recommendation, alternatives, approver.

| # | Question | Spec ref | Repo supports | Recommended solution | Alternatives/consequences | Approver |
|---|----------|----------|---------------|----------------------|-------------------------|----------|
| 1 | `module_code` exact value | new-module-prompt §0.1 | None (no MMS in repo) | `mms` (proposed) | Any other value changes URL/permission prefix/registry | Student 2 / assignment |
| 2 | `NN` docs folder number | student-assignment-guide §4 | Existing docs 00–08 | `09` (proposed, next free) | Any assigned number | Mentor |
| 3 | `ID_PREFIX` exact value | new-module-prompt §0.1 | Spec IDs use mixed forms | `MMS` (proposed) | Any other prefix | Student 2 / assignment |
| 4 | `Mess Caretaker` / `Mess Warden` / `Mess Admin` `globals_designation` spellings | PS §3.2; rbac-model.md | Only `mess_committee` example | Use PS labels exactly (proposed) | Must match ERP/fixture or grants silently reach nobody | ERP / fixture check |
| 5 | Special-food decision period value | PS §3.3.7; ISS-MMS-013 | None | Effective-dated policy row; `readiness()` reports missing until seeded | Hard-code 12h = inventing (forbidden); no policy = module unusable | Institute / assignment |
| 6 | Caretaker rejection reason required? | UC-020; CFR-MMS-016 | None | Optional `decision_note` (spec does not require) | Required = inventing a rule | Student 2 |
| 7 | Caretaker permission scope — all requests or role-scoped? | UC-020; BR-MMS-010 | None | Caretaker sees all pending special-food/rebate/registration/deregistration requests (role-scoped to active caretaker) | Personal scope only = breaks queue workflow | Student 2 |
| 8 | Notification delivery approach | BR-MMS-035; PS §3.3.10 | Console email backend; placement outbox pattern | MMS-owned `NotificationOutbox` + Celery `deliver_notifications` | Reuse placement outbox = forbidden (import-linter); direct `send_mail` in request cycle = breaks transactional guarantee | Student 2 |
| 9 | Duplicate/resubmission rule (re-submit special food after rejection?) | CW-MMS-05 | None | No rule; do not implement resubmission restrictions | Any limit = inventing | Student 2 |
| 10 | Mess Admin weekly-menu visibility (BR-MMS-038 contradiction) | PS §3.2.1 vs §3.3.2; UC-009 | None | Do NOT grant Mess Admin menu access until ruling | Granting = may violate "no operational data" (BR-MMS-005); not granting = may violate PS §3.3.2 | Mentor ruling |
| 11 | Cancellation billing treatment after special-food Cancelled | BR-MMS-030; CFR-MMS-017; ISS-MMS-015 | None | No charge reversal; charge stands on approval | Reversal = inventing unresolved policy | Mentor ruling |
| 12 | Served/Cancelled recording actor | BR-MMS-031; UC-021; ISS-MMS-014 | None | Caretaker (per UC-021 primary actor) | System/other = contradicts UC | Mentor confirmation |
| 13 | Rebate date-modification permitted range | BR-MMS-025; UC-015 | None | Caretaker modifies dates; no invented range/limits | Any range = inventing external policy | Institute policy |
| 14 | Vacation reminder cadence | UC-031; AFR-MMS-069; ISS-MMS-019 | None | Model reminder task; no schedule invented; `readiness()`/config supplies cadence | Any cadence = inventing | Institute policy |
| 15 | Monthly bill generation day/time within calendar month | UC-030; BW-MMS-16 | None | Monthly tick; configurable day | Any fixed day = inventing | Institute policy |
| 16 | Vacation survey audience = "currently registered" — registration source? | BR-MMS-026; UC-016 | `mms_registration` approved state | Use MMS registration approved status as "registered" | Cross-module registration data = none available | Student 2 |

All unresolved requirements remain in the traceability matrix (marked Blocked/Needs Clarification) and are NOT removed.

---

## Module purpose, boundaries and actors

**Purpose (PS §3.1):** Digitize student mess services — registration, menus, billing, rebates, vacation surveys, special food, announcements, feedback, reporting, and system-generated email notifications — for authorized institute employees and students.

**Boundaries (PS §3.4, BR-MMS-001/036):** MMS does NOT own employee master data, payment collection, accounting, payroll, procurement, inventory, or institutional policy definition (rates, vacations, eligibility, approval authority). MMS does not treat the system as a primary actor; system behavior = validation, record maintenance, status changes, billing adjustment, history logging, report generation, notification triggers. External email delivery outside MMS (BR-MMS-035, CFR-MMS-022).

**Actors (PS §3.2):** Mess Admin (role assignment only, no operational data), Student (consume services, submit/view requests), Mess Caretaker (day-to-day operations, approvals), Mess Warden (oversight only, no decide authority). Exactly one active Caretaker and one active Warden at a time (BR-MMS-003/004).

---

## Database models, fields, constraints and indexes

(See Step 3.2 entity list above.) Key database-level invariants:

- `mms_role_assignment`: partial unique indexes for exactly-one-active-caretaker and exactly-one-active-warden.
- `mms_registration` / `mms_deregistration`: partial unique index one-pending-per-student; CheckConstraint decided_at/decided_by paired.
- `mms_special_food_request`: CheckConstraint status in terminal ⇒ decided_at not null; CheckConstraint status in {requested} ⇒ decided_at null; `decision_due_at` indexed for the default-reject sweep.
- `mms_rebate_request`: domain-level overlap check (PostgreSQL `EXCLUDE` with range types preferred if available, otherwise `select_for_update` + domain rule); CheckConstraint end_date >= start_date + 3 days.
- `mms_vacation_response`: unique `(survey_id, student_user_id)`.
- `mms_monthly_bill`: unique `(student_user_id, month)`.
- `mms_notification_outbox`: unique `dedupe_key`; indexes `(status, created_at)` and `(recipient_user_id, -created_at)`.
- `mms_special_food_transition`: partial unique index `(request_id)` where `to_status` in terminal states (one decision per request).

Every index named in `Meta.indexes` and tied to a real query filter/ordering (per `ops/checks` and module DoD).

---

## Business-rule enforcement points

| BR | Enforcement point |
|----|-------------------|
| BR-MMS-001/036 | `domain/rules.py` scope/policy boundary; every view |
| BR-MMS-002 | `services/roles.py` (employee identity via session/contracts only) |
| BR-MMS-003/004 | `mms_role_assignment` partial unique indexes |
| BR-MMS-005 | `scoping.py` — Mess Admin empty scope → 404 |
| BR-MMS-006/007 | `services/roles.py` reassignment; handoff in selectors |
| BR-MMS-008/009 | `services/registration.py`; `domain/rules.py` window-open guard |
| BR-MMS-010 | `services/registration.py`/`deregistration.py` actor checks; Warden no decision endpoints |
| BR-MMS-011 | `scoping.py` Warden read-only |
| BR-MMS-012 | `services/deregistration.py` (no window) |
| BR-MMS-013 | `schedule.py` UC-027; `effective_date` field |
| BR-MMS-014 | `models/menu.py` day/meal CheckConstraint |
| BR-MMS-015 | `services/menu.py` notification topic `menu.updated` |
| BR-MMS-016/017 | `schedule.py` UC-030; `services/billing.py` computation |
| BR-MMS-018 | `services/billing.py` state machine generated→finalized→published |
| BR-MMS-019 | `services/billing.py` rebate deduction only if approved |
| BR-MMS-020 | `models/feedback.py`; `scoping.py` caretaker+warden |
| BR-MMS-021/022/024 | `domain/rules.py` rebate validation; serializer |
| BR-MMS-023 | domain overlap check + DB index |
| BR-MMS-025 | `services/rebate.py` (external-policy boundary, no invented range) |
| BR-MMS-026 | `services/survey.py` audience (registered students only) |
| BR-MMS-027 | `schedule.py` UC-028 default No |
| BR-MMS-028 | `domain/rules.py` special-food lead-time |
| BR-MMS-029 | `schedule.py` UC-029; `decision_due_at` |
| BR-MMS-030 | `services/billing.py` charge on approval |
| BR-MMS-031 | `state_machine.py`; model CheckConstraint |
| BR-MMS-032 | `services/announcement.py` actor check |
| BR-MMS-033 | `models/announcement.py` history; `scoping.py` |
| BR-MMS-034 | `scoping.py` role-based report scope |
| BR-MMS-035 | `services/notifications.py` TOPICS allowlist |
| BR-MMS-038 | Blocked — no Mess Admin menu grant until ruling |
| BR-MMS-039 | `services/menu.py` actor check |
| BR-MMS-040 | `scoping.py` own-billing scope |
| BR-MMS-041 | `domain/rules.py` Yes/No |
| BR-MMS-042 | `scoping.py` own-requests-only (404 foreign) |

---

## Backend architecture, services, selectors and APIs

Layer order per new-module-prompt §4: `domain/` (pure Python, no Django/DRF/Celery) → `models/` → `selectors/` (incl. `scoping.py`) → `services/` → `api/` → `management/commands/` → `migrations/` → `tests/`.

- `domain/state_machine.py`: declarative `TRANSITIONS` table + `resolve(frm, to, actor_kind)`; `InvalidTransition`/`ActorNotAllowed`/`GuardFailed`.
- `domain/rules.py`: lead-time, rebate validation, menu structure, response options, scope boundary checks. Raises plain `DomainError` subclasses (service maps to HTTP).
- `models/`: one file per aggregate (see Step 3.2).
- `selectors/scoping.py`: visibility per role — student sees own requests/bills/rebates/responses/feedback; caretaker sees all pending operational requests for active role + own reports; warden sees supervisory + own reports; Mess Admin sees nothing operational; foreign id → 404 (never 403).
- `services/`: one file per use-case family (`registration.py`, `deregistration.py`, `rebate.py`, `special_food.py`, `survey.py`, `menu.py`, `billing.py`, `announcement.py`, `feedback.py`, `roles.py`, `notifications.py`). One transactional choke point per state change: `select_for_update`, refuse terminal source state, refuse wrong actor, write audit trail (`mms_special_food_transition` etc.), emit notification outbox row — all in one transaction.
- `api/views.py`: transport only; `permission_classes=[MODULE, HasPermission(...)]`; `@extend_schema` with examples; `throttle_scope` on writes; no model access directly.
- `api/serializers.py`: explicit `fields`; server-owned fields (`status`, `user_id`, `decided_by_user_id`, `decided_at`, `published_at`, totals) read-only.
- `api/urls.py`: mount under `api/v1/mms/`.
- `registry.py`, `schedule.py`, `tasks.py`, `apps.py`, `contracts.py`, `management/commands/seed_mms_policy.py`, `mms_readiness.py`.

Import-linter: `modules.mms` added to `modules-only-touch-contracts` source_modules + forbidden_modules (`models`, `services`, `selectors`, `api`, `domain`); `modules.mms.domain` added to `domain-is-pure-python`; new `mms-layers` layers contract (api > services > selectors > models > domain).

---

## Permissions, IAM integration and role grants

- Permissions defined in `registry.PERMISSIONS`; granted via `ROLE_GRANTS` keyed by exact `globals_designation` spellings (UNCONFIRMED). MMS defines **permissions, not roles**; owns no `Role`/`Permission`/`UserRole`/`ModuleAccess` table (IAM owns RBAC).
- `student`/`faculty`/`staff` granted by definition. `Mess Caretaker`/`Mess Warden`/`Mess Admin` granted via designations (unconfirmed spellings).
- `seed_modules` reads `registry.readiness()`; `readiness()` returns unmet prerequisites (e.g. missing special-food policy row) as sentences.
- `make permissions` regenerates `registry/permissions.json`; IAM applies via `seed_iam_permissions --manifest`. `permission_manifest --check` must be green: every declared permission granted or in SYSTEM_PERMISSIONS; no orphans; no prefix violations.
- Module grant drives sidebar visibility; permission drives actions. Two gates separately tested (grant-only → 403 at route; permission-only → 403 at action).
- `accesscontrol_module` row for `mms` created by `seed_modules`; status `planned` until active (flipped to `active` in final commit).

---

## Frontend routes, pages and actor-specific journeys

`client/src/modules/mms/` matching `client/src/modules/placement/` shape:
```
api/types.ts        types mirroring serializers
api/hooks.ts        TanStack Query hook per endpoint
api/hooks.test.tsx
components/         module-specific components
pages/              one file per route, each with <Page>.test.tsx
routes.tsx          route table (read by nav_matches_routes.py)
```

Routes relative to basePath `/mms`, each with matching nav item in `registry.py`; detail opens in drawer/modal on list page (no standalone detail routes). Route guards via `RequirePermission` with nav item's `required_permission`; shared pages gate controls with `can()`.

Student journeys: submit special food (lead-time validated) → see Requested → view own status/history → receive submission + decision notifications; submit rebate; submit deregistration; view menu/bills/balance/announcements; submit feedback; respond to vacation survey.
Caretaker journeys: open registration window; approve/reject registration/deregistration/rebate/special food; record Served/Cancelled; manage menu; review/finalize/publish bills; create vacation survey; view survey summary; publish announcements; view feedback; generate operational reports.
Warden journeys: view operational requests (oversight only); view supervisory reports; view announcements/feedback; publish announcements.
Mess Admin journeys: assign/reassign Caretaker/Warden (no operational data access).

Every page: loading, empty, error state; `pages/<Page>.test.tsx` covering five states + hidden control + main action; mocked at `lib/http.ts` boundary; queried by role/label. No `any`, `@ts-ignore`, `eslint-disable`, `console.log`; every input labelled; icon-only buttons `aria-label`; no hard-coded sample data; Phosphor icons only (draw circles in this repo — expected). Module chunk ≤ 150 kB gzip. Playwright happy path per UC main flow in `client/e2e/mms/`.

---

## Notifications and scheduled tasks

MMS-owned outbox replicating placement's pattern (cannot import placement internals — import-linter contract). `services/notifications.py` with allowlisted `TOPICS` matching PS §3.3.10 events; `enqueue()` inside caller's transaction; `dedupe_key` idempotency; `tasks.deliver_notifications` Celery task (60s beat, `NOTIFY_MAX_PER_RUN`, backoff, daily cap); console email backend by default (no accidental mail). Delivery failure handling outside MMS (BR-MMS-035). Broadcast topics (survey creation, menu update, bill publication) expand to recipients at send time via `directory.get_users` (batched).

Scheduled tasks (Step 3.7 table above): default-reject-special-food, default-vacation-response, activate-deregistration, generate-monthly-bills, send-vacation-reminder, deliver-notifications. All idempotent, run manually once, effects observed and recorded in quality report. Decision period and reminder cadence from configuration/policy, not hard-coded.

---

## Database migrations

One clean initial migration set (`0001_initial`) for the unmerged module; `makemigrations --check` clean. No destructive migrations. Data migrations idempotent if any (policy seeding via management command, not migration). Migrations reviewed by hand (Step 7.4). No `ops/db/roles.sql` in this repo (manifest-based via `seed_modules`/`permission_manifest`).

---

## Testing

Backend: mirror `modules/placement/tests/` — one file per concern:
- `test_domain.py` (no DB; every rule branch)
- `test_state_machine.py` (every illegal transition refused, enumerated from table)
- `test_privilege_escalation.py` (per endpoint; 403/404 as designed)
- `test_recruiter_isolation.py` (person A cannot see/change person B's rows incl. filters/search/export/nested ids)
- `test_concurrency.py` (real threads, `transaction=True`, `threading.Barrier`; e.g. concurrent special-food decisions, rebate overlap)
- `test_query_budgets.py` (constant query count at 2 and 20 rows per list endpoint)
- `test_schedule.py` (beat entries in merged config; each task twice + twice at once = single effect)
- `test_permission_drift.py` (test permission strings equal `registry.PERMISSIONS`)
- `test_notification_worker.py` (outbox enqueue/deliver idempotency)
- `test_journeys.py` (one test per live UC main success + alternate/exception flow via HTTP only)
Coverage gates: `pytest modules/mms --cov=modules/mms --cov-branch --cov-fail-under=90` and `--cov=modules/mms/domain --cov-fail-under=95`; neither report lists `tests/` or `migrations/`. Five rules broken on purpose (Step 5.15) with tests that catch each. Adversarial pass (Step 5.11) documented. Negative twin for every positive test. Plain user tested, not only interesting roles. Every live spec id cited by a test (`grep -rn '<ID>' modules/mms/tests`).

Frontend: `pages/<Page>.test.tsx` five states each; `api/hooks.test.tsx`; `test_client_route_guards.py` equivalent; vitest; `make check-client` (typecheck && test && build).

E2E: `client/e2e/mms/` Playwright spec per UC main flow; signedInAs/actAs; unique data; role/label selectors; no `waitForTimeout`; guarded-route deep-link specs expecting `NotPermitted`. `make e2e` with IAM on 8001 and `make dev` running. `client/e2e/accounts.ts` entry for each role needed (pre-approved).

No test in `modules/mms/tests/spec/` or `docs/[NN]-mms/spec-tests/` (Student 2's). Builder never edits those.

---

## Documentation, OpenAPI and permission generation

- `make schema` → `openapi/fusion-integrated.v1.yaml` committed and diff-clean; every endpoint `@extend_schema` example.
- `make permissions` → `registry/permissions.json` + `docs/02-iam/permission-catalog.generated.md` regenerated; IAM seeded via `seed_iam_permissions --manifest`.
- `docs/[NN]-mms/`: `mms-blueprint.md`, `mms-quality-report.md`, `mms-reference.md` (generated by `ops/docs/mms_reference.py` with `file:line` links from every live rule/UC/WF/CFR/AFR to enforcement code; exits non-zero if any link unresolved; `git status --porcelain` empty after), `domain-model.md`, `state-machine.md`.
- `ops/docs/mms_reference.py`: teaching-reference script (pre-approved).
- No AI attribution; no production data; single-line comments only.

---

## Security, auditability and operational requirements

Security self-audit (Step 7.7) item by item:
- Both gates on every view; no `AllowAny`; no view outside module router.
- No serializer `__all__`/`exclude`; server-owned fields read-only.
- Every list/detail from `scoping.py`; ids in request bodies checked against caller scope.
- No raw SQL/`.extra()`/string-built queries/`eval`/`pickle`/`yaml.load`/`subprocess` on request data.
- No file uploads in scope (none required by PS).
- Every write endpoint `throttle_scope`.
- Logs carry ids only; no error stack traces/SQL/file paths.
- No view loosens authentication/permission classes; CSRF token required (403 test).
- No credentials in tracked files; no new dependency without approval.
- `manage.py check --deploy --fail-level WARNING` green (production settings line).
- Audit trail: `mms_special_food_transition` and per-decision `decided_by_user_id`/`decided_at`; notification outbox as audit of triggered events.
- Fail-closed: foreign id → 404; unknown active role → no permissions; deny-wins not applicable (MMS has no DENY grants).

Operability: `seed_mms_policy` + `mms_readiness` management commands; deployment order migrate → seed policy → `seed_modules` → grants → readiness; readiness prints unmet prerequisites; `seed_modules` no "NOT active" warning. Fresh install proof (Step 7.8) on throwaway DB. Every scheduled task run manually once.

---

## File creation/modification list

**New (module-owned; create only after blueprint approval):**
```
modules/mms/
  __init__.py  apps.py  contracts.py  registry.py  schedule.py  tasks.py
  domain/__init__.py  domain/state_machine.py  domain/rules.py  domain/exceptions.py
  models/__init__.py  models/role_assignment.py  models/registration.py  models/deregistration.py
  models/menu.py  models/special_food.py  models/special_food_transition.py  models/rebate.py
  models/vacation.py  models/announcement.py  models/feedback.py  models/billing.py  models/notification.py
  selectors/__init__.py  selectors/scoping.py  selectors/*.py
  services/__init__.py  services/registration.py  services/deregistration.py  services/rebate.py
  services/special_food.py  services/survey.py  services/menu.py  services/billing.py
  services/announcement.py  services/feedback.py  services/roles.py  services/notifications.py
  api/__init__.py  api/views.py  api/serializers.py  api/urls.py
  management/__init__.py  management/commands/__init__.py
  management/commands/seed_mms_policy.py  management/commands/mms_readiness.py
  migrations/__init__.py  migrations/0001_initial.py
  tests/__init__.py  tests/test_domain.py  tests/test_state_machine.py  tests/test_privilege_escalation.py
  tests/test_recruiter_isolation.py  tests/test_concurrency.py  tests/test_query_budgets.py
  tests/test_schedule.py  tests/test_permission_drift.py  tests/test_notification_worker.py
  tests/test_journeys.py
client/src/modules/mms/
  routes.tsx  api/types.ts  api/hooks.ts  api/hooks.test.tsx
  components/  pages/*  pages/*.test.tsx
docs/[NN]-mms/
  mms-blueprint.md  mms-quality-report.md  mms-reference.md  domain-model.md  state-machine.md
ops/docs/mms_reference.py
```

**Pre-approved shared-file modifications (Step 4.0; name each; no unasked shared changes):**
- `config/settings/base.py` — `"modules.mms"` to `DOMAIN_MODULES`; `DEFAULT_THROTTLE_RATES` entry for `mms` write scope
- `config/urls.py` — `path("api/v1/mms/", include("modules.mms.api.urls"))`
- `config/celery.py` — merge MMS `BEAT_SCHEDULE`/`TASK_ROUTES`
- `client/src/app/registry.ts` — `mms` manifest entry (static import of routes)
- `.importlinter` — `modules.mms` in `modules-only-touch-contracts` source+forbidden; `modules.mms.domain` in `domain-is-pure-python`; `mms-layers` contract
- `openapi/fusion-integrated.v1.yaml` (regenerate via `make schema`)
- `registry/permissions.json` + `docs/02-iam/permission-catalog.generated.md` (regenerate via `make permissions`)

**Not to be touched:** `Makefile`, `.github/`, `ops/checks/`, `docs/08-delivery/`, `docker-compose.yml`, root `conftest.py` (no new IAM method needed), client config/vite/tsconfig/playwright/support, `client/src/auth/`, `client/src/ui/components/NotPermitted`, `pyproject.toml` sections, `KNOWN_UNENFORCED`, `config/settings/test.py`, `SILENCED_SYSTEM_CHECKS`, `client/e2e/` harness files, Student 2's `tests/spec/` and `spec-tests/`.

---

## Implementation phases and verification commands

**Phase 0–1:** This blueprint → Shaheen written approval → answer open questions (no code).
**Phase 3 — backend (bottom-up):** register module (4 settings/registry/urls/celery/import-linter/client-registry) → `domain/` → `models/` + `migrations/0001_initial` → `selectors/scoping.py` → `services/` → `api/` → `schedule.py`/`tasks.py` → `management/commands`. After each layer: `make check` (or targeted subset), `makemigrations --check`, ruff, import-linter.
**Phase 4 — tests:** all backend test files; coverage gates 90%/95%; five rules broken on purpose; adversarial pass; `grep -rn` every live id; `test_journeys.py`.
**Phase 5 — frontend:** routes/pages/types/hooks/components; page tests (5 states); route-guard test; `make check-client`; Playwright specs; `make e2e` (needs IAM + dev).
**Phase 6 — ops/docs:** `make schema`; `make permissions`; deploy check; fresh-install proof (Step 7.8, throwaway DB); `ops/docs/mms_reference.py` + generated reference; quality report (Step 7.9); browser walkthrough (Step 6.9, "not run" if browser unavailable).
**Phase 7 — review:** local commit (not push); Student 2 review rounds until 10/10 all nine dimensions; fix findings; re-run every gate; update quality report.
**Phase 8 — post-10/10:** Student 2 spec tests (they own `tests/spec/`/`spec-tests/`); re-run all four spec suites; quality report; push/PR only on explicit approval.

Verification commands:
- `make check` (full backend CI)
- `make check-client` (typecheck && test && build; wait for tsc)
- `make e2e` (IAM + dev running)
- `pytest modules/mms --cov=modules/mms --cov-branch --cov-fail-under=90`
- `pytest modules/mms --cov=modules/mms/domain --cov-branch --cov-fail-under=95`
- `manage.py check --deploy --fail-level WARNING` (production settings env)
- `make schema` + `schema-check`; `make permissions` + `permission_manifest --check`
- `.venv/bin/python ops/docs/mms_reference.py && git status --porcelain` (empty)
- Fresh install: `dropdb/createdb` → `DB_NAME=fusion_integrated_fresh make migrate` → `migrate mms zero` → `make migrate` → `seed_modules` → `mms_readiness` (then seed IAM, grant account, policy seed, readiness again).

---

## Every live specification ID → implementation + test mapping

Consolidated from the traceability tables above:
- **22 CFRs** → each mapped to domain/services/selectors/api layer and test(s) (test_domain / test_privilege_escalation / test_recruiter_isolation / test_query_budgets / test_notification_worker / test_schedule / test_journeys).
- **101 AFRs** → grouped under parent CFRs; each AFR's statement maps to a specific field/constraint/guard/enforcement point; all cited by tests.
- **31 UCs** → each mapped to service method + state-machine transition + API endpoint + journey test (`test_journeys.py` test named `test_uc_<nn>_<slug>`).
- **41 active BRs** → each mapped to `domain/rules.py`, model constraint, selector scope, service, or schedule task; test named `test_br_mms_<nn>`.
- **16 basis + 5 composite workflows** → each mapped to `domain/state_machine.py` transitions (or service method for non-workflow-grounded UCs) + `test_state_machine.py` enumeration.
- **Retired BR-MMS-037 / MMS-FR-102** → excluded; `grep` must not find them in `modules/mms/` or `client/src/modules/mms/`.

Every `grep -rn '<ID>' modules/mms/tests` must return at least one hit where the test asserts the rule's effect (not just names the id).

---

## Review status

This draft is complete and ready for Shaheen's written blueprint approval. No production code has been created or modified. Awaiting:
1. Confirmation of proposed identifiers (`module_code`=`mms`, `NN`=`09`, `ID_PREFIX`=`MMS`).
2. Confirmation of `globals_designation` spellings for Mess Caretaker / Mess Warden / Mess Admin.
3. Rulings on open questions #5, #10, #11, #12, #13, #14, #15 (institution-defined values and unresolved spec ambiguities).
4. Shaheen's written approval of this blueprint (and each known gap) before Step 4.1 implementation.
