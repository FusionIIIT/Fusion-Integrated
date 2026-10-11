# Employee Leave Management implementation blueprint

**Status:** Approved working baseline. Application implementation is in progress.

**Module:** Employee Leave Management
**Module code:** `leave`
**Backend:** `modules.leave`
**API prefix:** `/api/v1/leave/`
**Frontend:** `client/src/modules/leave/`
**Frontend base route:** `/leave`

The user approved this blueprint as the working implementation baseline and
authorized implementation. BR-EL-030 governs policy versioning for this module.
The Workflow v1.6 STTs govern state transitions; the older RTM registry count is
recorded in §11 as a source-version discrepancy, not used to add or remove
transitions.

## 1. Specification inventory

| Source | Version | Intake result |
|---|---:|---|
| ELM Problem Statement | 1.4 | Synchronized baseline; actors, leave scope, external dependencies, and policy boundaries read. |
| ELM Functional Requirement Specification | 1.5 | 32 coherent CFRs and 128 atomic AFRs; mapping columns present. |
| ELM Use Case Specifications | 1.4 | 20 active use cases (18 actor-triggered, 2 event-triggered) and retired EL-UC-006. |
| ELM Business Rule Specifications | 1.4 | 38 identifiers: 36 active and 2 retired. |
| ELM Traceability Matrix | 1.5 | CFR, UC, BR, and workflow registries/mappings present; matrix identifies itself as WF v1.5-era material. |
| ELM Workflow Specifications | 1.6 | Four composite workflows; registry lists BW-EL-01 through BW-EL-19 and XTP-EL-01. The basis-workflow count/classification is unresolved; see Â§11. |

Retired identifiers are BR-EL-021 (replaced by BR-EL-034) and BR-EL-026
(retired with no active rule assigned), and EL-UC-006 (modify pending request;
replaced by the withdraw-and-submit path in BR-EL-034 / EL-UC-007 / EL-UC-001).
The workflow document's legacy WF-EL-02 is retired as an in-place modification
workflow; pending withdrawal remains in CW-EL-01 and CW-EL-03. Retired IDs are
not implementation requirements.

The requirement workbook's 32 CFRs and 128 AFRs are sourced from its stated
counts and the FR sheet. The traceability matrix gives populated mappings for
all 32 CFRs; it distinguishes minimum-sufficient representations from broader
workflow traces. Its workflow registry is v1.5-era and lists 19 basis entries;
the later v1.6 workflow source lists 17 complete paths and its STTs govern.

## 2. Architecture and integration constraints

The repository has one domain module (`modules.placement`) and uses Django
`DOMAIN_MODULES`, a module-owned `registry.py`, root URL includes, an import-linter
layer contract, and a React module manifest with static lazy imports. Reads are
intended to go through selectors; writes through services. `domain/` must remain
plain Python. IAM owns identity, designation grants, permissions, and module
grants; ELM must not add identity or role tables.

All cross-module person references will be integer IAM `user_id` values, not
foreign keys. ELM will not import another module's internal implementation.
`modules.directory.contracts.get_users(ids)` supplies a batched profile DTO;
the existing directory surface also has `get_employees()`, but neither API
currently provides organizational hierarchy, Unit Head resolution, designation
assignments, or employee leave/attendance records. The project has no
Academic Calendar contract in the inspected modules. These gaps are external
contract dependencies, not permission to query ERP tables directly.

The current platform configuration already provides PostgreSQL, optional Redis
cache, a Celery broker setting, IAM authentication, and DRF defaults. The ELM
module must use these settings and the existing principal/permission gates.
Whether a notification/outbox contract exists for ELM's assignment, reminder,
and escalation events must be settled before implementation; the current
placement notification implementation is module-owned, not a shared ELM
notification contract.

## 3. Questions and design decisions from Phase 1

### 3.1 Bounded context

ELM is one bounded context: leave applications, account transactions, decision
history, substitute responsibilities, policy/calendar configuration, and
resumption records form one leave-management lifecycle. It owns its tables in
the Fusion-Integrated database. IAM identity and academic calendar/attendance
remain external.

### 3.2 Cross-module contracts

Required interfaces are:

1. Existing directory profile lookup for employee identity and display fields.
2. A batched employee/org-unit/hierarchy contract that resolves each employee's
   organization, Unit Head, employee kind, and the authoritative designation or
   authority assignment needed by routing.
3. An Academic Calendar contract for vacation periods used by VL.
4. If resumption synchronization is required beyond ELM's own record, an
   attendance/leave-record contract with a defined owner and write interface.
5. An agreed notification delivery interface for workflow assignment,
   reminders, and escalations, or an explicit decision that ELM owns the
   delivery records and sends through the platform's existing configured
   channel.

Interfaces 2â€“5 are not exposed by the inspected Fusion-Integrated module
contracts. Exact endpoints, data shape, ownership, and development/test
availability remain open.

### 3.3 Identity

Use `Principal.user_id` and integer actor/employee identifiers. The existing
`UserDTO` has `kind`, `department`, `discipline`, and display data, but does not
resolve designation or the reporting hierarchy. Do not create an employee FK or
duplicate IAM user table.

### 3.4 Actors and role mapping

The source actor inventory is: Employee (Faculty or Staff), Substitute /
Responsibility Holder, Unit Head, Deputy Registrar (Estt.) / Establishment
Processing Role, Dean, Registrar, Director, Sanctioning Authority, Leave
Administrator, Authorized Administrative Role, and System for automatic
transitions. Academic Calendar is an external information dependency, not an
ELM actor. Employee maps to the IAM basic `faculty` and `staff` kinds.

The exact institute designation names, which actions each designation may
perform, and which are basic-kind capabilities are not assigned in the
specification bundle. The repository's role-assignment guide permits declared
designation keys, but using invented operational designations would still need
explicit mentor approval. Do not finalize `ROLE_GRANTS` until that mapping is
approved. System-only permissions will be separated from human role grants.

### 3.5 Scope

Candidate selector scopes, subject to approval: employees see only their own
applications, balances, and history; a substitute sees only assigned
responsibility requests; a reviewer sees only actionable tasks assigned to
them; a Unit Head sees requests for employees in their resolved organizational
unit; system processing is limited to due year-end/SLA work. Administrative
record maintenance is limited to the approved administrative scope. The
hierarchy contract is needed to implement unit scope; no cross-unit broad read
is proposed. A foreign or out-of-scope record should not be disclosed.

### 3.6 Time and scheduled/event work

The specifications include event-triggered year-end processing (EL-UC-020)
and SLA reminder/escalation processing (EL-UC-021). The schedule, trigger
source, timezone boundary, retry/idempotency contract, and production Celery
beat ownership need confirmation. Assignment notifications occur on task
assignment (BR-EL-035). Reminder and escalation only apply while a task remains
pending (BR-EL-032/033). No cadence or numeric SLA thresholds are specified;
EL-UC-018 configures the thresholds.

### 3.7 Balances

Candidate design: immutable append-only account transactions are authoritative;
balance views aggregate the ledger. Corrections are compensating transactions.
This follows the repository's module-generation guidance and the specification's
requirement to record account transactions. Account keying (category, leave
year, employee kind, policy parameter), precision/rounding, carry-forward
representation, and transaction reference/idempotency keys need review before
the data model is approved.

### 3.8 Policy and calendar

The ELM baseline says current configured leave-policy parameters are used
without a draft/publish/effective-version lifecycle (BR-EL-030). Per the user
direction, this ELM-specific rule governs over generic repository guidance.
Holiday/RH calendar publication has a separately specified currently-effective
published calendar (BR-EL-031) and remains separately modeled.

## 4. Proposed domain model

These are design candidates, not generated model definitions. Approve or revise
them before code generation.

| Candidate aggregate/entity | Purpose and key data |
|---|---|
| LeaveApplication | Applicant `user_id`, category, requested interval/CL half, purpose, station-leave details, supporting evidence reference, lifecycle status, and request type (new/cancellation/extension). |
| SubstituteAssignment | Application, applicant and substitute IDs, responsibility interval, response, and response history. |
| WorkflowTask / DecisionHistory | Actionable actor/user assignment, workflow state/event, decision/recommendation, timestamps, and immutable transition history. |
| LeaveAccountTransaction | Employee ID, category, signed amount, transaction kind, source application/year-end process, and actor; append-only. |
| LeavePolicyConfiguration | Current configured entitlement/routing parameters; exact versioning behavior blocked by BR-EL-030 conflict. |
| HolidayCalendar / HolidayDate | Published calendar identity, dates, RH applicability, publication and current-effective selection. |
| ResumptionRecord | Approved leave reference, actual return date/details, reviewer, outcome, and any resulting account/record synchronization reference. |
| SLA configuration / event log | Configured reminder/escalation thresholds and auditable processing results for actionable tasks. |
| Notification record | Assigned recipient, task/event reference, delivery state, and attempt history if notification ownership is confirmed. |

No cross-module foreign keys are proposed. Same-module relationships may use
foreign keys. Constraints and indexes will be specified against actual read
queries and concurrency requirements during generation, after the actors,
workflow set, and account precision are approved.

## 5. Workflow design

The composites named by the workflow specification are CW-EL-01 (new leave and
pending withdrawal), CW-EL-02 (approved leave cancellation), CW-EL-03 (ongoing
leave extension), and CW-EL-04 (resumption review). XTP-EL-01 is a conditional
system transition pattern for SLA escalation that changes task routing or
responsibility. Reminder-only escalation is not a workflow transition.

The v1.6 document says STTs are authoritative. Once the basis-workflow conflict
is resolved, generation will encode transitions from those exact tables,
including substitute response/replacement, direct CL/RH Unit Head decisions,
higher sanction with optional configured Establishment step, Director
self-sanction, cancellation outcomes, incremental extension, pending
withdrawal, and normal/early/late resumption. This blueprint does not invent
states or select an interpretation of the disputed basis-workflow registry.

## 6. Permissions and role grants (provisional)

Permission codes must use the confirmed `leave` module prefix and the
repository's closed action vocabulary. Resource/action candidates include
application view/create/update/review/approve, substitute update, task view,
balance view, policy manage, calendar manage/publish, record update/import,
resumption review, and SLA manage. System-only permission candidates cover
year-end processing and SLA event processing. This is not an approved
`registry.py` list: exact granularity, role holders, and dangerous-action
classification depend on the actor/designation decision and the final endpoint
inventory. No role grant is proposed to an unverified designation.

The module registry will use code `leave`, label `Employee Leave Management`,
base path `/leave`, and server-filtered navigation items tied to the approved
permissions. It will remain `planned` until the separate activation decision;
the current request is local implementation, not production activation.

## 7. Proposed API and frontend integration

Endpoint families derived from the active use cases (exact methods, request
schemas, gates, and responses to be finalized after role approval):

| Use case | Proposed API family |
|---|---|
| EL-UC-001, 007â€“009, 019 | Create, view, withdraw, cancel, extend applications; nominate replacement substitute. |
| EL-UC-002â€“005 | Substitute response, Unit Head review, configured Establishment routing, final sanction decision. |
| EL-UC-010â€“011 | Submit resumption and review it. |
| EL-UC-012â€“013 | Own balances/history and printable/exportable accessible application. |
| EL-UC-014â€“015, 018 | Maintain policy/hierarchy, publish holiday/RH calendars, configure task SLA thresholds. |
| EL-UC-016â€“017 | Record already-sanctioned offline leave and maintain authorized leave records. |
| EL-UC-020â€“021 | Celery/event handlers for year-end and SLA processing; no user-facing endpoint unless the platform's task conventions require one. |

Backend integration points expected: add `modules.leave` to `DOMAIN_MODULES`,
include `modules.leave.api.urls` under `/api/v1/leave/`, add the ELM layer/import
contract, generate its own migrations, and update the generated permissions
manifest if registry tooling supports this module. No unrelated module or IAM
internals should be changed.

Frontend integration points expected: create pages/components and API
types/hooks under `client/src/modules/leave/`; register a static import in
`client/src/app/registry.ts`; use the existing HTTP client and route table
conventions. The shell builds routes from IAM-granted module codes. Navigation
must remain server-driven. No new login, shell, or hardcoded client sidebar is
proposed.

Candidate pages: employee leave dashboard/apply, own applications and details,
balances/history, assigned tasks, substitute response, and authorized
administrative configuration/record views. Visibility and exact page list
remain contingent on the approved permission/designation mapping.

## 8. Mechanical integration log (to be completed during integration)

No mechanical corrections have been made. During the later integration phase,
each correction will record file, mechanical error, smallest correction,
reason, and confirmation that business behavior did not change. Functional or
workflow issues found during permitted startup/build checks will be reported,
not repaired.

## 9. Verification plan (after code generation and integration)

Run the requested mechanical checks locally after the implementation is ready:

- Backend environment/dependency readiness and `python manage.py check`.
- `python manage.py makemigrations --check --dry-run` and `python manage.py migrate` if a configured PostgreSQL service is available.
- Backend startup/import check (`python manage.py runserver 8002`) as a smoke check only.
- Frontend `npx tsc --noEmit` and `npm run build`.
- Final `git status --short`, `git diff --stat`, and `git diff --check`.

Do not run systematic business-rule/workflow correctness audits as part of
Assignment #6 integration. The local `.venv` currently reports Python 3.14 and
does not have Django installed; CI uses Python 3.12. Dependencies may be
installed in the project environment after this blueprint is approved, without
changing the global Python installation.

## 10. Traceability plan

Each active BR and UC is assigned a planned primary enforcement point. This is
an implementation placement plan, not a claim that requirements have already
been implemented or verified. Cross-cutting rules may be enforced at more than
one layer.

### Active business rules

| ID | Requirement | Planned primary enforcement point |
|---|---|---|
| BR-EL-001 | Supported leave-category eligibility | `domain/eligibility.py`, invoked by application/extension services. |
| BR-EL-002 | CL entitlement and lapse | `domain/accounts.py`; year-end service and account transaction. |
| BR-EL-003 | RH entitlement/calendar applicability | `domain/eligibility.py` plus current published calendar selector. |
| BR-EL-004 | SCL entitlement/admissibility decision | Domain validation for limit; sanction decision service for authority judgment. |
| BR-EL-005 | Non-faculty EL credit/carry-forward | Account domain and year-end service. |
| BR-EL-006 | Faculty VL and vacation-period applicability | Domain validation using Academic Calendar contract. |
| BR-EL-007 | VL-to-EL conversion | Year-end domain operation and ledger service. |
| BR-EL-008 | Converted EL is usable/carryable | Account ledger and balance selector. |
| BR-EL-009 | COL entitlement/evidence/carry-forward | Domain validation and year-end service. |
| BR-EL-010 | Half-day CL accounting | Leave-day/account domain. |
| BR-EL-011 | Continuous-day count for EL/COL/VL | `domain/counting.py`, used by new/extension validation. |
| BR-EL-012 | Active overlap and distinct CL halves | Application selector plus domain overlap rule. |
| BR-EL-013 | Station Leave lives inside application | Application data model/serializer; no separate request aggregate. |
| BR-EL-014 | Substitute is eligible and non-overlapping | Substitute eligibility domain using employee and leave selectors. |
| BR-EL-015 | Substitute consent gate/recovery | State transition domain/service. |
| BR-EL-016 | Unit Head final authority for CL/RH | Authority resolver and workflow transition guard. |
| BR-EL-017 | Unit Head recommendation for higher-sanction leave | Workflow transition domain/service. |
| BR-EL-018 | Higher-sanction routing | Authority resolver and routing service. |
| BR-EL-019 | Contextual authority/optional Establishment step | Current hierarchy configuration resolver. |
| BR-EL-020 | Director self-sanction | Authority resolver and workflow transition guard. |
| BR-EL-022 | Immediate pending withdrawal | Application lifecycle service and transition table. |
| BR-EL-023 | Pre-start approved-leave cancellation | Cancellation service, transition table, and compensating ledger entry on approval. |
| BR-EL-024 | Revised leave requires a fresh application | Lifecycle domain; no in-place mutation endpoint. |
| BR-EL-025 | Ongoing EL/COL/VL extension/incremental posting | Extension domain and approval service. |
| BR-EL-027 | EL/COL/VL resumption submission/review authority | Resumption service and authority resolver. |
| BR-EL-028 | Normal/early/late resumption outcome | Resumption domain and reviewed synchronization service. |
| BR-EL-029 | Offline-sanctioned leave synchronization | Offline-entry service with sanction evidence; no approval transition. |
| BR-EL-030 | Current configured policy/hierarchy, no version lifecycle | Policy selector/configuration service; **blocked by Â§11 conflict**. |
| BR-EL-031 | Effective published holiday/RH calendar | Calendar selector and publish service. |
| BR-EL-032 | Pending-only reminder threshold | SLA event handler/service and task-pending selector. |
| BR-EL-033 | Pending-only configured escalation | SLA event handler/service; route-changing transition only when configured. |
| BR-EL-034 | No pending in-place modification | Application lifecycle service and API surface (no update-to-pending endpoint). |
| BR-EL-035 | Notify on actionable task assignment | Task assignment service and approved notification interface. |
| BR-EL-036 | Role-based authorization | DRF module-grant/permission gates plus scoped selectors. |
| BR-EL-037 | Maintenance/offline entry is not sanctioning | Separate maintenance/offline services; no sanction transition. |
| BR-EL-038 | Configurable SLA thresholds | SLA configuration service and UC-021 event handler. |

### Active use cases

| ID | Use case | Planned primary enforcement point |
|---|---|---|
| EL-UC-001 | Apply for Leave | Application serializer, eligibility domain, application service. |
| EL-UC-002 | Respond to Substitute Request | Substitute response API/service and workflow transition. |
| EL-UC-003 | Review Leave-Related Request at Unit Head | Assigned-task selector, permission gate, review service. |
| EL-UC-004 | Verify and Route Higher-Sanction Request | Assigned-task selector, hierarchy resolver, route service. |
| EL-UC-005 | Make Final Sanctioning Decision | Assigned-task selector, permission gate, decision service. |
| EL-UC-007 | Withdraw Pending Request | Application owner selector and withdrawal service. |
| EL-UC-008 | Request Cancellation of Approved Leave | Owner selector, pre-start guard, cancellation service. |
| EL-UC-009 | Request Extension of Ongoing Leave | Extension validation domain and service. |
| EL-UC-010 | Submit Resumption of Duty | Owner selector and resumption service. |
| EL-UC-011 | Review Resumption | Assigned-task selector, authority gate, review/sync service. |
| EL-UC-012 | View Leave Balances and History | Own-row selector and account-history API. |
| EL-UC-013 | Obtain Printable/Exportable Leave Application | Scoped application selector and export API. |
| EL-UC-014 | Maintain Policy and Hierarchy Configuration | Admin permission gates and configuration service. |
| EL-UC-015 | Maintain and Publish Holiday/RH Calendar | Admin permission gates and calendar service. |
| EL-UC-016 | Record Already-Sanctioned Offline Leave | Admin permission gate, evidence serializer, synchronization service. |
| EL-UC-017 | Maintain Authorized Leave Records | Admin permission gate and record-maintenance service. |
| EL-UC-018 | Configure Workflow SLA Thresholds | Admin permission gate and SLA configuration service. |
| EL-UC-019 | Nominate Replacement Substitute After Decline | Application owner selector and substitute eligibility service. |
| EL-UC-020 | Execute Year-End Leave Processing | Celery task/service, idempotent ledger entries; schedule trigger to be confirmed. |
| EL-UC-021 | Process SLA Threshold Event | Celery/event handler, pending-task guard, notification/escalation service. |

## 11. Recorded discrepancies and integration dependencies

1. **Workflow registry version:** The v1.5 traceability workbook lists 19 BW
   entries, while the later v1.6 workflow document defines 17 Basis Workflows
   and supplies the authoritative STTs. Implementation follows the 17 BW IDs
   in v1.6 and does not infer transitions from the older registry.
2. **Policy versioning:** BR-EL-030's no-version lifecycle exception is
   approved for ELM and will be implemented. Holiday/RH calendar publication
   remains governed by BR-EL-031.
3. **Authority/designation mapping:** The module will use only literal role
   labels present in the ELM actor specifications as functional permission
   groups. It will not claim those labels are provisioned IAM designations;
   deployment must map/assign approved institutional designations to those
   permission groups through IAM. Without those assignments, the corresponding
   routes remain denied.
4. **External interfaces:** The repository does not expose organizational
   hierarchy/Unit Head resolution, Academic Calendar vacation periods, or an
   attendance synchronization API. ELM will implement provider boundaries and
   report unavailable dependencies; it will not query ERP tables or fabricate
   responses.
5. **Notifications and scheduling:** ELM can use its own outbox with the
   configured Django email backend and existing Celery infrastructure. The
   local schedule uses calendar-year processing and the configured timezone.
   Production delivery depends on SMTP and a running Celery worker/Beat.
6. **Account representation:** Use Decimal quantities for fractional days and
   append-only transaction rows with unique source keys. Policy rows configure
   entitlements and carry-forward. Calendar year is used for year-end because
   the baseline describes annual entitlements and year-end processing; a
   different institutional leave year requires configuration before production.

These dependencies do not block local implementation or compilation/migration
checks, but IAM grants and external providers are required for complete
production integration.

## 12. Review/approval record

- [x] User approved this blueprint as the working baseline.
- [x] BR-EL-030 is approved over generic policy-versioning guidance.
- [x] Workflow v1.6 STTs are the workflow source of truth.
- [x] External dependencies will be explicit unavailable-by-default boundaries.

Application generation and local integration are authorized. Generated business
behavior will be treated as frozen during Assignment #6 integration corrections.
