# IAA — Blueprint

Module: Institute Accounts and Audits · code `iaa` · docs `docs/14-iaa/` · environment `module-only`.
Spec: `14-IAA` v1.2/v1.3 (Problem Statement, CFR/AFR registry, UC, BR, WF, RTM).

> **Approval status:** awaiting written approval from Student 2. No row of this document is
> final until that approval is recorded in the quality report (Step 7.9).

## Phase 0 inventory (Step 1.4)

| Artefact | Count | Ids | Retired |
|---|---|---|---|
| Business rules | 19 | IAA-BR-001…006, 101…104, 201, 202, 301, 302, 401, 501…504 | none stated |
| Use cases | 27 | IAA-UC-101…105, 201…203, 302…304, 401…404, 501…504, 601…604, 701…704 | none stated; **IAA-UC-301 does not exist** (numbering gap, not a retirement) |
| Workflows | 23 | BW-IAA-01…19 (basis), CW-IAA-01…04 (composite) | none |
| Requirements | 18 CFR, 75 AFR | CFR-IAA-01…18, AFR-IAA-001…075 | none |
| RTM | populated | `06_…Traceability_Matrix` — used as a cross-check only; coverage below is derived from each rule's own text |

Actors named across BR/UC/WF: Basic User (faculty, staff, employee, department representative),
Finance Staff, HoD, Dean, Director (the three "Approving Authority" roles), Auditor, System Admin,
System (timer / automatic anomaly).

Contradictions and gaps found while reading:
1. BR-104 vs UC-101: a Draft is editable; nothing says a Draft may be deleted. **No delete is built.**
2. TA has no Draft (CW-IAA-02 starts at "Not Submitted → Submitted"); expense has one. Built as written.
3. Expense Finance review has no "reject" outcome in CW-IAA-01; TA Finance verification does
   ("Policy verification fails → Rejected"). Built as written — open question Q5.
4. "Escalated → Escalated" (an escalated item going overdue again) appears in no table. Not built — Q6.
5. BR-102's "available departmental budget" has no defined source. Built as an append-only ledger — Q4.

## Phase 1 answers (§2)

- **2.1 Bounded context:** one — every UC acts on the same financial record, its approvals, anomalies and observations.
- **2.2 Other modules:** `directory.contracts.get_users` only (display names, a person's department for HoD scoping). Nothing new is asked of any module.
- **2.3 Identity:** every person is a plain `user_id` (`UserScopedModel`); the acting role is `principal.active_role`, stored as text on every audit row (BR-003, BR-502).
- **2.4 Roles:** see §(d). Six designations the IAM must hold; none exists in `fusion-dev.dump`, so all are provisioned with `assign_role` for testing — Q1.
- **2.5 Scope:** `selectors/scoping.py`, 404 never 403 — owner rows, assigned rows, office-wide rows; System Admin sees no operational row (BR-004).
- **2.6 Time:** yes — overdue approvals escalate (BR-401, UC-203). One beat entry, every 10 minutes.
- **2.7 Money:** the departmental budget is an append-only ledger (`BudgetEntry`); recording a request writes a commitment row, corrections are reversing rows. No payment is executed (BR-006).
- **2.8 Policy:** one effective-dated `PolicyVersion` holds every administered value (timeout, TA high-value threshold, request types, required documents, approval routes, anomaly resolver chains). Never edited — superseded. With none seeded, every action that needs it refuses with code `policy_missing` and names what is missing.

## (a) Traceability

| Id | What it requires | Layer | Enforcement point (planned) | Notes |
|---|---|---|---|---|
| IAA-BR-001 | Creator never decides own item; reroute to next authority | services | `services/decisions.py::decide — actor vs record.user_id, reroute` | |
| IAA-BR-002 | Route by amount, type, department, hierarchy | domain | `domain/routing.py::select_route, snapshot on record` | |
| IAA-BR-003 | Act and log under the active role | services | `principal.active_role written on every TrailEntry` | |
| IAA-BR-004 | System Admin: configuration only | selectors | `scoping returns no operational row for iaa_system_admin; grants hold no operational code` | |
| IAA-BR-005 | Decision needs remarks | domain | `domain/state_machine.py guard has_remarks + DB Check on ApprovalStep` | |
| IAA-BR-006 | Recording is non-monetary | services | `services/processing.py writes status + ledger commitment only` | |
| IAA-BR-101 | Completeness only at submission | domain | `domain/validation.py::submission_errors` | |
| IAA-BR-102 | Budget check at Finance review; insufficiency → anomaly | services | `services/review.py::validate → services/anomalies.raise_automatic` | |
| IAA-BR-103 | Anomalies tracked Open → Resolved/Escalated | domain | `domain/state_machine.py ANOMALY table` | |
| IAA-BR-104 | Read-only after submission | services | `services/records.py::update_draft refuses non-draft` | |
| IAA-BR-201 | TA verification against policy | services | `services/review.py::validate (ta)` | |
| IAA-BR-202 | High-value TA needs authority approval | domain | `domain/policy.py::is_high_value` | |
| IAA-BR-301 | Observation states Open/Responded/Closed, never deleted | domain | `OBSERVATION table; PROTECT FKs; no delete endpoint` | |
| IAA-BR-302 | Close only after satisfactory verification | services | `services/observations.py::review` | |
| IAA-BR-401 | Overdue approval escalates | services | `tasks.escalate_overdue_approvals → services/decisions.py::escalate_overdue` | |
| IAA-BR-501 | Active role + ownership/assignment scope | selectors | `selectors/scoping.py (404) + HasPermission` | |
| IAA-BR-502 | Role changes never rewrite history | models | `role stored as text on TrailEntry/ApprovalStep; append-only` | |
| IAA-BR-503 | Audit every state change | services | `services/trail.py::log inside each choke point` | |
| IAA-BR-504 | Notifications for every listed event | services | `services/notify.py called from each choke point` | |
| IAA-UC-101 | Create Expense / Voucher Request</td> | services | `services/records.py::create_expense` |  |
| IAA-UC-102 | Submit Expense / Voucher Request</td> | services | `services/records.py::submit` |  |
| IAA-UC-103 | Review &amp; Validate Request (Finance)</td> | services | `services/review.py::raise_query, validate` |  |
| IAA-UC-104 | Respond to Finance Clarification Query</td> | services | `services/records.py::respond_query` |  |
| IAA-UC-105 | Process &amp; Record Approved Expense / Voucher Request</td> | services | `services/processing.py::record` |  |
| IAA-UC-201 | Approve / Reject Request</td> | services | `services/decisions.py::decide` |  |
| IAA-UC-202 | Handle Escalated Approval</td> | services | `services/decisions.py::decide (escalated step)` |  |
| IAA-UC-203 | Escalate Overdue Approval</td> | services | `services/decisions.py::escalate_overdue` |  |
| IAA-UC-302 | Flag Anomaly</td> | services | `services/anomalies.py::flag` |  |
| IAA-UC-303 | Resolve or Escalate Anomaly</td> | services | `services/anomalies.py::resolve, escalate` |  |
| IAA-UC-304 | Create Automatic Anomaly</td> | services | `services/anomalies.py::raise_automatic` |  |
| IAA-UC-401 | Submit TA Form</td> | services | `services/records.py::create_ta` |  |
| IAA-UC-402 | Verify TA Form</td> | services | `services/review.py::validate (ta), raise_query` |  |
| IAA-UC-403 | Approve / Reject High-Value TA Form</td> | services | `services/decisions.py::decide (ta)` |  |
| IAA-UC-404 | Process &amp; Record TA Request</td> | services | `services/processing.py::record (ta)` |  |
| IAA-UC-501 | Raise Audit Observation</td> | services | `services/observations.py::raise_observation` |  |
| IAA-UC-502 | Respond to Audit Observation</td> | services | `services/observations.py::respond` |  |
| IAA-UC-503 | Review and Close Audit Observation</td> | services | `services/observations.py::review` |  |
| IAA-UC-504 | Review Financial Records for Audit</td> | selectors | `selectors/scoping.py::records_for (auditor)` |  |
| IAA-UC-601 | View Reports &amp; Dashboards</td> | services | `services/reports.py::summary` |  |
| IAA-UC-602 | Export Report</td> | services | `services/reports.py::export_rows` |  |
| IAA-UC-603 | Track Own Request / TA Status</td> | selectors | `selectors/scoping.py::records_for (owner)` |  |
| IAA-UC-604 | View Notifications and Pending Actions</td> | selectors | `selectors/notifications.py` |  |
| IAA-UC-701 | Switch Active IAA Role</td> | IAM | `IAM set_active_role — not rebuilt (Q3)` | known gap, Q3 |
| IAA-UC-702 | Manage IAA Role Assignments</td> | IAM | `IAM assign_role — not rebuilt (Q3)` | known gap, Q3 |
| IAA-UC-703 | Configure Approval Hierarchy &amp; Thresholds</td> | services | `services/configuration.py::publish_policy (routes)` |  |
| IAA-UC-704 | Configure Financial Year &amp; Policy Parameters</td> | services | `services/configuration.py::publish_policy, add_financial_year` |  |
| BW-IAA-01 | Expense/Voucher Standard Success | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-02 | Expense/Voucher One Additional Approval Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-03 | Expense/Voucher Rejection | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-04 | Expense/Voucher One Clarification Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-05 | Escalated Expense/Voucher Approval | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-06 | Escalated Expense/Voucher Rejection | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-07 | Standard TA Processing | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-08 | High-Value TA Approval | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-09 | High-Value TA One Additional Approval Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-10 | High-Value TA Rejection | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-11 | TA One Clarification Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-12 | Anomaly Direct Resolution | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-13 | Anomaly One Escalation Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-14 | Audit Observation Straight Closure | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-15 | Audit Observation One Revision Traversal | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-16 | Escalated High-Value TA Approval | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-17 | Escalated High-Value TA Rejection | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-18 | Automatic Anomaly Direct Resolution | domain | `domain/state_machine.py` table rows | journey test |
| BW-IAA-19 | Automatic Anomaly One Escalation Traversal | domain | `domain/state_machine.py` table rows | journey test |
| CW-IAA-01 | Expense/Voucher Lifecycle | domain | `domain/state_machine.py` table rows | journey test |
| CW-IAA-02 | TA Lifecycle | domain | `domain/state_machine.py` table rows | journey test |
| CW-IAA-03 | Anomaly Lifecycle | domain | `domain/state_machine.py` table rows | journey test |
| CW-IAA-04 | Audit Observation Lifecycle | domain | `domain/state_machine.py` table rows | journey test |
| CFR-IAA-01 | Expense/Voucher Drafting, Submission, Locking, and History | services | `services/records.py` | parent of its AFRs |
| CFR-IAA-02 | Finance Validation and Clarification | services | `services/review.py` | parent of its AFRs |
| CFR-IAA-03 | Expense/Voucher Internal Completion and Record Retention | services | `services/processing.py` | parent of its AFRs |
| CFR-IAA-04 | Configured Approval Routing and Decisions | services | `services/decisions.py + domain/routing.py` | parent of its AFRs |
| CFR-IAA-05 | Approval Timeout Escalation | services | `services/decisions.py::escalate_overdue + schedule.py` | parent of its AFRs |
| CFR-IAA-06 | Budget Validation and Insufficiency Handling | services | `services/review.py + services/budget.py` | parent of its AFRs |
| CFR-IAA-07 | Material Anomaly Management | services | `services/anomalies.py` | parent of its AFRs |
| CFR-IAA-08 | TA Claim Submission | services | `services/records.py::create_ta` | parent of its AFRs |
| CFR-IAA-09 | TA Finance Verification and Clarification | services | `services/review.py` | parent of its AFRs |
| CFR-IAA-10 | High-Value TA Approval | services | `services/decisions.py` | parent of its AFRs |
| CFR-IAA-11 | TA Internal Completion and Terminal Record | services | `services/processing.py` | parent of its AFRs |
| CFR-IAA-12 | Audit Record Review and Observation Initiation | services | `services/observations.py + selectors` | parent of its AFRs |
| CFR-IAA-13 | Audit Observation Response, Verification, and Closure | services | `services/observations.py` | parent of its AFRs |
| CFR-IAA-14 | Role-Scoped Reporting and Export | services | `services/reports.py` | parent of its AFRs |
| CFR-IAA-15 | User Status Tracking and Notifications | services | `selectors/notifications.py + services/notify.py` | parent of its AFRs |
| CFR-IAA-16 | Administration and Configuration Governance | services | `services/configuration.py` | parent of its AFRs |
| CFR-IAA-17 | Active Role Context, Historical Role Integrity, and RBAC | services | `selectors/scoping.py + TrailEntry.actor_role` | parent of its AFRs |
| CFR-IAA-18 | Complete IAA Audit Trail | services | `services/trail.py` | parent of its AFRs |
| AFR-IAA-001 | allow an authorized Basic User to create an expense/voucher request and save it as Draft. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-002 | allow the request creator to enter request type, amount, department, description, and supporting information. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-003 | allow the request creator to attach supporting documents to an expense/voucher request. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-004 | permit a Draft to be saved even when submission-mandatory information is incomplete, while identifying missing information. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-005 | allow a Basic User to submit a Draft expense/voucher request for formal processing. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-006 | block formal submission when mandatory fields or required documents are missing. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-007 | On successful submission, the system shall set the request to Submitted and route it to Finance Staff. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-008 | After submission, the system shall prevent ordinary creator editing except through supported clarification/correction responses. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-009 | preserve a complete request action and status history. | services | `services/records.py` | CFR-IAA-01 |
| AFR-IAA-010 | allow Finance Staff to review submitted expense/voucher request details and supporting documents. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-011 | allow Finance Staff to validate expense/voucher requests against applicable financial and policy requirements. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-012 | allow Finance Staff to request clarification or additional evidence during validation. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-013 | allow the concerned Basic User to respond to a Finance clarification query with information or evidence. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-014 | After a clarification response, the system shall return the request to Finance review without losing prior history. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-015 | A request that passes Finance validation shall become Finance Validated and enter its configured approval route. | services | `services/review.py` | CFR-IAA-02 |
| AFR-IAA-016 | allow Finance Staff to mark an approved expense/voucher request as internally processed/recorded. | services | `services/processing.py` | CFR-IAA-03 |
| AFR-IAA-017 | Internal processing/recording states shall not execute or imply a real bank transfer. | services | `services/processing.py` | CFR-IAA-03 |
| AFR-IAA-018 | retain processed financial records for subsequent audit review. | services | `services/processing.py` | CFR-IAA-03 |
| AFR-IAA-019 | determine the required approval route using configured request amount, request type, department, and hierarchy rules. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-020 | HoD, Dean, and Director shall be represented as distinct approval authorities and assigned according to the configured route. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-021 | allow the assigned Approving Authority to review a routed request. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-022 | allow the assigned Approving Authority to approve a routed request with recorded remarks. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-023 | allow the assigned Approving Authority to reject a routed request with recorded remarks. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-024 | prevent a request creator from approving that same request. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-025 | When another approval level is required, an approved request shall remain pending and be routed to the next configured eligible authority. | services | `services/decisions.py + domain/routing.py` | CFR-IAA-04 |
| AFR-IAA-026 | A pending approval that exceeds its configured action time limit shall be escalated automatically. | services | `services/decisions.py::escalate_overdue + schedule.py` | CFR-IAA-05 |
| AFR-IAA-027 | An escalated approval shall be routed to the next eligible configured authority. | services | `services/decisions.py::escalate_overdue + schedule.py` | CFR-IAA-05 |
| AFR-IAA-028 | allow the assigned higher/next authority to review and resolve an escalated request by approval or rejection. | services | `services/decisions.py::escalate_overdue + schedule.py` | CFR-IAA-05 |
| AFR-IAA-029 | During Finance validation, the system shall compare the applicable request/claim amount with available departmental budget. | services | `services/review.py + services/budget.py` | CFR-IAA-06 |
| AFR-IAA-030 | Budget insufficiency shall be flagged for configured review/escalation rather than automatically causing rejection. | services | `services/review.py + services/budget.py` | CFR-IAA-06 |
| AFR-IAA-031 | allow Finance Staff to flag a material anomaly or policy violation. | services | `services/anomalies.py` | CFR-IAA-07 |
| AFR-IAA-032 | allow an Auditor to flag a material anomaly or policy violation. | services | `services/anomalies.py` | CFR-IAA-07 |
| AFR-IAA-033 | automatically create an anomaly record for configured material anomaly conditions. | services | `services/anomalies.py` | CFR-IAA-07 |
| AFR-IAA-034 | track each anomaly from Open until it is Resolved or Escalated. | services | `services/anomalies.py` | CFR-IAA-07 |
| AFR-IAA-035 | allow the designated anomaly resolver to record a resolution or escalation outcome. | services | `services/anomalies.py` | CFR-IAA-07 |
| AFR-IAA-036 | allow an eligible employee to submit a TA claim. | services | `services/records.py::create_ta` | CFR-IAA-08 |
| AFR-IAA-037 | capture TA trip dates, purpose, claimed amount, and other required trip details. | services | `services/records.py::create_ta` | CFR-IAA-08 |
| AFR-IAA-038 | allow the employee to attach required TA supporting documents. | services | `services/records.py::create_ta` | CFR-IAA-08 |
| AFR-IAA-039 | block TA submission when mandatory TA fields or required documents are missing. | services | `services/records.py::create_ta` | CFR-IAA-08 |
| AFR-IAA-040 | allow Finance Staff to verify a submitted TA claim for policy compliance. | services | `services/review.py` | CFR-IAA-09 |
| AFR-IAA-041 | validate a submitted TA claim against applicable available departmental budget. | services | `services/review.py` | CFR-IAA-09 |
| AFR-IAA-042 | allow Finance Staff to request clarification/evidence on a TA claim and the claimant to respond. | services | `services/review.py` | CFR-IAA-09 |
| AFR-IAA-043 | A TA claim requiring high-value approval shall be routed through the configured approval route. | services | `services/decisions.py` | CFR-IAA-10 |
| AFR-IAA-044 | allow the assigned Approving Authority to approve or reject a high-value TA claim with remarks. | services | `services/decisions.py` | CFR-IAA-10 |
| AFR-IAA-045 | A TA claimant shall not approve their own TA claim. | services | `services/decisions.py` | CFR-IAA-10 |
| AFR-IAA-046 | allow Finance Staff to internally process and record a verified/approved TA claim. | services | `services/processing.py` | CFR-IAA-11 |
| AFR-IAA-047 | A processed and recorded TA claim shall become read-only and reach its terminal recorded state. | services | `services/processing.py` | CFR-IAA-11 |
| AFR-IAA-048 | allow Auditors to review completed and in-process financial records within authorized scope. | services | `services/observations.py + selectors` | CFR-IAA-12 |
| AFR-IAA-049 | allow an Auditor to raise an audit observation linked to a relevant financial record or process. | services | `services/observations.py + selectors` | CFR-IAA-12 |
| AFR-IAA-050 | A newly raised audit observation shall enter Open state. | services | `services/observations.py + selectors` | CFR-IAA-12 |
| AFR-IAA-051 | allow the concerned user/department to submit corrective-action response information for an Open observation. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-052 | allow supporting evidence to be attached to an audit-observation response. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-053 | A submitted audit-observation response shall move the observation to Responded state. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-054 | allow the Auditor to verify the response, corrective action, and supporting evidence. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-055 | An audit observation shall be closable only after Auditor verification of the response and evidence. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-056 | If the response is unsatisfactory, the observation shall return from Responded to Open for another response cycle. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-057 | Audit observations shall not be deleted in a way that removes their recorded history. | services | `services/observations.py` | CFR-IAA-13 |
| AFR-IAA-058 | provide authorized users a read-only dashboard/report of request status summaries. | services | `services/reports.py` | CFR-IAA-14 |
| AFR-IAA-059 | provide approval turnaround-time information to authorized reporting users. | services | `services/reports.py` | CFR-IAA-14 |
| AFR-IAA-060 | provide authorized reporting users information on flagged anomalies and audit observations. | services | `services/reports.py` | CFR-IAA-14 |
| AFR-IAA-061 | allow authorized reporting users to export a read-only report for offline reference. | services | `services/reports.py` | CFR-IAA-14 |
| AFR-IAA-062 | allow a Basic User to track the status/history of their own expense/voucher requests and TA claims. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-063 | notify relevant actors of request/claim submission and status changes. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-064 | notify relevant actors of approval, rejection, and escalation events. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-065 | notify relevant actors of anomaly and audit-observation events. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-066 | notify relevant actors of pending actions and overdue follow-ups. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-067 | make IAA notifications visible through the Fusion dashboard. | services | `selectors/notifications.py + services/notify.py` | CFR-IAA-15 |
| AFR-IAA-068 | allow System Admin to assign and manage IAA roles. | services | `services/configuration.py` | CFR-IAA-16 |
| AFR-IAA-069 | allow System Admin to configure approval hierarchy and threshold/routing parameters. | services | `services/configuration.py` | CFR-IAA-16 |
| AFR-IAA-070 | allow System Admin to configure financial years and policy parameters. | services | `services/configuration.py` | CFR-IAA-16 |
| AFR-IAA-071 | System Admin shall not be permitted to access operational financial request content or perform operational approvals. | services | `services/configuration.py` | CFR-IAA-16 |
| AFR-IAA-072 | require a multi-role user to explicitly switch/activate the role used for a role-specific action. | services | `selectors/scoping.py + TrailEntry.actor_role` | CFR-IAA-17 |
| AFR-IAA-073 | Role changes shall not alter historical records or the recorded identity/role of completed actions. | services | `selectors/scoping.py + TrailEntry.actor_role` | CFR-IAA-17 |
| AFR-IAA-074 | enforce role-based access control across all IAA features and data views. | services | `selectors/scoping.py + TrailEntry.actor_role` | CFR-IAA-17 |
| AFR-IAA-075 | log IAA actions with user identity, active role, timestamp, action, and resulting status where applicable. | services | `services/trail.py` | CFR-IAA-18 |


## (b) Domain model

| Entity | Key fields | Invariants (DB unless marked) |
|---|---|---|
| `FinancialYear` | code, starts_on, ends_on | unique code; `ends_on > starts_on` (Check) |
| `PolicyVersion` | effective_from, approval_timeout_hours, ta_high_value_threshold, budget_check_required, request_types, required_documents, routes, anomaly_resolvers, created_by, created_role | timeout > 0, threshold ≥ 0 (Check); JSON shape validated in `domain/policy.py`; no update path |
| `BudgetEntry` | financial_year, department, kind (allocation / adjustment / commitment), amount (signed), record?, note, created_by | append-only (save refuses update); commitment amount < 0 (Check); one commitment per record (partial unique) |
| `FinancialRecord` | kind (expense / ta), user_id, department, request_type, title, description, amount, trip_start, trip_end, purpose, status, financial_year?, route_levels, escalation_designation, current_level, submitted_at, processing_note | amount > 0 (Check); TA ⇒ trip dates and `trip_end ≥ trip_start` (Check); status in the state table |
| `SupportingDocument` | record, title, link, added_by | https link (validator) |
| `ClarificationQuery` | record, question, raised_by/role, response, responded_by, responded_at | one unanswered query per record (partial unique) |
| `ApprovalStep` | record, level, designation, status (pending / approved / rejected / escalated / rerouted), assigned_at, escalated, decided_by/role/at, remarks | one pending step per record (partial unique); a decided step carries remarks (Check) |
| `Anomaly` | record?, category, source (manual / automatic), description, status, resolver_chain, resolver_level, raised_by/role, resolved_by/role/at, resolution | one unresolved automatic anomaly per record + category (partial unique) |
| `AuditObservation` | record?, respondent_user_id, title, detail, status, cycle, raised_by | no delete path; PROTECT FKs (BR-301) |
| `ObservationResponse` | observation, cycle, corrective_action, evidence_link, responded_by, verdict, reviewed_by/at, review_remarks | unique (observation, cycle) |
| `TrailEntry` | entity, entity_id, action, from_status, to_status, actor_user_id?, actor_role, remarks | append-only, never deleted (BR-503) |
| `Notification` | recipient_user_id?, recipient_role, kind, message, entity, entity_id | exactly one of user / role set (Check) |

## (c) State machines — `domain/state_machine.py`

Declarative tables keyed by `(kind, from_state, event)`; an absent key is an illegal move.

**Financial record** (CW-IAA-01, CW-IAA-02):

| Kind | From | Event | Actor | To | Ids |
|---|---|---|---|---|---|
| expense | — | create | owner | draft | UC-101 |
| expense | draft | submit | owner | submitted | UC-102, BR-101 |
| both | submitted, query_responded | raise_query | finance | query_raised | UC-103, UC-402 |
| both | query_raised | respond_query | owner | query_responded | UC-104 |
| expense | submitted, query_responded | validate | finance | finance_validated | UC-103, BR-102 |
| ta | — | create | owner | submitted | UC-401, BR-101 |
| ta | submitted, query_responded | verify | finance | verified | UC-402, BR-201 |
| ta | submitted, query_responded | verify_for_approval | finance | approval_pending | UC-402, BR-202 |
| ta | submitted, query_responded | reject_policy | finance | rejected | UC-402, BR-201 |
| expense | finance_validated, approval_pending, escalated | approve_level | approver | approval_pending | UC-201/202, BR-002 |
| ta | approval_pending, escalated | approve_level | approver | approval_pending | UC-403/202 |
| expense | finance_validated, approval_pending, escalated | approve_final | approver | approved | UC-201/202 |
| ta | approval_pending, escalated | approve_final | approver | approved | UC-403/202 |
| expense | finance_validated, approval_pending, escalated | reject | approver | rejected | UC-201/202, BR-005 |
| ta | approval_pending, escalated | reject | approver | rejected | UC-403/202, BR-005 |
| expense | finance_validated, approval_pending | escalate | system | escalated | UC-203, BR-401 |
| ta | approval_pending | escalate | system | escalated | UC-203, BR-401 |
| expense | approved | record | finance | recorded | UC-105, BR-006 |
| ta | verified, approved | record | finance | recorded | UC-404, BR-006 |

Terminal: `rejected`, `recorded`.

**Anomaly** (CW-IAA-03): open →resolve→ resolved; open →escalate→ escalated; escalated →resolve→ resolved. Actor: the designation at `resolver_chain[resolver_level]`.

**Audit observation** (CW-IAA-04, BR-301/302): open →respond (respondent)→ responded; responded →close (auditor, satisfactory)→ closed; responded →return (auditor, unsatisfactory)→ open.

## (d) Permissions — `registry.py`

`MODULE = {"code": "iaa", ...}`; every permission is `iaa.<noun>.<verb>` from the closed verb list.

| Permission | Basic (faculty, staff) | Finance | HoD / Dean / Director | Auditor | System Admin |
|---|---|---|---|---|---|
| iaa.request.view | ✓ own | ✓ all | ✓ assigned | ✓ all | — |
| iaa.request.create | ✓ | | | | |
| iaa.clarification.update | ✓ own | | | | |
| iaa.request.review | | ✓ | | | |
| iaa.request.approve | | | ✓ | | |
| iaa.processing.create | | ✓ | | | |
| iaa.anomaly.view | | ✓ | ✓ assigned | ✓ | |
| iaa.anomaly.create | | ✓ | | ✓ | |
| iaa.anomaly.review | | ✓ | ✓ | ✓ | |
| iaa.observation.view | ✓ own | ✓ | | ✓ | |
| iaa.observation.create | | | | ✓ | |
| iaa.observation.update | ✓ own | | | | |
| iaa.observation.review | | | | ✓ | |
| iaa.report.view | | ✓ | ✓ | ✓ | |
| iaa.report.export | | ✓ | ✓ | ✓ | |
| iaa.notification.view | ✓ | ✓ | ✓ | ✓ | |
| iaa.configuration.view | | | | | ✓ |
| iaa.configuration.update | | | | | ✓ |

`SYSTEM_PERMISSIONS = ["iaa.approval.assign"]` — the overdue-escalation sweep (UC-203).

Designations (`ROLE_GRANTS` keys): `faculty`, `staff` (held by definition), `iaa_finance_staff`,
`iaa_hod`, `iaa_dean`, `iaa_director`, `iaa_auditor`, `iaa_system_admin` — Q1.

## (e) Endpoints — `/api/v1/iaa/`

Every endpoint: `HasModuleGrant("iaa")` then `HasPermission(...)`; rows from `selectors/scoping.py`.

| Method | Path | Permission | Ids |
|---|---|---|---|
| GET, POST | records | request.view / request.create | UC-101, UC-401, UC-603, UC-504 |
| GET, PATCH | records/{id} | request.view / request.create (draft only) | UC-101, BR-104 |
| POST | records/{id}/documents | request.create or clarification.update | BR-101 |
| POST | records/{id}/submit | request.create | UC-102, BR-101 |
| POST | records/{id}/query | request.review | UC-103, UC-402 |
| POST | records/{id}/query-response | clarification.update | UC-104 |
| POST | records/{id}/validate | request.review | UC-103, UC-402, BR-102, BR-201, BR-202 |
| POST | records/{id}/decision | request.approve | UC-201, UC-202, UC-403, BR-001, BR-005 |
| POST | records/{id}/processing | processing.create | UC-105, UC-404, BR-006 |
| GET | records/{id}/history | request.view | CFR-IAA-01, BR-503 |
| GET, POST | anomalies | anomaly.view / anomaly.create | UC-302 |
| POST | anomalies/{id}/resolve, anomalies/{id}/escalate | anomaly.review | UC-303 |
| GET, POST | observations | observation.view / observation.create | UC-501 |
| POST | observations/{id}/respond | observation.update | UC-502 |
| POST | observations/{id}/review | observation.review | UC-503, BR-302 |
| GET | reports/summary | report.view | UC-601 |
| GET | reports/export | report.export | UC-602 |
| GET | notifications | notification.view | UC-604, BR-504 |
| GET, POST | config/policies | configuration.view / update | UC-703, UC-704 |
| GET, POST | config/financial-years | configuration.view / update | UC-704 |
| GET, POST | config/budget-entries | configuration.view / update | BR-102 |

Client routes (each has a nav item; details open in a drawer):

| Route | Guard (`RequirePermission`) |
|---|---|
| /iaa/my-requests | iaa.request.create |
| /iaa/finance | iaa.request.review |
| /iaa/approvals | iaa.request.approve |
| /iaa/anomalies | iaa.anomaly.view |
| /iaa/observations | iaa.observation.view |
| /iaa/reports | iaa.report.view |
| /iaa/notifications | iaa.notification.view |
| /iaa/configuration | iaa.configuration.view |

`Fusion-client` sidebar entry (module-only, to hand over):
`{ id: "iaa", label: "Accounts & Audits", icon: "Calculator", to: "/iaa", section: "Finance" }`.

## (f) Contracts

`modules/iaa/contracts.py` exposes `get_open_item_counts(user_ids)` → per user, how many records and
audit observations are still open (for an exit/no-dues check). Needed from others: nothing new.

## (g) Scheduled work

| Beat entry | Cadence | If it does not run |
|---|---|---|
| `iaa.escalate-overdue-approvals` → `iaa.escalate_overdue_approvals` | every 10 min | an approver who never acts blocks the request forever (BR-401) |

`manage.py iaa_escalate_overdue` runs the same sweep by hand; `manage.py iaa_readiness` reports a missing policy / financial year / budget.

## (h) Open questions — need Student 2's written answer

1. **Designation names.** None of the six exists in `fusion-dev.dump`. Proposed: `iaa_finance_staff`, `iaa_hod`, `iaa_dean`, `iaa_director`, `iaa_auditor`, `iaa_system_admin`, provisioned with `assign_role`. In production should HoD/Dean/Director map to the ERP's existing posts instead?
2. **HoD department scope.** An `iaa_hod` step is visible only to an approver whose directory department equals the record's department. In the fixture departments may be empty, so an HoD may see nothing. Accept?
3. **UC-702 (role assignments) and UC-701 (switch role)** are the IAM's (`assign_role`, `set_active_role`). Not rebuilt here — known gap?
4. **Budget source.** Available budget = sum of the department's `BudgetEntry` rows for the financial year, entered by System Admin as configuration. No allocation counts as zero, which raises the automatic budget anomaly. Accept?
5. **Expense Finance rejection.** CW-IAA-01 gives Finance no reject; only clarification or validation. Built that way.
6. **Re-escalation.** An escalated item that goes overdue again is not escalated again (no table row). Accept?
7. **Automatic anomaly conditions.** Only budget insufficiency (BR-102) is automatic; no other condition is configured in the spec.
8. **Department representative** (UC-502). Responses come from the observation's respondent user only.
