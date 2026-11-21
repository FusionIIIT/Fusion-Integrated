# Patent Management System — Implementation and Verification Record

**Current branch:** `assignment9_PMS`
**Specification baseline:** PMS Problem Statement v1.2; Requirement Registry, Use Cases, Business Rules, Workflows, and Traceability Matrix v1.3
**Reviewed base commit:** `73b49fbe0c08ee5153f55e13cb62044a9ea4f194`
**Verification snapshot:** base commit plus R2 commits `c7bae1e`, `d8f1ac5`, `09c2539`, `6bb56b8`, `0d8d60a`, `dad1ede`, `5875c4f`, `eee3556`, and `642bc57` on `assignment9_PMS`, as of 2026-11-22
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

- `modules/pms/models.py`, `migrations/` — 18 PMS models and four migrations, including `PmsRoleAssignment` (whose presence is an unresolved IAM architecture violation).
- `modules/pms/domain/` — state machine, policy configuration, validation, and domain errors.
- `modules/pms/services/` — application, review, budget, attorney, filing, office-action, maintenance, document, licensing, audit, deadline, and notification logic.
- `modules/pms/selectors/` — application visibility scoping.
- `modules/pms/api/` — 37 URL patterns in `urls.py`, serializers, permissions, and views. Some patterns support multiple HTTP methods.
- `modules/pms/tasks.py`, `schedule.py` — Celery deadline and notification tasks and Beat schedule.
- `modules/pms/tests/` — domain, workflow, business-rule, API, authorization, policy, scheduling, notification, model, and audit tests.
- `client/src/modules/pms/` — API hooks/types, shared action form and application selector, routes, functional pages, and partial page/route tests.
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

The initial implementation report’s check results are historical and predate M3–M6. M7 did not rerun the backend suite or frontend build. This R2 continuation added partial PMS frontend and HTTP journey tests; current coverage and check limits are recorded below.

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

The four migrations are `0001_initial.py` (domain schema), `0002_seed_pms_configuration.py` (specified default values), `0003_separate_prefiling_workflow_states.py` (normalizes legacy application statuses and keeps substates in workflow records), and `0004_fail_closed_document_scan_defaults.py` (marks prior scan claims unverified and changes the defaults to fail closed). `showmigrations pms` against the local development database reported all four unapplied; `make check` applied migrations only to its temporary test database.

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

Pages use the shared HTTP/CSRF client and React Query hooks. UI role checks control visibility only; API and service authorization remain authoritative. Application selectors are populated from the scoped applications API. The shared forms display validation, loading, success, and server error feedback. PMS client tests currently cover My Applications, Reports, Workflow Oversight, and all 13 direct route guards; other PMS pages still lack the required page-state, hidden-control, and main-action tests.

## Current implementation gaps and dependencies

- **Document files and malware scanning:** APIs accept document metadata and an optional storage URL; they do not accept or store binary files. With no trusted scanner configured, submission, revision, and version upload reject document acceptance with HTTP 503. Caller-supplied `is_clean` values are ignored, model defaults are false, and migration 0004 marks old scan claims unverified. A supported scanner and binary storage flow remain unavailable.
- **Prior art:** no external patent/publication query connector is configured. Search now returns HTTP 503 and logs an unavailable/not-queried event; no simulated results are exposed. Attaching a reference remains separate. Search becomes available only when a supported external source is provided.
- **Appeals:** an Applicant can submit an appeal, and the API can decide a known appeal ID. There is no appeal-list endpoint and application detail does not return appeal IDs, so a Director cannot discover appeals through a review queue.
- **Application history:** current details and audit rows are available; there is no dedicated complete application history endpoint/timeline.
- **Reports:** the API and UI provide visible-application counts and status/domain aggregates. Scheduled reports, filtering/customization, export, workload/financial/deadline dashboards, and historical/trend analysis are absent.
- **Administration/exceptions:** PMS configuration and attorney-panel CRUD are present. PMS role grants are platform-IAM-owned; no PMS role-assignment endpoint is exposed. Workflow oversight is read-only and does not resolve conflict or exception cases.
- **IAM scope data:** the platform session exposes active role, permissions and module grants, but no Director domain assignment projection. PMS still contains `PmsRoleAssignment`, which duplicates IAM-owned designation/access data. Do not remove it until IAM exposes the required domain-scope data and the Director domain authorization can be preserved.
- **External systems:** patent-office filing/grant decisions, financial/payment execution, DMS binary storage, external prior-art queries, and email transport are recorded or delegated at the boundary rather than integrated as live systems.
- **Conditional policy:** appeal period, escalation chain, budget threshold, and maintenance schedule remain unset unless an operator configures them. `PatentBudget.threshold_limit` still has a legacy model default of 100000; current escalation logic reads `PmsConfiguration.budget_threshold` and does not consult that legacy value when policy is unset. This schema/API field can therefore appear misleading and should be reconciled in a later implementation decision.
- **Traceability source quality:** all 203 AFR rows in the supplied RTM have blank UC mapping, UC locations, BR mapping, workflow mapping, minimum-representation, and coverage cells. The registry’s AFR-to-UC/BR/WF columns and each UC’s CFR/AFR links are also blank. The source Summary says coverage is full, which is unsupported by its own blank evidence cells. M7 leaves those source sheets intact; its separate implementation map labels associations as direct or derived.

The M7 workbook includes 371 traceability rows (203 AFR, 30 CFR, 33 use cases, 84 business rules, 21 workflows). Its status is an evidence classification based on current code references, feature-level associations, and test-file presence. “Covered by tests” means a related test source exists; it does not mean the test was run in M7 or that it asserts every mapped requirement clause. `PMS_IMPLEMENTATION_REFERENCE.md` is generated from that map plus current source/test files that cite each exact ID; it is a navigation index, not proof of coverage or passing tests. Frontend behavior remains only partially tested.

## Latest verification — 2026-11-22

- `make check-client` passed in this session: TypeScript checks for the app and E2E project, 63 client tests across 10 files (including 25 PMS tests), and the Vite production build. React Router emitted upgrade notices; Vite emitted its existing large-chunk advisory.
- Focused command `cd client && npx vitest run src/modules/pms/routes.test.tsx src/modules/pms/pages/WorkflowPage.test.tsx src/modules/pms/pages/ReportsPage.test.tsx src/modules/pms/pages/MyApplicationsPage.test.tsx` passed (25 tests). Direct route refusals passed for all 13 PMS child routes; page states passed for these three pages.
- `.venv/bin/pytest modules/pms/tests/test_client_route_guards.py -q` passed (2 tests). `.venv/bin/ruff check modules/pms ops/docs/pms_reference.py` passed. `make permissions` completed and produced no additional manifest change.
- `.venv/bin/python ops/docs/pms_reference.py --check` passed: 371 mapped identifier rows, no referenced file paths missing. The generated file links the M7 map and current source/test files with exact ID citations; links do not certify behavior or test adequacy.
- `.venv/bin/pytest modules/pms/tests/test_journeys.py --collect-only -q` passed collection (6 tests). `DB_NAME=fusion_integrated DB_USER=fusion_admin .venv/bin/pytest modules/pms/tests/test_journeys.py -q` could not initialize PostgreSQL; all six errored at database setup because the server was unreachable. The focused query-budget and fail-closed backend test attempts were similarly blocked. Docker access to `/var/run/docker.sock` was denied. These backend test attempts are **blocked, not passed**.
- `make e2e` failed before test execution: Playwright reported `Process from config.webServer was not able to start. Exit code: 1`. The E2E account registry contains only `student` and `placementOfficer`; neither is a PMS-designated test account. The expected IAM helper virtualenv was absent. No PMS Playwright specs or browser walkthroughs were run.
- The prior recorded `make check` passed against local PostgreSQL in an earlier session, before the new `test_journeys.py` was added. It was not rerun in this environment; it is not current verification of the new backend tests.
- The previously recorded focused query-budget test passed in the earlier working-database environment after the selector prefetch fix. It could not be rerun here, so current execution is environment-blocked.
- No original specification, source RTM, or Student 2 spec-test files were modified. No approver decision or waiver was inferred.

R2-02 remains open pending written acceptance from the actual assignment approver for each retained gap or implementation of those live requirements; the approver's identity and approval record are not present in this repository. R2-03 remains open pending an approved IAM-owned Director-domain assignment projection/API or an explicitly approved alternative. R2-04 remains only fail-closed and needs a trusted malware scanner and binary-storage path. R2-06 is blocked: PMS role accounts and a working IAM/backend/browser environment are needed. R2-07 is partial: six HTTP journeys were added, but not every live use case main and alternate flow is covered, and this session could not execute them. R2-08 remains not run. R2-09 is partial: three page components and every direct route guard are tested; the remaining pages still need loading/empty/error, hidden-control, and main-action coverage. R2-12 is partial: the 371-row reference generator/output now exist, but no approved blueprint exists. No R2 pass or assignment completion is claimed.

### Browser walkthrough status

No result, request-log output, screenshot, or other walkthrough evidence is claimed for these rows. Each remains **not run** because no PMS test accounts or live backend/IAM walkthrough were available in the supplied harness. Assignment guide Step 6.9 requires a role/dump username/use-case/result table with actual `runserver` log lines under each row, plus one keyboard-only flow. Screenshots are not required and the guide prohibits using screenshots from the production ERP. The repository has no screenshot folder/naming convention for this walkthrough. Do not mark a row complete until the real browser flow and request log are recorded; link only to evidence actually captured.

The role registry in `client/e2e/accounts.ts` contains `stu00001` (student) and `stf00062` (placement officer), with no PMS designation grants. The expected helper interpreter `../Fusion_System_Administrator/Backend/venv/bin/python` is absent in this checkout. `make e2e` could not start its configured web server, so this session could not capture authentic request logs or complete the keyboard-only walk. The Student 2/author must supply the PMS-enabled environment and perform these rows.

| Use case | Spec actor | Result |
| --- | --- | --- |
| UC-PMS-001 | Applicant | Not run — author walkthrough needed |
| UC-PMS-002 | Applicant | Not run — author walkthrough needed |
| UC-PMS-003 | Applicant | Not run — author walkthrough needed |
| UC-PMS-004 | Applicant or Attorney | Not run — author walkthrough needed |
| UC-PMS-005 | Applicant | Not run — author walkthrough needed |
| UC-PMS-006 | Applicant | Not run — author walkthrough needed |
| UC-PMS-007 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-008 | Director | Not run — author walkthrough needed |
| UC-PMS-009 | Director | Not run — author walkthrough needed |
| UC-PMS-010 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-011 | Attorney | Not run — author walkthrough needed |
| UC-PMS-012 | Attorney | Not run — author walkthrough needed |
| UC-PMS-013 | Attorney | Not run — author walkthrough needed |
| UC-PMS-014 | Attorney | Not run — author walkthrough needed |
| UC-PMS-015 | Attorney | Not run — author walkthrough needed |
| UC-PMS-016 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-017 | Attorney | Not run — author walkthrough needed |
| UC-PMS-018 | Director | Not run — author walkthrough needed |
| UC-PMS-019 | Applicant; other roles when authorized | Not run — author walkthrough needed |
| UC-PMS-020 | Applicant | Not run — author walkthrough needed |
| UC-PMS-021 | Director | Not run — author walkthrough needed |
| UC-PMS-022 | Applicant | Not run — author walkthrough needed |
| UC-PMS-023 | Director | Not run — author walkthrough needed |
| UC-PMS-024 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-025 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-026 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-027 | PCC_ADMIN | Not run — author walkthrough needed |
| UC-PMS-028 | PCC_ADMIN; Director where authorized | Not run — author walkthrough needed |
| UC-PMS-029 | Applicant | Not run — author walkthrough needed |
| UC-PMS-030 | Applicant | Not run — author walkthrough needed |
| UC-PMS-031 | Director | Not run — author walkthrough needed |
| UC-PMS-032 | Director | Not run — author walkthrough needed |
| UC-PMS-033 | Attorney | Not run — author walkthrough needed |
| Plain user | No PMS role | Not run — author walkthrough needed |
