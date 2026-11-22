# Complaints module blueprint

**Status:** Approved by the user in this conversation; CMS module implementation is complete on `module/complaints` with documented generic defaults. IAM-owned timed designation assignment remains an external integration handoff.
**Base commit:** `5595be6628b4cdc6f8b47cf74bac267a2470f780` (`origin/main`, 2026-11-15)
**Module:** Complaint Management System (CMS)
**Module code:** `complaints`
**Specification set:** `Specifications/01_CMS_Problem_Statement_v1.2_SYNCHRONIZED.docx` through `06_CMS_Traceability_Matrix_v1.3_FINAL.xlsx`
**Environment:** `module-only`
**Roles stated by the spec:** System Admin, User / Complainant, Complaint Handler, Complaint Supervisor. No additional actors are inferred.

## 3.1 (a) Traceability

The source documents remain authoritative for full statements. The table has one row per live AFR, UC, BR and workflow ID, with its planned enforcement location. CFR groupings follow the final RTM. `BR-CMS-042` is retired as a business rule and is excluded.

| ID | Requirement area | Layer / planned enforcement |
|---|---|---|
| AFR-CMS-001 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-002 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-003 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-004 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-005 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-006 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-007 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-008 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-009 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-010 | Submission and acceptance (see requirement registry) | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| AFR-CMS-011 | Assignment, category, priority (see requirement registry) | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| AFR-CMS-012 | Assignment, category, priority (see requirement registry) | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| AFR-CMS-013 | Assignment, category, priority (see requirement registry) | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| AFR-CMS-014 | Assignment, category, priority (see requirement registry) | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| AFR-CMS-015 | Assignment, category, priority (see requirement registry) | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| AFR-CMS-016 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-017 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-018 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-019 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-020 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-021 | Tracking and progress history (see requirement registry) | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| AFR-CMS-022 | Lifecycle outcomes (see requirement registry) | domain/state_machine transition table; services/outcomes; DB constraints |
| AFR-CMS-023 | Lifecycle outcomes (see requirement registry) | domain/state_machine transition table; services/outcomes; DB constraints |
| AFR-CMS-024 | Lifecycle outcomes (see requirement registry) | domain/state_machine transition table; services/outcomes; DB constraints |
| AFR-CMS-025 | Lifecycle outcomes (see requirement registry) | domain/state_machine transition table; services/outcomes; DB constraints |
| AFR-CMS-026 | Lifecycle outcomes (see requirement registry) | domain/state_machine transition table; services/outcomes; DB constraints |
| AFR-CMS-027 | Closure verification (see requirement registry) | models/Verification; domain transitions; services/closure; actor ownership checks |
| AFR-CMS-028 | Closure verification (see requirement registry) | models/Verification; domain transitions; services/closure; actor ownership checks |
| AFR-CMS-029 | Closure verification (see requirement registry) | models/Verification; domain transitions; services/closure; actor ownership checks |
| AFR-CMS-030 | Reopening (see requirement registry) | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| AFR-CMS-031 | Reopening (see requirement registry) | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| AFR-CMS-032 | Reopening (see requirement registry) | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| AFR-CMS-033 | Reopening (see requirement registry) | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| AFR-CMS-034 | Reopening (see requirement registry) | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| AFR-CMS-035 | Feedback (see requirement registry) | models/Feedback; feedback service and selectors |
| AFR-CMS-036 | Feedback (see requirement registry) | models/Feedback; feedback service and selectors |
| AFR-CMS-037 | Feedback (see requirement registry) | models/Feedback; feedback service and selectors |
| AFR-CMS-038 | Manual escalation (see requirement registry) | models/Escalation; domain eligibility; service; supervisor scoping |
| AFR-CMS-039 | Manual escalation (see requirement registry) | models/Escalation; domain eligibility; service; supervisor scoping |
| AFR-CMS-040 | Manual escalation (see requirement registry) | models/Escalation; domain eligibility; service; supervisor scoping |
| AFR-CMS-041 | SLA reminder and automatic escalation (see requirement registry) | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| AFR-CMS-042 | SLA reminder and automatic escalation (see requirement registry) | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| AFR-CMS-043 | SLA reminder and automatic escalation (see requirement registry) | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| AFR-CMS-044 | SLA reminder and automatic escalation (see requirement registry) | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| AFR-CMS-045 | SLA reminder and automatic escalation (see requirement registry) | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| AFR-CMS-046 | Announcements (see requirement registry) | models/Announcement; publish/view services; notification outbox |
| AFR-CMS-047 | Announcements (see requirement registry) | models/Announcement; publish/view services; notification outbox |
| AFR-CMS-048 | Announcements (see requirement registry) | models/Announcement; publish/view services; notification outbox |
| AFR-CMS-049 | Announcements (see requirement registry) | models/Announcement; publish/view services; notification outbox |
| AFR-CMS-050 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-051 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-052 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-053 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-054 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-055 | Reports and analytics visibility (see requirement registry) | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| AFR-CMS-056 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-057 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-058 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-059 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-060 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-061 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-062 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-063 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-064 | Notification triggering (see requirement registry) | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| AFR-CMS-065 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-066 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-067 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-068 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-069 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-070 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-071 | CMS role management (see requirement registry) | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| AFR-CMS-072 | Scope boundaries (see requirement registry) | architecture/import rules, API surface, no cross-module FK; negative acceptance checks |
| AFR-CMS-073 | Scope boundaries (see requirement registry) | architecture/import rules, API surface, no cross-module FK; negative acceptance checks |
| UC-CMS-001 | Submit Complaint | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| UC-CMS-002 | Track Submitted Complaint Status and History | selectors/scoping + read-only API |
| UC-CMS-003 | Review Assigned Complaints | selectors/scoping + read-only API |
| UC-CMS-004 | Assign, Categorize, and Prioritize Complaint | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-005 | Update Complaint Progress | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-006 | Resolve or Reject Complaint | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-007 | Verify Resolved Complaint for Closure (User / Complainant) | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-008 | Request Complaint Reopening | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-009 | Submit Feedback | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-010 | Review Submitted Feedback | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-011 | Manually Escalate Unresolved Complaint | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-012 | Monitor Escalated Complaints | selectors/scoping + read-only API |
| UC-CMS-013 | Publish Complaint-Related Announcement | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-014 | View Complaint-Related Announcements | selectors/scoping + read-only API |
| UC-CMS-015 | Generate Operational Complaint Reports | selectors/scoping + read-only API |
| UC-CMS-016 | View Complaint and Escalation Summaries | selectors/scoping + read-only API |
| UC-CMS-017 | View CMS Reports and Analytics | selectors/scoping + read-only API |
| UC-CMS-018 | Manage CMS Roles | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-019 | Verify Resolved Complaint for Closure (Complaint Supervisor) | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-020 | Review Complaint Reopening Request | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-021 | Trigger Pre-Breach SLA Reminder | domain/services + permissioned API; see matching AFR/BR enforcement |
| UC-CMS-022 | Automatically Escalate Complaint on SLA Breach | domain/services + permissioned API; see matching AFR/BR enforcement |
| BR-CMS-001 | Complaint Submission Availability | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-002 | Mandatory Complaint Fields | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-003 | Submission Timestamp Recording | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-004 | Attachment Acceptance Constraint | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-005 | Attachment Constraint Boundary | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-006 | Unique Complaint Identifier | models/Complaint + Attachment; domain submission validation; services/complaints.submit; API serializer; outbox |
| BR-CMS-007 | Manual Assignment Rule | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| BR-CMS-008 | Complaint Category/Type Rule | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| BR-CMS-009 | Priority Value Set | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| BR-CMS-010 | Assignment and Priority Downstream Use | models/Complaint; services/handling; domain validation; assignment selector, generic target: accountable employee |
| BR-CMS-011 | Complaint Status and Progress History | models/ComplaintHistory; selectors/scoping; services/progress; immutable history |
| BR-CMS-012 | Complaint Lifecycle State Set | domain/state_machine transition table; services/outcomes; DB constraints |
| BR-CMS-013 | Resolution Details Required | domain/state_machine transition table; services/outcomes; DB constraints |
| BR-CMS-014 | Rejection Details Required | domain/state_machine transition table; services/outcomes; DB constraints |
| BR-CMS-015 | Outcome and Status Notification Rule | domain/state_machine transition table; services/outcomes; DB constraints |
| BR-CMS-016 | Closure Verification Rule | models/Verification; domain transitions; services/closure; actor ownership checks |
| BR-CMS-017 | Closure Recording Rule | models/Verification; domain transitions; services/closure; actor ownership checks |
| BR-CMS-018 | Reopening Eligibility Rule | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| BR-CMS-019 | Reopening Review Ownership | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| BR-CMS-020 | Approved Reopening Status Rule | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| BR-CMS-021 | Reopening Outcome Recording | models/ReopeningRequest; services/reopen; supervisor review; approved requests return to In Progress by generic default |
| BR-CMS-022 | Feedback Eligibility Rule | models/Feedback; feedback service and selectors |
| BR-CMS-023 | Feedback Review Access Rule | models/Feedback; feedback service and selectors |
| BR-CMS-024 | Manual Escalation Eligibility | models/Escalation; domain eligibility; service; supervisor scoping |
| BR-CMS-025 | Escalation Status Tracking | models/Escalation; domain eligibility; service; supervisor scoping |
| BR-CMS-026 | Priority-SLA Association | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| BR-CMS-027 | SLA Duration Boundary | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| BR-CMS-028 | Pre-Breach Reminder Rule | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| BR-CMS-029 | Automatic SLA Escalation Rule | effective-dated policy; Celery schedule/task; idempotent services; configurable generic SLA values are set in platform settings |
| BR-CMS-030 | Announcement Publishing Authority | models/Announcement; publish/view services; notification outbox |
| BR-CMS-031 | Announcement Notification Configuration | models/Announcement; publish/view services; notification outbox |
| BR-CMS-032 | Reporting and Analytics Access Rule | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| BR-CMS-033 | Analytics Scope Boundary | selectors/aggregates and role-checked report endpoints; only spec-named measures |
| BR-CMS-034 | Notification Triggering Boundary | transactional outbox + delivery task; event triggers; provider delivery remains platform-configured |
| BR-CMS-035 | Time-Bound CMS Role Assignment | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| BR-CMS-036 | Mid-Cycle Role Reassignment | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| BR-CMS-037 | Active Role Cardinality | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| BR-CMS-038 | CMS Role Scope Boundary | IAM owns designation assignment; CMS declares grants and does not duplicate auth tables |
| BR-CMS-039 | Excluded Cross-Module Functions | architecture/import rules, API surface, no cross-module FK; negative acceptance checks |
| BR-CMS-040 | External Service/Department Complaint Boundary | architecture/import rules, API surface, no cross-module FK; negative acceptance checks |
| BR-CMS-041 | External Policy Boundary | architecture/import rules, API surface, no cross-module FK; negative acceptance checks |
| BW-CMS-01 | Complaint Intake to Resolved | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-02 | Complaint Intake to User-Verified Closure | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-03 | Complaint Intake to Supervisor-Verified Closure | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-04 | Complaint Intake to Rejection | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-05 | Reopening Request Denied | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-06 | Reopening Request Approved | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-07 | Manual Escalation of Unresolved Complaint | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| BW-CMS-08 | Automatic SLA Escalation | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| CW-CMS-01 | Complaint Intake-to-Outcome Lifecycle | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| CW-CMS-02 | Complaint Reopening Decision | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |
| CW-CMS-03 | Complaint Escalation Paths | domain/state_machine + transactional services; STT guards and results mapped to the source workflow |

## 3.2 (b) Domain model

All business tables live in the platform database. Every person reference is an integer `user_id`, never a foreign key to IAM/ERP. No authentication, role, permission, or module-access table is proposed. Time-stamped records use the project mixins. Exact fields and indexes are refined after open decisions are settled.

- **Complaint:** UUID public reference, complainant `user_id`, submitted category, description, lifecycle state, submitted/updated timestamps, optional priority and accountable handler assignment, recorded during manual handling setup, and outcome details. Database checks constrain priority and state values.
- **ComplaintAttachment:** complaint FK, opaque random storage key, detected content type, byte count, digest, uploader `user_id`, timestamp. Store outside the repository using the project private-file facilities; never store client filenames as paths. Attachment limits and scan policy must be configured; no unsupported limits are invented.
- **ComplaintHistory:** complaint FK, actor `user_id`, event, prior/result state where applicable, progress text, timestamp. Append-only in services; transition/audit rows are not edited in place.
- **ClosureVerification:** complaint FK, verifier `user_id`, verifier kind, outcome and timestamp; unique successful verification per required path.
- **ReopeningRequest:** complaint FK, requester `user_id`, reason/dissatisfaction details, pending/approved/denied decision, reviewer `user_id`, timestamps. Approval returns the complaint to In Progress under the generic default.
- **Feedback:** complaint FK, complainant `user_id`, content/rating only where specified, timestamp; uniqueness and eligibility rules follow the exact feedback requirements.
- **Escalation:** complaint FK, manual/automatic source, actor or system marker, timestamp, reason when supplied. Idempotency constraint prevents duplicate automatic escalation for the same SLA breach. Escalation stays orthogonal to lifecycle state as the workflow specification requires.
- **Announcement:** author `user_id`, content, publication window/state and timestamps.
- **NotificationOutbox:** recipient `user_id`, event type, complaint reference, delivery status/attempt count and timestamps. Written in the same transaction as the triggering business event; delivery is retried asynchronously.
- **CMS policy defaults:** SLA and attachment values are configurable platform settings, with generic values documented in section 3.8. IAM continues to own timed designation assignments.

DB-level uniqueness/checks enforce UUID references, priority/state enums, one feedback item per complainant per complaint, one pending reopening request, one escalation per complaint/source, outbox idempotency, and per-user idempotency keys. Exactly-one active Handler/Supervisor role assignment is IAM-owned and is not stored in this module; role grants are published through the permission manifest.

## 3.3 (c) State machine

A declarative transition table will be the only source of lifecycle changes. Workflow STTs are authoritative. Current known transitions:

| Current state | Event | Actor | Result | Spec basis / caveat |
|---|---|---|---|---|
| No record | submit valid complaint | User / Complainant | Submitted | UC-001; BR-001–006 |
| Submitted | assign handler / record progress | Complaint Handler | In Progress | Generic default for ISS-CMS-007: assignment starts work; an unassigned record stays Submitted |
| Active unresolved | resolve with details | Complaint Handler | Resolved | UC-006; BR-012–013 |
| Active unresolved | reject with reason | Complaint Handler | Rejected | UC-006; BR-012, 014 |
| Resolved | successful required user verification | User / Complainant | Closed | UC-007; BR-016–017 |
| Resolved | successful required supervisor verification | Complaint Supervisor | Closed | UC-019; BR-016–017 |
| Closed | request reopening | User / Complainant | Closed + pending request | UC-008; BR-018 |
| Closed + pending request | deny reopening | Complaint Supervisor | Closed + denial recorded | UC-020; BR-019, 021 |
| Closed + pending request | approve reopening | Complaint Supervisor | In Progress | Generic default for ISS-CMS-008; clears prior resolution fields and starts a new SLA window |
| Active unresolved, not escalated | manual escalation | Complaint Handler | lifecycle unchanged; escalation recorded | UC-011; BR-024–025 |
| Active unresolved, SLA breached | automatic escalation | System | lifecycle unchanged; escalation recorded | UC-022; BR-025–029 |

Generic default for ISS-CMS-010: closure verification is required. When disabled by deployment policy, resolving a complaint closes it automatically and records both events. Illegal/unsupported transitions fail in the domain service and are backed by database constraints where representable.

## 3.4 (d) Permissions and role grants

Permission codes registered in the module manifest:

- `complaints.complaint.create`, `complaints.complaint.view`, `complaints.complaint.review`, `complaints.complaint.assign`, `complaints.complaint.update`, `complaints.complaint.approve`
- `complaints.feedback.create`, `complaints.feedback.review`
- `complaints.announcement.view`, `complaints.announcement.publish`
- `complaints.report.view`
- `complaints.cms_role.assign` only if a supported IAM-owned assignment integration is approved

Scope is enforced in selectors and services, not permissions alone: complainants see only their own complaints and feedback; handlers see complaints assigned to them; supervisors see escalated complaints and reopening requests and the summaries the spec permits; admins see only the specified reports/analytics. Out-of-scope object IDs return 404. No scheduled job uses a human permission; any system-only permission must be declared separately.

Generic role mapping: basic `student`, `faculty`, and `staff` kinds receive complainant permissions; the exact designations `System Admin`, `Complaint Handler`, and `Complaint Supervisor` receive the corresponding CMS grants. IAM remains authoritative for creating, time-limiting, and assigning those designations; CMS does not duplicate identity role assignments. The Complaint Handler manually sets complaint-to-handler assignment, category/type, and priority.

## 3.5 (e) API and navigation

Candidate routes under `/api/v1/complaints/`:

- `POST /complaints/`; `GET /complaints/` (selector scoped); `GET /complaints/{uuid}/`; attachment list/download via authenticated, scoped endpoints.
- Handler operations: assigned work queue, progress, resolve/reject, and manual escalation as separate action endpoints. Supervisors and admins have an active assignment queue.
- Complainant operations: status/history, closure verification when required, reopening request, feedback.
- Supervisor operations: escalation monitoring, closure verification, reopening decision, feedback review.
- Announcement list/detail and authorized publication.
- Reports/summaries/analytics endpoints restricted to the specified actors and measures.
- Role designation assignment remains in IAM; CMS never writes ERP or IAM tables directly.

Navigation belongs in the module registry and client module registry. A complainant sees submission, own complaints, announcements, and eligible feedback; handler, supervisor, and admin views are filtered by active-role permissions. Routes and menu labels are registered in the module manifests; role grants use the generic mapping documented above. No standalone sidebar is introduced.

## 3.6 (f) Cross-module contracts

No cross-module data dependency is needed for the baseline complaint lifecycle. `user_id` is an opaque integer from the authenticated principal. If display names or email addresses are required, use the directory contract and treat missing optional identity fields safely. No cross-module foreign keys, direct ERP access, or writes to `fusionlab` are allowed. Notification delivery uses the platform outbox/email configuration; the CMS owns trigger records, not central delivery infrastructure. IAM role assignment is a separate system boundary and remains managed by IAM.

## 3.7 (g) Time-driven behavior

Celery beat processes SLA deadlines every 15 minutes and pending notifications every minute. Jobs are bounded, idempotent, and safe under retries; state changes use transactions/row locks. Generic defaults use elapsed UTC hours from submission: Low 120 hours, Medium 72 hours, High 24 hours, with one reminder 24 hours before the deadline. Breaches create one SLA escalation in the supervisor queue. Values can be overridden with `CMS_SLA_LOW_HOURS`, `CMS_SLA_MEDIUM_HOURS`, `CMS_SLA_HIGH_HOURS`, and `CMS_SLA_REMINDER_HOURS`.

## 3.8 (h) Generic defaults for underspecified items

The user asked that gaps not answered by the specifications be implemented with generic values. These defaults are centralized/configurable where they affect policy:

1. **IAM role administration handoff:** the module registry maps `student`, `faculty`, and `staff` to complainant permissions and uses the specification’s exact designation labels for System Admin, Complaint Handler, and Complaint Supervisor. Platform guidance forbids a CMS-owned role table, and this checkout has no IAM role-assignment API. Therefore permission seeding and user role grants/removals must be done in the separate IAM tooling; the module does not implement the spec’s timed-role UI or enforce exactly-one active holder. See `docs/08-delivery/role-assignment-guide.md` for the supported IAM commands.
2. **ISS-CMS-007 and ISS-CMS-009:** the Complaint Handler manually assigns an active complaint to one accountable faculty/staff employee, sets category/type and Low/Medium/High priority, and starts it as In Progress. Reassignment is permitted while active. A complaint starts without an assigned priority; the SLA clock begins when the handler sets one.
3. **ISS-CMS-008:** approving reopening returns the complaint to In Progress, clears the old resolution/closure fields, preserves history, and restarts the SLA clock.
4. **ISS-CMS-010:** closure verification is required by default. A deployment may disable it; then resolve immediately closes and audits the complaint.
5. **SLA:** elapsed UTC time from submission, 120/72/24 hours for Low/Medium/High, a single reminder 24 hours before due, and an automatic escalation at breach. Configuration is in platform settings/environment variables.
6. **Attachments:** at most five files per complaint, 5 MiB per file, with PDF/JPEG/PNG signatures accepted. Files are stored outside the web root and served only through authenticated scope checks. The generic policy does not add a third-party malware scanning dependency; type signatures are validated server-side.
7. **Notifications:** event emails use the existing outbox and platform email backend; absent addresses become failed outbox entries. Published announcements are shown in the authenticated CMS feed. Bulk announcement email is off by default and can be enabled explicitly with `CMS_NOTIFY_ANNOUNCEMENTS=true`.
8. **Feedback and reporting:** one free-text feedback entry per complainant per complaint after resolution; reports expose complaint counts by status and escalation counts, both already supported by the specification.

These are defaults, not institution-approved policy. They can be changed without changing the domain structure. See `config/settings/base.py`, `modules/complaints/registry.py`, the CMS services/API, and the UI under `client/src/modules/complaints/`.
