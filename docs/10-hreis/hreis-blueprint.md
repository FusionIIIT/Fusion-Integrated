# HR-EIS module blueprint and implementation handoff

**Status:** Student 2’s approval to begin code generation was relayed on 2026-11-16. Backend implementation has been started and is being handed to the independent specification-testing phase as a draft PR. This is not a claim of 10/10 review completion.

**Branch:** `module/hreis`
**Specification set:** `/home/zer0/Documents/Study/Fusion ERP/HR Domain Modeling/day 4/`
**Assignment environment:** `module-only`

## 1. Assignment inputs

| Prompt value | Proposed value | Basis |
|---|---|---|
| Module name | Human Resource — Employee Information System (HR-EIS) | Assignment and supplied HR specifications |
| Specification folder | `/home/zer0/Documents/Study/Fusion ERP/HR Domain Modeling/day 4/` | Local six-document bundle |
| Specification prefixes | `HR-CFR-`, `HR-AFR-`, `HR-UC-`, `BR-HR-`, `BW-HR-`, `CW-HR-` | Specification identifiers |
| Module code / URL segment | `hreis` | Assignment module identity |
| Environment | `module-only` | Assignment 9 guide |
| Documentation folder | `docs/10-hreis/` | Student 1’s assigned folder number: 10 |

## 2. Scope and target shape

Build the HR-EIS backend inside `Fusion-Integrated`, following `modules/placement` and the canonical new-module prompt. The assigned implementation scope is backend only: employee service records, leave, annual appraisal, LTC and CPDA requests, approval workflows, financial processing status, notifications, and audit history, to the extent defined by supplied requirements. The module remains isolated from IAM and other modules and uses the platform’s existing identity and permission contracts. No frontend or Fusion-client work is included in this backend branch.

The six inputs to be read and traced are:

1. `01_HR_Problem_Statement_v1.2_SYNCHRONIZED`
2. `02_HR_Requirement_Registry_CFR_AFR_v1.3_FINAL`
3. `03_HR_Use_Case_Specifications_v1.3_FINAL`
4. `04_HR_Business_Rule_Specifications_v1.3_FINAL`
5. `05_HR_Workflow_Specifications_v1.3_FINAL`
6. `06_HR_Traceability_Matrix_v1.3_FINAL`

Inventory recorded from the bundle: 14 CFRs, 107 AFRs, 34 active business rules, 21 active use cases (19 actor-triggered and 2 event-triggered), 13 basis workflows, and 4 composite workflows. `HR-UC-020` is retired; `BR-HR-032` is retired/relocated. They are not implementation requirements. Every active identifier must be accounted for in the final traceability section and cited at the relevant enforcement point or listed as an explicitly accepted known gap.

## 3. Proposed architecture

Keep the feature inside `modules/hreis/`, using the platform’s existing module boundaries:

- `registry.py`, contracts, API serializers/views/permissions, and URL registration for the module surface.
- `domain/` for HR entities, state definitions, and pure domain invariants.
- `selectors/` for permission-scoped reads and query-efficient projections.
- `services/` for transactional commands and workflow transitions. All writes that change status, balances, assignments, or financial status pass through these services.
- `schedule.py` for only those scheduled jobs explicitly required by the specs.
- `client/src/modules/hreis/` for the module’s standalone client pages and route guards.
- `tests/` for domain, service, permission/isolation, API, query-budget, and client coverage in the existing project style.
- `docs/10-hreis/` for the approved blueprint, traceability, operational notes, and quality report required by the canonical prompt.

No HR-owned authentication, user, role, or permission tables. Store the platform’s integer `user_id` as the actor/owner reference; do not create cross-module foreign keys. Use the existing IAM permission checks and fail closed. Scope row visibility in selectors, independently of permission checks. Reuse core audit/outbox/pagination/error primitives where the repository provides them.

### Proposed domain records

Subject to source-field confirmation during implementation: employee service record; leave policy and effective-dated quota; leave request and append-only leave-balance ledger; appraisal cycle/window, appraisal record, reviewer/authority assignment, and decision history; LTC request and decision history; CPDA request and decision history; approval-route/policy versions; financial-processing status references; notification/outbox record; and append-only audit event. Avoid duplicating IAM identity data or modeling an external finance/payroll system as if it were present.

### Invariants and transaction boundaries

- Every read is scoped to the authorized employee/department/authority context; client-side hiding is not security enforcement.
- State changes validate the current state, actor permission, route position, and applicable effective policy inside one transaction.
- Leave submission/approval and ledger changes are atomic; serialize competing balance updates and preserve an append-only ledger.
- Approval/decision history and audit events are append-only; closed appraisal records cannot be silently rewritten.
- Policy changes are effective-dated and immutable by version. Missing policy must produce a clear actionable validation/configuration result, never an invented default or server error.
- External processing is represented as a status/reference only until an actual integration contract is supplied and approved.

## 4. Actor and role proposal

Use the roles named by the use cases and map them to the existing designation values only after Student 2 confirms the mapping. The public fixture contains `hradmin`, `SectionHead_HR`, `Accounts Admin`, six HOD designations (CSE, ECE, ME, Design, NS, Liberal Arts), `Director`, and `Registrar`.

| Spec actor | Proposed designation mapping | Review status |
|---|---|---|
| Employee / Faculty / Staff | Existing basic faculty/staff roles as assigned by the platform | Confirm UC distinctions and whether all staff categories share access |
| HR Administrator | `hradmin` | Proposed; confirm exact role and scope |
| Section Head, HR | `SectionHead_HR` | Proposed; confirm exact spelling and scope |
| Head of Department | The six fixture HOD designations | Confirm routing/department scoping |
| Registrar | `Registrar` | Proposed; confirm route position and scope |
| Director | `Director` | Proposed; confirm route position and scope |
| Accountant | `Accounts Admin` | **Unconfirmed mapping**; no literal `Accountant` designation found in the fixture |

Do not invent additional roles or designation-name authorization. Permission codes will use the `hreis.<resource>.<action>` namespace and only verbs from the platform’s closed permission-action list. The exact permission catalog and grants must be traced to each UC/BR and approved before implementation.

## 5. Workflow proposal

These are state shapes, not permission to invent missing transitions. Route order and policy values come from versioned configuration supported by the specs.

| Area | Proposed lifecycle | Guardrails / unresolved points |
|---|---|---|
| Leave | Draft → Submitted/Pending current authority → Pending next configured authority → Approved or Rejected | Submission validates eligibility and available balance; final approval and ledger deduction are atomic. Route and quota values must be configured from approved policy. |
| Appraisal | Not submitted → Submitted → Reviewer assigned / Pending review → Pending next configured authority → Finalized/Closed | Appraisal windows and reviewer assignment are policy data. **User ruling:** BR-HR-014 is the base; allow repeated traversals when the configured authority route calls for them, with no fixed “one extra traversal” cap. Do not finalize before the configured route is complete. |
| LTC | Draft → Submitted/Awaiting HR verification → Pending current/next configured authority → Approved or Rejected → financial processing status recorded | BR-HR-019 mentions “Returned,” but no UC/workflow defines who creates that state or its transition. Do not add a return transition without a ruling. |
| CPDA | Draft → Submitted → Pending configured authority/authorities → Approved or Rejected → financial processing status recorded | Purpose, amount, supporting documents, eligibility, and financial rules must be taken from the specs/configuration; no external finance API is assumed. |

Notification generation and audit capture accompany the specified events. Actual email/Fusion-dashboard delivery depends on an integration contract and remains an explicit gap below.

## 6. Implementation and traceability

The source traceability matrix leaves its mapping columns blank. The inventory and a per-ID statement-to-code/gap register are in `hr-eis-traceability.md`; it covers 14 CFRs, 107 AFRs, 34 active BRs, 21 active UCs, and 13 basis plus 4 composite workflows. Each row is explicitly marked partial or gap where full evidence is not available. The register does not claim complete implementation or one test per ID.

The backend currently contains employee service-record and effective-dated policy models, request and append-only decision/audit/leave-ledger records, declarative leave/appraisal/LTC/CPDA transitions, permission-scoped selectors, service-layer validation, API serializers/views/URLs, registry grants, migrations, and focused tests. The appraisal route is configuration-driven; per the Student 1 ruling, BR-HR-014 is the base and repeated configured authority traversals are allowed.

## 7. Known gaps carried into partner testing

1. **Authority policy:** the code validates route designations against the fixture but no complete, approved authority order or department-scoping matrix is supplied. Operators must configure versioned policy before requests can proceed.
2. **Accountant role:** `Accounts Admin` is used as the fixture designation for the spec’s Accountant; the precise finance permissions remain a policy decision.
3. **Leave policy:** starting balances are ledger entries, and eligibility/routes are configurable; quota, accrual, carry-forward, and special leave rules need source-backed values and tests.
4. **Appraisal:** submission windows and routes are configurable. Complete appraisal content capture, reviewer identity/eligibility checks, service-record archival, amendments, and reopen behavior remain incomplete.
5. **LTC/CPDA:** request types and generic fields/flows exist. Prescribed form schemas, eligibility, limits, detailed verification criteria, and all financial correctness rules remain incomplete.
6. **LTC Returned state:** BR-HR-019 mentions a returned state without an authoritative transition definition. No return transition is implemented pending a ruling.
7. **Integrations:** payroll/finance status is represented locally. No external adapter is implemented because no service contract is present; automatic real-time synchronization is not claimed.
8. **Notifications:** request events create in-app notification records. Reminder scheduling, policy/deadline event delivery, dashboard integration, and official email are not implemented; cadence is not invented.
9. **Audit:** writes are captured as append-only records. Full event-by-event source coverage, retention rules, and compliance-report requirements still need validation.
10. **Verification:** tests are focused rather than per-ID journeys; the full Student 2 generated test suite, coverage thresholds, mutation tests, fresh-database seed proof, adversarial review, and independent 10/10 review are pending.

## 8. Explicitly outside this module-only build

No real Fusion-client sidebar change, legacy Fusion integration, new IAM/authentication schema, cross-module database foreign key, or undocumented payroll/finance/email API is included. If the final assignment requires an external repository change, request separate written approval and record the exact handoff; do not silently expand this module branch.

## 9. Student 2 approval and handoff

- Student 2 approval to begin code generation, relayed by Student 1: **“Student 2 said done ok proceed with code gen.”**
- Date recorded: **2026-11-16**.
- Student 1’s BR-HR-014 ruling: use the business rule as the base and allow any number of traversals when the configured route calls for them.
- The draft PR is the handoff point for Student 2 to begin independent, specification-derived tests and review. This handoff does not claim that those tests or the required independent score have already passed.
