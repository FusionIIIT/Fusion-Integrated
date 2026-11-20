# Patent Management System — Implementation and Verification Record

**Current branch:** `assignment9_PMS`
**Specification baseline:** PMS Problem Statement v1.2; Requirement Registry, Use Cases, Business Rules, Workflows, and Traceability Matrix v1.3
**Code snapshot:** M6 commits through `9026735`
**M7 purpose:** describe repository evidence; this report does not change or supersede requirements.

## Specification set reviewed

The source documents reviewed for this report are the six supplied files in the original `11-PMS` folder:

1. `01_PMS_Problem_Statement_v1.2_SYNCHRONIZED.docx`
2. `02_PMS_Requirement_Registry_CFR_AFR_v1.3_DIRECT_FINAL.docx`
3. `03_PMS_Use_Case_Specifications_v1.3_DIRECT_FINAL.docx`
4. `04_PMS_Business_Rule_Specifications_v1.3_DIRECT_FINAL.docx`
5. `05_PMS_Workflow_Specifications_v1.3_DIRECT_FINAL.docx`
6. `06_PMS_Traceability_Matrix_v1.3_DIRECT_FINAL.xlsx`

The first five files and the original workbook remain unchanged. The derived M7 workbook is [PMS_Traceability_Matrix_M7.xlsx](PMS_Traceability_Matrix_M7.xlsx).

## Product and architecture

PMS manages institutional patent applications from submission through internal review, assignment, budgeting, external filing records, office-action response tracking, licensing records, appeals, and post-grant maintenance. PMS records institutional workflow and externally supplied outcomes; it does not make patent-office, financial, or legal decisions.

The backend is a Django module registered as `pms`, mounted at `/api/v1/pms/`. Important directories:

- `modules/pms/models.py`, `migrations/` — 17 PMS models and three migrations.
- `modules/pms/domain/` — state machine, policy configuration, validation, and domain errors.
- `modules/pms/services/` — application, review, budget, attorney, filing, office-action, maintenance, document, licensing, audit, deadline, and notification logic.
- `modules/pms/selectors/` — application visibility scoping.
- `modules/pms/api/` — 37 URL patterns in `urls.py`, serializers, permissions, and views. Some patterns support multiple HTTP methods.
- `modules/pms/tasks.py`, `schedule.py` — Celery deadline and notification tasks and Beat schedule.
- `modules/pms/tests/` — domain, workflow, business-rule, API, authorization, policy, scheduling, notification, model, and audit tests.
- `client/src/modules/pms/` — API hooks/types, shared action form and application selector, routes, and functional pages.
- `modules/pms/registry.py`, `permissions.py` — server-driven navigation and IAM permission declarations.

`PatentApplication` owns dependent records through Django foreign keys. Actor references are integer IAM user IDs; there are no cross-module IAM foreign keys. Pre-filing budget and attorney assignment progress is stored in workflow records so the application’s main status is not used to represent parallel stages.

## Milestones and Git evidence

The branch history contains the following implementation stages:

- **M0 baseline:** `4e02b49` added PMS domain/models/services/API; `0dcbb8d` added backend tests; `8f57d9b` added placeholder client routes; `4a0a761` registered the module and permissions; `4e16d1e` added the initial report.
- **M0a–M0c:** the current branch has no distinct commits bearing these milestone labels. Their completion cannot be independently attributed to a labeled commit from this history.
- **M1:** `1367421` introduced configurable policies and deadlines. Only specified defaults (15 business days, 60 calendar days, 30/15/5 alert offsets) are seeded.
- **M2:** `a359762` records DEC-1–3 state-machine corrections; `f6296b4` applies the exact 50 MB rejection boundary; `282f0b6` aligns budget/filing transitions; `e565b9f` separates pre-filing substates from application status.
- **M3:** `24089fc` scopes API data to visible applications; `dadd5f6` adds service-layer actor ownership checks.
- **M4:** `c8361cb` adds configuration API; `01a5e87` completes attorney-panel API; `d0d249e` adds scoped workflow oversight.
- **M5:** `e45ebd4` makes outbox delivery retry-safe; `9c252a7` automates configured maintenance deadline alerts; `2a05039` schedules PMS deadline and notification tasks.
- **M6:** `f19537f` adds submission/tracking; `9d2c18c` adds review and attorney workflows; `9026735` adds administration, workflow oversight, audit, and reporting screens.

The initial implementation report’s check results are historical and predate M3–M6. M7 did not rerun the backend suite or frontend build. A previous M6 build attempt could not start because this checkout did not have TypeScript installed (`tsc: not found`). No PMS-specific frontend test files exist under `client/src/modules/pms/`.

### Decisions and constraints visible in the repository

- **DEC-1:** grant is recorded as an external official outcome by an Attorney; PMS does not decide grant.
- **DEC-2:** budget escalation does not invent a higher-authority PMS actor or approval transition.
- **DEC-3:** “Modify Decision” ends at the recorded appeal outcome; no unspecified downstream state is created.
- **DEC-4:** documents at or above 50 MiB are rejected; exactly 50 MiB is rejected.
- **DEC-7:** unspecified thresholds and policy values have no seeded defaults.
- **DEC-8:** maintenance cycles are created only from an explicitly configured jurisdiction schedule.
- **DEC-9:** missed review/office-action deadlines escalate without changing application status; ordinary business-day counting is Monday–Friday unless a holiday calendar is configured.

No DEC-5 or DEC-6 decision record was found in the current repository documentation or code comments. Their approved wording should be recovered from the historical decision log if they remain governing decisions.

## Backend, data, and automation

The three migrations are `0001_initial.py` (domain schema), `0002_seed_pms_configuration.py` (specified default values), and `0003_separate_prefiling_workflow_states.py` (normalizes legacy application statuses and keeps substates in workflow records).

The API covers application CRUD/lifecycle actions, review, budget, attorney assignment/response, patentability/legal advice, external filing/grant records, office actions and responses, maintenance, prior art, document metadata/versioning, licensing, inventor consent, attorney panel, configuration, audit, reports, and workflow oversight. There are 37 URL patterns in the current `urls.py`; M4 instructions referred to 39 routes. Whether that count included individual method operations is undocumented, so the count convention remains unverified.

`visible_applications()` scopes Applicant, Director, Attorney, and PCC_ADMIN reads. Nested views resolve the parent application through the same selector. Services enforce assigned-Director and assigned-Attorney rules on workflow writes. `test_authorization.py` includes role, cross-application, Director-scope, and service-ownership checks. This is implementation evidence, not a claim that every permission combination or object path has been tested.

Celery Beat schedules a daily deadline scan and a notification drain every 60 seconds. Deadline offsets and maintenance dates come from configuration; dedupe keys make repeated alert/outbox creation idempotent. Mail delivery still depends on the Directory service returning email addresses and on the deployment’s configured mail backend. A missing escalation chain remains unset by design.

## Frontend pages and API use

`routes.tsx` registers permission-gated PMS routes and lazy-loads these pages:

- My Applications and Submit Application
- Application Queue and Reviews (including budget decisions)
- Attorney workspace / Filings
- Office Actions, Maintenance, and Licensing
- Workflow Oversight, Reports / My Reports, Administration, and Audit Trail

Pages use the shared HTTP/CSRF client and React Query hooks. UI role checks control visibility only; API and service authorization remain authoritative. Application selectors are populated from the scoped applications API. The shared forms display validation, loading, success, and server error feedback. The client has no PMS-specific automated tests, and M6’s build/type check remains unverified because the local `tsc` executable was absent.

## Current implementation gaps and dependencies

- **Document files:** APIs and UI record document metadata, versions, and an optional storage URL; they do not accept or store binary files. Malware status is a caller-supplied boolean that defaults clean; no scanner or fail-closed scanning integration exists. The M6 document size input is capped at 52,428,799 bytes, while the server remains authoritative.
- **Prior art:** `services/prior_art.py` returns deterministic sample records. No external patent/publication query connector, keyword optimization, or classification mapping is present. The frontend deliberately does not present those sample records as real search results. Attaching a reference and logging a search are separate implemented capabilities.
- **Appeals:** an Applicant can submit an appeal, and the API can decide a known appeal ID. There is no appeal-list endpoint and application detail does not return appeal IDs, so a Director cannot discover appeals through a review queue.
- **Application history:** current details and audit rows are available; there is no dedicated complete application history endpoint/timeline.
- **Reports:** the API and UI provide visible-application counts and status/domain aggregates. Scheduled reports, filtering/customization, export, workload/financial/deadline dashboards, and historical/trend analysis are absent.
- **Administration/exceptions:** PMS configuration and attorney-panel CRUD are present. PMS role grants are platform-IAM-owned; no PMS role-assignment endpoint is exposed. Workflow oversight is read-only and does not resolve conflict or exception cases.
- **External systems:** patent-office filing/grant decisions, financial/payment execution, DMS binary storage, external prior-art queries, and email transport are recorded or delegated at the boundary rather than integrated as live systems.
- **Conditional policy:** appeal period, escalation chain, budget threshold, and maintenance schedule remain unset unless an operator configures them. `PatentBudget.threshold_limit` still has a legacy model default of 100000; current escalation logic reads `PmsConfiguration.budget_threshold` and does not consult that legacy value when policy is unset. This schema/API field can therefore appear misleading and should be reconciled in a later implementation decision.
- **Traceability source quality:** all 203 AFR rows in the supplied RTM have blank UC mapping, UC locations, BR mapping, workflow mapping, minimum-representation, and coverage cells. The registry’s AFR-to-UC/BR/WF columns and each UC’s CFR/AFR links are also blank. The source Summary says coverage is full, which is unsupported by its own blank evidence cells. M7 leaves those source sheets intact; its separate implementation map labels associations as direct or derived.

The M7 workbook includes 371 traceability rows (203 AFR, 30 CFR, 33 use cases, 84 business rules, 21 workflows). Its status is an evidence classification based on current code references, feature-level associations, and test-file presence. “Covered by tests” means a related test source exists; it does not mean the test was run in M7 or that it asserts every mapped requirement clause. Frontend behavior has no PMS-specific automated tests.

## Verification boundary

M7 performed static source and test-file inspection to update the report and RTM. It did not run extensive tests, alter implementation code, or modify the six original specifications. Before M8 or production use, Student 2 should execute backend and frontend suites in the configured environment and review every partial, unimplemented, and externally dependent RTM row.
