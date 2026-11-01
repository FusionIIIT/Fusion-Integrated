# CMS supplied specification context


## Problem Statement v1.2
Fusion ERP — Complaint Management System
Problem Statement · v1.2 SYNCHRONIZED
| Metadata Field | Value |
| Project | Fusion ERP |
| Module | Complaint Management System (CMS) |
| Artifact | Problem Statement |
| Version | v1.2 |
| Date | 2026-08-22 |
| Status | SYNCHRONIZED — SOURCE SEMANTICS PRESERVED |
| Governing method | PS → FR → UC + BR → Basis WF → Composite WF → RTM; State-Transition Table authoritative |
Synchronization Note
The source Problem Statement is retained without semantic rewriting. Synchronization identified four explicit policy/transition clarifications (ISS-CMS-007 through ISS-CMS-010); they are documented in the Issue Register rather than silently resolved here.
1. Overview
The Complaint Management System (CMS) digitizes and streamlines institutional complaint handling within Fusion ERP.
The module supports complaint registration, complaint attachments, complaint categorization, manual assignment for operational handling, complaint tracking, SLA-based reminders, manual escalation, automatic SLA-based escalation, resolution, rejection, closure verification, complaint reopening, announcements, notifications, feedback, reporting, analytics visibility, and CMS role management.
The module is intended to improve transparency, correctness, accountability, timely communication, and auditable handling while reducing manual effort and paperwork.
CMS records and tracks complaint-handling information. Execution of remedial work by other institutional units remains outside CMS unless it is explicitly recorded in CMS as complaint progress, resolution, rejection, escalation, closure, reopening, feedback, announcement, notification, report, or role-management information.
2. Actors
2.1 System Admin
Assigns Complaint Handler and Complaint Supervisor roles to existing institutional users for a specified duration.
Performs mid-cycle reassignment of CMS-specific Complaint Handler and Complaint Supervisor roles when required.
Ensures that exactly one active Complaint Handler and one active Complaint Supervisor role-holder exist at a time within CMS.
Views complaint reports and analytics available within CMS.
Does not perform routine complaint registration, assignment, progress update, resolution, rejection, escalation handling, closure verification, reopening review, feedback review, or announcement publication.
2.2 User / Complainant
Registers complaints.
Provides complaint category, complaint description, and other mandatory complaint submission information.
Attaches supporting evidence when the complaint submission requires or allows attachments.
Tracks the status and history of the User / Complainant's submitted complaints.
Views complaint-related announcements.
Receives complaint-related notifications.
Verifies complaint resolution when the closure process requires User / Complainant verification.
Requests reopening of a closed complaint where dissatisfaction remains after closure.
Provides feedback after complaint resolution or closure.
2.3 Complaint Handler
Reviews complaints assigned for handling.
Manually assigns submitted complaints for operational handling.
Categorizes complaints by complaint category/type.
Assigns complaint priority as Low, Medium, or High.
Updates complaint progress during handling.
Resolves or rejects complaints with recorded details or reasons.
Initiates manual escalation where needed.
Publishes complaint-related announcements.
Reviews submitted feedback.
Generates operational complaint reports.
2.4 Complaint Supervisor
Provides supervisory oversight over complaint handling.
Monitors escalated complaints.
Reviews feedback and announcements.
Views complaint summaries, escalation summaries, and reports.
Verifies complaint resolution for closure when the closure process requires Supervisor verification.
Reviews complaint reopening requests.
Does not directly perform routine complaint resolution.
3. Functional Scope
3.1 Complaint Registration Management
Users / Complainants may submit complaints at any time.
Each complaint submission records at least complaint category, complaint description, and submission date/time.
Complaint submissions may include supporting attachments.
CMS validates mandatory complaint fields before accepting a complaint submission.
CMS validates accepted attachment constraints before accepting submitted attachments. The exact file-type, file-size, or attachment-format limits are treated as configurable or institutional constraints and are not specified in this problem statement.
CMS generates a unique complaint identifier for each submitted complaint.
CMS provides complaint submission confirmation or notification to the User / Complainant.
3.2 Complaint Assignment, Categorization, and Priority Management
Submitted complaints are manually assigned by the Complaint Handler for operational handling.
Complaints are categorized by complaint category/type.
Complaint priority is assigned as Low, Medium, or High.
Assignment and priority information are recorded by CMS and used for downstream complaint handling, reminders, and escalation.
3.3 Complaint Tracking and Progress Management
Users / Complainants can track complaint status and complaint history for their submitted complaints.
Complaint Handlers can review complaints assigned for handling.
Complaint Handlers can update complaint progress during processing.
CMS maintains complaint status and progress history throughout the lifecycle of each complaint.
3.4 Complaint Resolution, Rejection, and Closure Management
Complaint lifecycle states include Submitted, In Progress, Resolved, Rejected, and Closed.
Complaint resolution details are recorded for resolved complaints.
Rejection details or rejection reason information are recorded for rejected complaints.
Users / Complainants are notified of complaint outcome and status updates.
A resolved complaint may require verification by the User / Complainant or the Complaint Supervisor before closure, depending on the applicable closure process.
CMS records complaint closure after successful verification when verification is required.
3.5 Complaint Reopening Management
Users / Complainants may request reopening of a closed complaint where dissatisfaction remains after closure.
The Complaint Supervisor reviews complaint reopening requests.
If reopening is approved, CMS reopens the complaint and updates its status accordingly.
CMS records the outcome of the reopening request.
3.6 Feedback Management
Users / Complainants may submit feedback after complaint resolution or closure.
Complaint Handlers and Complaint Supervisors can review submitted feedback.
3.7 Escalation and SLA Management
Complaints that remain unresolved may be escalated manually.
CMS tracks escalation status.
Complaint Supervisors monitor escalated complaints.
Complaint priority is associated with applicable SLA timelines. The exact SLA duration values are not specified in this problem statement.
CMS sends reminder notifications when a complaint approaches the applicable SLA breach condition.
If a complaint is not resolved within the applicable SLA timeline, CMS automatically escalates it.
3.8 Announcements
Complaint Handlers or Complaint Supervisors may publish complaint-related announcements.
Users / Complainants can view complaint-related announcements.
Users / Complainants receive announcement-related notifications where CMS is configured to notify them about such announcements.
3.9 Reports and Analytics
Complaint Handlers generate operational complaint reports.
Complaint Supervisors view complaint summaries and escalation summaries.
System Admin views complaint reports and analytics available within CMS.
This scope does not introduce unsupported analytics beyond complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS.
3.10 Notifications
CMS triggers email notifications for complaint submission, complaint status updates, complaint resolution, complaint rejection, complaint escalation, complaint reopening outcomes where applicable, feedback-related events where applicable, and complaint-related announcements.
CMS notification triggering is within module scope. Central email delivery infrastructure and platform-level notification infrastructure are outside CMS scope unless explicitly represented as CMS notification records or events.
3.11 Role Management
System Admin assigns Complaint Handler and Complaint Supervisor roles for specified duration.
Role reassignment is allowed mid-cycle.
Exactly one active Complaint Handler and one active Complaint Supervisor role-holder exist at a time within CMS.
CMS role assignment is limited to CMS-specific operational and supervisory roles. HR master-data management, payroll, employment records, and platform-wide user-account administration are outside CMS scope.
3.12 Scope Boundaries
CMS does not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration.
Complaints may refer to services or departments outside CMS, but CMS scope is limited to recording, assigning, tracking, escalating, resolving/rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information.
External institutional policies, manuals, guidelines, and departmental processes are outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them.
The System is not treated as a regular primary actor in use cases derived later from this problem statement. System behavior appears as internal validation, state update, notification, escalation, postcondition, maintained data, or reporting behavior.

## Two-Level Requirement Registry v1.3 (CFR & AFR)
Fusion ERP — Complaint Management System
Two-Level Requirement Registry · v1.3 FINAL
| Field | Content |
| Project | Fusion ERP |
| Module | Complaint Management System (CMS) |
| Artifact | Two-Level Requirement Registry (CFR + AFR) |
| Version | v1.3 |
| Date | 2026-08-30 |
| Status | FINAL SYNCHRONIZED — OPEN DOMAIN CLARIFICATIONS EXPLICIT |
| Governing method | PS → CFR/AFR → UC + BR → Basis WF → Composite WF → RTM; event-triggered UCs permitted; STT authoritative |
Registry Method and Historical Continuity
The v1.2 atomic registry is preserved as historical continuity evidence. Final AFR-CMS-001 through AFR-CMS-073 retain the wording of historical CMS-FR-001 through CMS-FR-073 one-to-one, but are grouped beneath coherent CFR obligations. Historical CMS-FR-074 is not promoted to an AFR because it is a specification-modeling convention rather than a business/system requirement; its disposition is retained in the historical crosswalk.
Level 1 — Coherent / Consolidated Requirements (CFR)
| CFR ID | Name | CFR Statement | Semantic Profile | Source | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) |
CFR-CMS-001 Complaint Submission and Acceptance: CMS shall support complete complaint submission by a User / Complainant, validate mandatory submission data and applicable attachment constraints, record required submission data, assign a unique complaint identifier, and confirm successful acceptance.
CFR-CMS-002 Complaint Handling Setup: CMS shall allow the Complaint Handler to establish operational handling information for submitted complaints by manual assignment, categorization, and Low/Medium/High priority assignment, and shall record the resulting assignment and priority information.
CFR-CMS-003 Complaint Tracking and Progress History: CMS shall support complainant tracking and handler review/progress update while maintaining complaint status and progress history throughout the complaint lifecycle.
CFR-CMS-004 Complaint Lifecycle Outcome Management: CMS shall manage the defined complaint lifecycle and allow the Complaint Handler to resolve or reject a complaint with required outcome details while recording and communicating supported outcome/status changes.
CFR-CMS-005 Closure Verification: CMS shall support the applicable User / Complainant or Complaint Supervisor verification path for a resolved complaint and record closure after successful verification when verification is required.
CFR-CMS-006 Complaint Reopening: CMS shall allow a dissatisfied User / Complainant to request reopening of a closed complaint, allow the Complaint Supervisor to decide the request, and record the reopening decision and supported resulting complaint state information.
CFR-CMS-007 Feedback Management: CMS shall allow Users / Complainants to submit feedback after resolution or closure and allow Complaint Handlers and Complaint Supervisors to review submitted feedback.
CFR-CMS-008 Manual Escalation and Oversight: CMS shall support manual escalation of unresolved complaints, maintain escalation status, and allow Complaint Supervisors to monitor escalated complaints.
CFR-CMS-009 SLA-Driven Reminder and Automatic Escalation: CMS shall associate complaint priority with applicable SLA timelines, trigger a reminder when an unresolved complaint approaches the applicable SLA breach condition, and automatically escalate an unresolved complaint when the applicable SLA is breached, without hard-coding unspecified SLA durations into the baseline.
CFR-CMS-010 Complaint Announcements: CMS shall allow authorized Complaint Handlers and Complaint Supervisors to publish complaint-related announcements, allow Users / Complainants to view them, and trigger configured announcement notifications.
CFR-CMS-011 Complaint Reporting and Analytics Visibility: CMS shall provide the complaint reports, summaries, escalation summaries, and analytics visibility specified for Complaint Handlers, Complaint Supervisors, and System Admin, without introducing unsupported analytics scope.
CFR-CMS-012 Notification Triggering: CMS shall trigger the specified complaint-related email notification events while limiting CMS responsibility to notification triggering rather than central email-delivery or platform-level notification infrastructure.
CFR-CMS-013 CMS Role Management: CMS shall allow System Admin to assign and reassign the CMS-specific Complaint Handler and Complaint Supervisor roles for specified durations while enforcing exactly one active holder of each role and excluding HR/platform account administration.
CFR-CMS-014 CMS Functional Scope Boundaries: CMS shall confine Complaint Management functionality to the accepted complaint-handling scope and shall not implement excluded cross-module functions or unstated external institutional policies/processes.
Level 2 — Atomic Requirements (AFR): Core Specification
| AFR ID | Parent CFR | AFR Statement | Historical ID | Source | Decomposition / Atomicity Rationale | Verification / Acceptance Focus |
AFR-CMS-001 (CFR-CMS-001): CMS shall allow a User / Complainant to submit a complaint at any time.
AFR-CMS-002 (CFR-CMS-001): CMS shall record the complaint category for each submitted complaint.
AFR-CMS-003 (CFR-CMS-001): CMS shall record the complaint description for each submitted complaint.
AFR-CMS-004 (CFR-CMS-001): CMS shall record the submission date/time for each submitted complaint.
AFR-CMS-005 (CFR-CMS-001): CMS shall allow complaint submissions to include supporting attachments.
AFR-CMS-006 (CFR-CMS-001): CMS shall validate mandatory complaint fields before accepting a complaint submission.
AFR-CMS-007 (CFR-CMS-001): CMS shall validate accepted attachment constraints before accepting submitted attachments.
AFR-CMS-008 (CFR-CMS-001): CMS shall treat the exact attachment file-type, file-size, and format limits as configurable or institutional constraints outside the frozen problem-statement details.
AFR-CMS-009 (CFR-CMS-001): CMS shall generate a unique complaint identifier for each submitted complaint.
AFR-CMS-010 (CFR-CMS-001): CMS shall provide complaint submission confirmation or notification to the User / Complainant.
AFR-CMS-011 (CFR-CMS-002): CMS shall allow the Complaint Handler to manually assign submitted complaints for operational handling.
AFR-CMS-012 (CFR-CMS-002): CMS shall allow the Complaint Handler to categorize complaints by complaint category/type.
AFR-CMS-013 (CFR-CMS-002): CMS shall allow the Complaint Handler to assign complaint priority as Low, Medium, or High.
AFR-CMS-014 (CFR-CMS-002): CMS shall record assignment information for downstream complaint handling, reminders, and escalation.
AFR-CMS-015 (CFR-CMS-002): CMS shall record priority information for downstream complaint handling, reminders, and escalation.
AFR-CMS-016 (CFR-CMS-003): CMS shall allow a User / Complainant to track the status of the User / Complainant's submitted complaints.
AFR-CMS-017 (CFR-CMS-003): CMS shall allow a User / Complainant to track the history of the User / Complainant's submitted complaints.
AFR-CMS-018 (CFR-CMS-003): CMS shall allow Complaint Handlers to review complaints assigned for handling.
AFR-CMS-019 (CFR-CMS-003): CMS shall allow Complaint Handlers to update complaint progress during processing.
AFR-CMS-020 (CFR-CMS-003): CMS shall maintain complaint status history throughout the lifecycle of each complaint.
AFR-CMS-021 (CFR-CMS-003): CMS shall maintain complaint progress history throughout the lifecycle of each complaint.
AFR-CMS-022 (CFR-CMS-004): CMS shall recognize Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states.
AFR-CMS-023 (CFR-CMS-004): CMS shall record complaint resolution details for resolved complaints.
AFR-CMS-024 (CFR-CMS-004): CMS shall record rejection details or rejection reason information for rejected complaints.
AFR-CMS-025 (CFR-CMS-004): CMS shall notify Users / Complainants of complaint outcome updates.
AFR-CMS-026 (CFR-CMS-004): CMS shall notify Users / Complainants of complaint status updates.
AFR-CMS-027 (CFR-CMS-005): CMS shall support User / Complainant verification of a resolved complaint when the applicable closure process requires such verification.
AFR-CMS-028 (CFR-CMS-005): CMS shall support Complaint Supervisor verification of a resolved complaint when the applicable closure process requires such verification.
AFR-CMS-029 (CFR-CMS-005): CMS shall record complaint closure after successful verification when verification is required.
AFR-CMS-030 (CFR-CMS-006): CMS shall allow Users / Complainants to request reopening of a closed complaint where dissatisfaction remains after closure.
AFR-CMS-031 (CFR-CMS-006): CMS shall allow the Complaint Supervisor to review complaint reopening requests.
AFR-CMS-032 (CFR-CMS-006): CMS shall reopen the complaint when a reopening request is approved.
AFR-CMS-033 (CFR-CMS-006): CMS shall update the complaint status accordingly when reopening is approved.
AFR-CMS-034 (CFR-CMS-006): CMS shall record the outcome of the complaint reopening request.
AFR-CMS-035 (CFR-CMS-007): CMS shall allow Users / Complainants to submit feedback after complaint resolution or closure.
AFR-CMS-036 (CFR-CMS-007): CMS shall allow Complaint Handlers to review submitted feedback.
AFR-CMS-037 (CFR-CMS-007): CMS shall allow Complaint Supervisors to review submitted feedback.
AFR-CMS-038 (CFR-CMS-008): CMS shall allow unresolved complaints to be escalated manually.
AFR-CMS-039 (CFR-CMS-008): CMS shall track escalation status.
AFR-CMS-040 (CFR-CMS-008): CMS shall allow Complaint Supervisors to monitor escalated complaints.
AFR-CMS-041 (CFR-CMS-009): CMS shall associate complaint priority with applicable SLA timelines.
AFR-CMS-042 (CFR-CMS-009): CMS shall not specify exact SLA duration values in the module baseline.
AFR-CMS-043 (CFR-CMS-009): CMS shall send reminder notifications when a complaint approaches the applicable SLA breach condition.
AFR-CMS-044 (CFR-CMS-009): CMS shall automatically escalate a complaint if it is not resolved within the applicable SLA timeline.
AFR-CMS-045 (CFR-CMS-010): CMS shall allow Complaint Handlers to publish complaint-related announcements.
AFR-CMS-046 (CFR-CMS-010): CMS shall allow Complaint Supervisors to publish complaint-related announcements.
AFR-CMS-047 (CFR-CMS-010): CMS shall allow Users / Complainants to view complaint-related announcements.
AFR-CMS-048 (CFR-CMS-010): CMS shall send announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements.
AFR-CMS-049 (CFR-CMS-011): CMS shall allow Complaint Handlers to generate operational complaint reports.
AFR-CMS-050 (CFR-CMS-011): CMS shall allow Complaint Supervisors to view complaint summaries.
AFR-CMS-051 (CFR-CMS-011): CMS shall allow Complaint Supervisors to view escalation summaries.
AFR-CMS-052 (CFR-CMS-011): CMS shall allow System Admin to view complaint reports available within CMS.
AFR-CMS-053 (CFR-CMS-011): CMS shall allow System Admin to view analytics available within CMS.
AFR-CMS-054 (CFR-CMS-011): CMS shall limit analytics scope to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS.
AFR-CMS-055 (CFR-CMS-012): CMS shall trigger email notifications for complaint submission events.
AFR-CMS-056 (CFR-CMS-012): CMS shall trigger email notifications for complaint status update events.
AFR-CMS-057 (CFR-CMS-012): CMS shall trigger email notifications for complaint resolution events.
AFR-CMS-058 (CFR-CMS-012): CMS shall trigger email notifications for complaint rejection events.
AFR-CMS-059 (CFR-CMS-012): CMS shall trigger email notifications for complaint escalation events.
AFR-CMS-060 (CFR-CMS-012): CMS shall trigger email notifications for complaint reopening outcome events where applicable.
AFR-CMS-061 (CFR-CMS-012): CMS shall trigger email notifications for feedback-related events where applicable.
AFR-CMS-062 (CFR-CMS-012): CMS shall trigger email notifications for complaint-related announcement events.
AFR-CMS-063 (CFR-CMS-012): CMS shall limit module responsibility to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events.
AFR-CMS-064 (CFR-CMS-013): CMS shall allow System Admin to assign the Complaint Handler role to an existing institutional user for a specified duration.
AFR-CMS-065 (CFR-CMS-013): CMS shall allow System Admin to assign the Complaint Supervisor role to an existing institutional user for a specified duration.
AFR-CMS-066 (CFR-CMS-013): CMS shall allow System Admin to reassign Complaint Handler and Complaint Supervisor roles mid-cycle.
AFR-CMS-067 (CFR-CMS-013): CMS shall enforce exactly one active Complaint Handler role-holder at a time within CMS.
AFR-CMS-068 (CFR-CMS-013): CMS shall enforce exactly one active Complaint Supervisor role-holder at a time within CMS.
AFR-CMS-069 (CFR-CMS-013): CMS role assignment shall be limited to CMS-specific operational and supervisory roles.
AFR-CMS-070 (CFR-CMS-013): CMS shall exclude HR master-data management, payroll, employment records, and platform-wide user-account administration from CMS role-management scope.
AFR-CMS-071 (CFR-CMS-014): CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration.
AFR-CMS-072 (CFR-CMS-014): CMS shall limit complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information.
AFR-CMS-073 (CFR-CMS-014): CMS shall treat external institutional policies, manuals, guidelines, and departmental processes as outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them.
AFR Traceability, Minimum Representation, and Disposition
| AFR ID | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Minimum Sufficient Representation | Coverage | UC Exact Location(s) |
Open Domain Clarifications Preserved
ISS-CMS-007 — In Progress is recognized but its entry transition is not defined.
ISS-CMS-008 — Approved reopening requires a status update but the exact resulting lifecycle state is not defined.
ISS-CMS-009 — Manual assignment target/ownership semantics are not defined beyond operational handling assignment.
ISS-CMS-010 — Closure behavior when verification is not required is not defined.

## Use Case Specifications v1.3
Fusion ERP — Complaint Management System
Use Case Specifications · v1.3 FINAL
| Metadata Field | Value |
| Project | Fusion ERP |
| Module | Complaint Management System (CMS) |
| Artifact | Use Case Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Status | FINAL SYNCHRONIZED — OPEN DOMAIN CLARIFICATIONS EXPLICIT |
| Governing method | Actor-triggered and event-triggered UCs; System is not its own UC actor; STT authoritative for workflow behavior |
Modeling Notes
Use cases model actor goals or meaningful event-triggered system services. The system under specification is not its own UC actor. For event-triggered UCs, Primary Actor is “N.A. — Event-triggered” and the time/SLA event is stated in Trigger. UC-CMS-012 now contains only the Complaint Supervisor monitoring goal; SLA reminder and automatic escalation are represented separately as UC-CMS-021 and UC-CMS-022. Informational UCs remain outside workflows unless they themselves cause a meaningful persistent state change.
| UC ID | Use Case Name | UC Type | Primary Actor | Related CFRs / AFRs | Related BRs | Related Workflow(s) |
| UC-CMS-001 | Submit Complaint | Actor-triggered | User / Complainant |  | BR-CMS-001; BR-CMS-002; BR-CMS-003; BR-CMS-004; BR-CMS-005; BR-CMS-006; BR-CMS-034 | CW-CMS-01 r1; BW-CMS-01/02/03/04 r1 |
| UC-CMS-002 | Track Submitted Complaint Status and History | Actor-triggered | User / Complainant |  | BR-CMS-011 | N/A |
| UC-CMS-003 | Review Assigned Complaints | Actor-triggered | Complaint Handler |  | N/A | N/A |
| UC-CMS-004 | Assign, Categorize, and Prioritize Complaint | Actor-triggered | Complaint Handler |  | BR-CMS-007; BR-CMS-008; BR-CMS-009; BR-CMS-010 | CW-CMS-01 r2; BW-CMS-01/02/03/04 r2 |
| UC-CMS-005 | Update Complaint Progress | Actor-triggered | Complaint Handler |  | BR-CMS-011; BR-CMS-015; BR-CMS-034 | CW-CMS-01 r3; BW-CMS-01/02/03/04 r3 (zero or one traversal) |
| UC-CMS-006 | Resolve or Reject Complaint | Actor-triggered | Complaint Handler |  | BR-CMS-012; BR-CMS-013; BR-CMS-014; BR-CMS-015; BR-CMS-034 | CW-CMS-01 r4-r5; BW-CMS-01/02/03/04 outcome row |
| UC-CMS-007 | Verify Resolved Complaint for Closure (User / Complainant) | Actor-triggered | User / Complainant |  | BR-CMS-016; BR-CMS-017 | CW-CMS-01 r6; BW-CMS-02 r5 |
| UC-CMS-008 | Request Complaint Reopening | Actor-triggered | User / Complainant |  | BR-CMS-018 | CW-CMS-02 r1; BW-CMS-05/06 r1 |
| UC-CMS-009 | Submit Feedback | Actor-triggered | User / Complainant |  | BR-CMS-022; BR-CMS-034 | N/A |
| UC-CMS-010 | Review Submitted Feedback | Actor-triggered | Complaint Handler or Complaint Supervisor |  | BR-CMS-023 | N/A |
| UC-CMS-011 | Manually Escalate Unresolved Complaint | Actor-triggered | Complaint Handler |  | BR-CMS-024; BR-CMS-025; BR-CMS-034 | CW-CMS-03 r1; BW-CMS-07 r1 |
| UC-CMS-012 | Monitor Escalated Complaints | Actor-triggered | Complaint Supervisor |  | N/A | N/A |
| UC-CMS-013 | Publish Complaint-Related Announcement | Actor-triggered | Complaint Handler or Complaint Supervisor |  | BR-CMS-030; BR-CMS-031; BR-CMS-034 | N/A |
| UC-CMS-014 | View Complaint-Related Announcements | Actor-triggered | User / Complainant |  | N/A | N/A |
| UC-CMS-015 | Generate Operational Complaint Reports | Actor-triggered | Complaint Handler |  | BR-CMS-032 | N/A |
| UC-CMS-016 | View Complaint and Escalation Summaries | Actor-triggered | Complaint Supervisor |  | BR-CMS-032 | N/A |
| UC-CMS-017 | View CMS Reports and Analytics | Actor-triggered | System Admin |  | BR-CMS-032; BR-CMS-033 | N/A |
| UC-CMS-018 | Manage CMS Roles | Actor-triggered | System Admin |  | BR-CMS-035; BR-CMS-036; BR-CMS-037; BR-CMS-038 | N/A — state-changing but single-actor administrative support; no cross-actor workflow progression is established. |
| UC-CMS-019 | Verify Resolved Complaint for Closure (Complaint Supervisor) | Actor-triggered | Complaint Supervisor |  | BR-CMS-016; BR-CMS-017 | CW-CMS-01 r7; BW-CMS-03 r5 |
| UC-CMS-020 | Review Complaint Reopening Request | Actor-triggered | Complaint Supervisor |  | BR-CMS-019; BR-CMS-020; BR-CMS-021; BR-CMS-034 | CW-CMS-02 r2-r3; BW-CMS-05/06 r2 |
| UC-CMS-021 | Trigger Pre-Breach SLA Reminder | Event-triggered | N.A. — Event-triggered |  | BR-CMS-026; BR-CMS-027; BR-CMS-028; BR-CMS-034 | N/A — reminder is non-state-changing. |
| UC-CMS-022 | Automatically Escalate Complaint on SLA Breach | Event-triggered | N.A. — Event-triggered |  | BR-CMS-025; BR-CMS-026; BR-CMS-027; BR-CMS-029; BR-CMS-034 | BW-CMS-08 r1; CW-CMS-03 r2 |
UC-CMS-001 — Submit Complaint
| Primary Actor | User / Complainant |
| Goal / Description | Submit a complaint with required details and optional supporting attachments. |
| Trigger | User / Complainant chooses to submit a complaint. |
| Preconditions | User / Complainant is an authorized CMS user; mandatory fields and attachment constraints are available to CMS. |
| Main Success Scenario | 1. User / Complainant opens the complaint submission function. | 2. Enters complaint category/type, complaint description, and other mandatory complaint information. | 3. Attaches supporting evidence if applicable. | 4. CMS validates mandatory complaint fields. | 5. CMS validates accepted attachment constraints. | 6. CMS accepts the submission, records submission date/time, and generates a unique complaint identifier. | 7. CMS provides submission confirmation and triggers the complaint-submission email notification event. |
| Alternative Flows | - If mandatory fields are incomplete, CMS does not accept the submission and asks the User / Complainant to correct the submission. | - If an attachment violates accepted constraints, CMS does not accept the attachment until corrected or removed. |
| Success Postcondition | Complaint is registered with identifier, category/type, description, submission date/time, and submission confirmation/notification event recorded. |
| Related Business Rules | BR-CMS-001; BR-CMS-002; BR-CMS-003; BR-CMS-004; BR-CMS-005; BR-CMS-006; BR-CMS-034 |
| Related Workflow(s) | CW-CMS-01 r1; BW-CMS-01/02/03/04 r1 |
UC-CMS-002 — Track Submitted Complaint Status and History
| Primary Actor | User / Complainant |
| Goal / Description | View the status and history of the User / Complainant's submitted complaints. |
| Trigger | User / Complainant chooses to check complaint status or history. |
| Preconditions | At least one complaint submitted by the User / Complainant exists in CMS. |
| Main Success Scenario | 1. User / Complainant opens complaint tracking. | 2. CMS lists the User / Complainant's submitted complaints. | 3. User / Complainant selects a complaint. | 4. CMS displays current complaint status and complaint history for the selected complaint. |
| Alternative Flows | - If no submitted complaint exists, CMS shows that there is no complaint history for the User / Complainant. |
| Success Postcondition | User / Complainant has viewed status/history information; no lifecycle state is changed. |
| Related Business Rules | BR-CMS-011 |
| Related Workflow(s) | N/A |
UC-CMS-003 — Review Assigned Complaints
| Primary Actor | Complaint Handler |
| Goal / Description | Review complaints assigned for handling. |
| Trigger | Complaint Handler accesses assigned complaint worklist. |
| Preconditions | Complaint Handler role is active and assigned complaints exist or may exist. |
| Main Success Scenario | 1. Complaint Handler opens assigned complaints list. | 2. CMS displays complaints assigned for handling. | 3. Complaint Handler reviews complaint details, status, history, assignment, priority, and available attachments where present. |
| Alternative Flows | - If no assigned complaints exist, CMS shows an empty assigned-complaint list. |
| Success Postcondition | Complaint Handler has reviewed assigned complaint information; no state change is required by this use case. |
| Related Business Rules | N/A |
| Related Workflow(s) | N/A |
UC-CMS-004 — Assign, Categorize, and Prioritize Complaint
| Primary Actor | Complaint Handler |
| Goal / Description | Manually assign submitted complaints for operational handling, categorize them, and assign priority. |
| Trigger | Complaint Handler selects a submitted complaint for operational handling setup. |
| Preconditions | A submitted complaint exists and the Complaint Handler role is active. |
| Main Success Scenario | 1. Complaint Handler selects a submitted complaint. | 2. Complaint Handler manually assigns the complaint for operational handling. | 3. Complaint Handler categorizes the complaint by complaint category/type. | 4. Complaint Handler assigns priority as Low, Medium, or High. | 5. CMS records assignment and priority information for downstream handling, reminders, and escalation. |
| Alternative Flows | - If required assignment, category/type, or priority information is not supplied, CMS keeps the complaint from completing this operation until corrected. |
| Success Postcondition | Complaint has assignment, category/type, and priority information recorded for handling, reminders, and escalation. |
| Related Business Rules | BR-CMS-007; BR-CMS-008; BR-CMS-009; BR-CMS-010 |
| Related Workflow(s) | CW-CMS-01 r2; BW-CMS-01/02/03/04 r2 |
UC-CMS-005 — Update Complaint Progress
| Primary Actor | Complaint Handler |
| Goal / Description | Record progress updates while a complaint is being processed. |
| Trigger | Complaint Handler needs to update complaint progress. |
| Preconditions | Complaint is assigned for handling and is within the complaint lifecycle. |
| Main Success Scenario | 1. Complaint Handler opens the complaint. | 2. Complaint Handler enters a progress update. | 3. CMS records the progress update and maintains progress history. | 4. CMS triggers a status-update notification only where an independently supported status update event applies. |
| Alternative Flows | - If the progress update is incomplete or invalid for the current state, CMS does not record the update until corrected. |
| Success Postcondition | Complaint progress history is updated. No generic lifecycle-state change is inferred from a progress entry. |
| Related Business Rules | BR-CMS-011; BR-CMS-015; BR-CMS-034 |
| Related Workflow(s) | CW-CMS-01 r3; BW-CMS-01/02/03/04 r3 (zero or one traversal) |
UC-CMS-006 — Resolve or Reject Complaint
| Primary Actor | Complaint Handler |
| Goal / Description | Record resolution or rejection details and update complaint outcome. |
| Trigger | Complaint Handler completes handling decision for a complaint. |
| Preconditions | Complaint is assigned for handling and is not already closed. |
| Main Success Scenario | 1. Complaint Handler opens the complaint. | 2. Selects Resolution or Rejection. | 3. For Resolution, records resolution details. | 4. For Rejection, records rejection details/reason. | 5. CMS updates status to Resolved or Rejected according to the supported outcome. | 6. CMS records the outcome/status update and triggers the corresponding resolution or rejection email notification event. |
| Alternative Flows | - If resolution details are missing for a resolved complaint, CMS does not mark the complaint Resolved. | - If rejection details or reason information are missing for a rejected complaint, CMS does not mark the complaint Rejected. |
| Success Postcondition | Complaint outcome and status are recorded; User / Complainant is notified. |
| Related Business Rules | BR-CMS-012; BR-CMS-013; BR-CMS-014; BR-CMS-015; BR-CMS-034 |
| Related Workflow(s) | CW-CMS-01 r4-r5; BW-CMS-01/02/03/04 outcome row |
UC-CMS-007 — Verify Resolved Complaint for Closure (User / Complainant)
| Primary Actor | User / Complainant |
| Goal / Description | Verify a resolved complaint when the applicable closure process requires User / Complainant verification, enabling CMS to record closure. |
| Trigger | A complaint is Resolved and the applicable closure process requires User / Complainant verification. |
| Preconditions | Complaint is Resolved; applicable closure process identifies User / Complainant verification. |
| Main Success Scenario | 1. User / Complainant opens the resolved complaint. | 2. Reviews resolution details. | 3. Records successful verification. | 4. CMS records closure and updates status to Closed. |
| Alternative Flows | If verification is not recorded/successful, CMS does not close the complaint under this verification-required path. |
| Success Postcondition | Resolved complaint is Closed after successful required User / Complainant verification. |
| Related Business Rules | BR-CMS-016; BR-CMS-017 |
| Related Workflow(s) | CW-CMS-01 r6; BW-CMS-02 r5 |
UC-CMS-008 — Request Complaint Reopening
| Primary Actor | User / Complainant |
| Goal / Description | Request reopening of a closed complaint where dissatisfaction remains after closure. |
| Trigger | User / Complainant remains dissatisfied after complaint closure. |
| Preconditions | Complaint is Closed and belongs to the User / Complainant. |
| Main Success Scenario | 1. User / Complainant opens the closed complaint. | 2. Submits a reopening request. | 3. CMS records the reopening request and makes it available for Complaint Supervisor review. |
| Alternative Flows | If the complaint is not Closed, CMS does not process the action as a reopening request. |
| Success Postcondition | A reopening request is recorded while the complaint remains Closed pending review. |
| Related Business Rules | BR-CMS-018 |
| Related Workflow(s) | CW-CMS-02 r1; BW-CMS-05/06 r1 |
UC-CMS-009 — Submit Feedback
| Primary Actor | User / Complainant |
| Goal / Description | Submit feedback after complaint resolution or closure. |
| Trigger | User / Complainant chooses to submit feedback. |
| Preconditions | Complaint is resolved or closed. |
| Main Success Scenario | 1. User / Complainant opens feedback submission. | 2. Enters feedback. | 3. CMS records feedback for authorized review. | 4. CMS triggers a feedback-related email notification event where applicable. |
| Alternative Flows | - If the complaint is neither resolved nor closed, CMS does not treat the feedback as post-resolution/closure feedback. |
| Success Postcondition | Feedback is stored and available to authorized reviewers. |
| Related Business Rules | BR-CMS-022; BR-CMS-034 |
| Related Workflow(s) | N/A |
UC-CMS-010 — Review Submitted Feedback
| Primary Actor | Complaint Handler or Complaint Supervisor |
| Goal / Description | Review feedback submitted by Users / Complainants. |
| Trigger | Complaint Handler or Complaint Supervisor opens submitted feedback. |
| Preconditions | Submitted feedback exists. |
| Main Success Scenario | 1. Actor opens feedback review function. | 2. CMS displays submitted feedback. | 3. Actor reviews feedback content. |
| Alternative Flows | - If no feedback exists, CMS shows an empty feedback list. |
| Success Postcondition | Feedback is reviewed; no complaint lifecycle transition is implied. |
| Related Business Rules | BR-CMS-023 |
| Related Workflow(s) | N/A |
UC-CMS-011 — Manually Escalate Unresolved Complaint
| Primary Actor | Complaint Handler |
| Goal / Description | Escalate an unresolved complaint manually when needed. |
| Trigger | Complaint Handler determines that an unresolved complaint requires escalation. |
| Preconditions | Complaint remains unresolved and is within active handling. |
| Main Success Scenario | 1. Complaint Handler opens an unresolved complaint. | 2. Initiates manual escalation. | 3. CMS records escalation status. | 4. CMS triggers the complaint-escalation email notification event. |
| Alternative Flows | - If the complaint is already resolved, rejected, or closed, CMS does not treat it as an unresolved complaint for manual escalation. |
| Success Postcondition | Complaint escalation status is recorded. |
| Related Business Rules | BR-CMS-024; BR-CMS-025; BR-CMS-034 |
| Related Workflow(s) | CW-CMS-03 r1; BW-CMS-07 r1 |
UC-CMS-012 — Monitor Escalated Complaints
| Primary Actor | Complaint Supervisor |
| Goal / Description | Monitor complaints that have been escalated and view their recorded escalation status. |
| Trigger | Complaint Supervisor opens the escalated-complaint monitoring view. |
| Preconditions | One or more complaints may have recorded escalation status; Complaint Supervisor role is active. |
| Main Success Scenario | 1. Complaint Supervisor opens escalated-complaint monitoring. | 2. CMS displays escalated complaints and their recorded escalation status. | 3. Complaint Supervisor reviews the displayed escalation information. |
| Alternative Flows | - If no escalated complaints exist, CMS shows no escalated complaint entries. |
| Success Postcondition | Complaint Supervisor has reviewed escalated complaint information; no complaint lifecycle or escalation state is changed by this use case. |
| Related Business Rules | N/A |
| Related Workflow(s) | N/A |
UC-CMS-013 — Publish Complaint-Related Announcement
| Primary Actor | Complaint Handler or Complaint Supervisor |
| Goal / Description | Publish a complaint-related announcement. |
| Trigger | Authorized actor chooses to publish a complaint-related announcement. |
| Preconditions | Actor is an active Complaint Handler or Complaint Supervisor. |
| Main Success Scenario | 1. Authorized Complaint Handler or Complaint Supervisor opens announcement publishing. | 2. Enters complaint-related announcement content. | 3. CMS publishes the announcement. | 4. CMS triggers the announcement-related email notification event where CMS is configured to notify Users / Complainants. |
| Alternative Flows | - If actor is not Complaint Handler or Complaint Supervisor, CMS does not allow announcement publication. |
| Success Postcondition | Announcement is published and notification may be triggered according to CMS configuration. |
| Related Business Rules | BR-CMS-030; BR-CMS-031; BR-CMS-034 |
| Related Workflow(s) | N/A |
UC-CMS-014 — View Complaint-Related Announcements
| Primary Actor | User / Complainant |
| Goal / Description | View complaint-related announcements. |
| Trigger | User / Complainant opens announcements. |
| Preconditions | User / Complainant has access to CMS. |
| Main Success Scenario | 1. User / Complainant opens announcement view. | 2. CMS displays complaint-related announcements. |
| Alternative Flows | - If no announcement exists, CMS shows no announcement entries. |
| Success Postcondition | User / Complainant has viewed announcements. |
| Related Business Rules | N/A |
| Related Workflow(s) | N/A |
UC-CMS-015 — Generate Operational Complaint Reports
| Primary Actor | Complaint Handler |
| Goal / Description | Generate operational complaint reports. |
| Trigger | Complaint Handler requests an operational complaint report. |
| Preconditions | Complaint Handler role is active. |
| Main Success Scenario | 1. Complaint Handler opens reporting function. | 2. Complaint Handler selects operational report parameters available within CMS. | 3. CMS generates the operational complaint report. |
| Alternative Flows | - If no data matches selected parameters, CMS generates an empty/no-data result. |
| Success Postcondition | Operational complaint report is available to Complaint Handler. |
| Related Business Rules | BR-CMS-032 |
| Related Workflow(s) | N/A |
UC-CMS-016 — View Complaint and Escalation Summaries
| Primary Actor | Complaint Supervisor |
| Goal / Description | View complaint summaries and escalation summaries. |
| Trigger | Complaint Supervisor opens summary/report view. |
| Preconditions | Complaint Supervisor role is active. |
| Main Success Scenario | 1. Complaint Supervisor opens complaint summary view. | 2. CMS displays complaint summaries. | 3. Complaint Supervisor opens escalation summary view. | 4. CMS displays escalation summaries. |
| Alternative Flows | - If no data exists, CMS displays empty/no-data summary. |
| Success Postcondition | Complaint Supervisor has viewed available summaries. |
| Related Business Rules | BR-CMS-032 |
| Related Workflow(s) | N/A |
UC-CMS-017 — View CMS Reports and Analytics
| Primary Actor | System Admin |
| Goal / Description | View complaint reports and analytics available within CMS without performing routine complaint operations. |
| Trigger | System Admin opens CMS reports or analytics view. |
| Preconditions | System Admin role is active. |
| Main Success Scenario | 1. System Admin opens CMS reporting/analytics view. | 2. CMS displays complaint reports available within CMS. | 3. CMS displays analytics available within CMS. |
| Alternative Flows | - If analytics/report data is unavailable, CMS displays empty/no-data result. |
| Success Postcondition | System Admin has viewed reports/analytics available within CMS; no routine complaint operation is performed. |
| Related Business Rules | BR-CMS-032; BR-CMS-033 |
| Related Workflow(s) | N/A |
UC-CMS-018 — Manage CMS Roles
| Primary Actor | System Admin |
| Goal / Description | Assign or reassign Complaint Handler and Complaint Supervisor roles for specified duration. |
| Trigger | System Admin needs to assign or reassign CMS-specific roles. |
| Preconditions | Target institutional users exist outside CMS; CMS role-management function is available. |
| Main Success Scenario | 1. System Admin selects an existing institutional user for Complaint Handler role assignment and specified duration. | 2. System Admin selects an existing institutional user for Complaint Supervisor role assignment and specified duration. | 3. System Admin performs mid-cycle reassignment when required. | 4. CMS enforces exactly one active Complaint Handler and exactly one active Complaint Supervisor role-holder at a time within CMS. |
| Alternative Flows | - If assignment would violate active-role cardinality, CMS does not complete the role assignment until corrected. |
| Success Postcondition | CMS-specific Complaint Handler and Complaint Supervisor role assignments are recorded for specified duration. |
| Related Business Rules | BR-CMS-035; BR-CMS-036; BR-CMS-037; BR-CMS-038 |
| Related Workflow(s) | N/A — state-changing but single-actor administrative support; no cross-actor workflow progression is established. |
UC-CMS-019 — Verify Resolved Complaint for Closure (Complaint Supervisor)
| Primary Actor | Complaint Supervisor |
| Goal / Description | Verify a resolved complaint when the applicable closure process requires Complaint Supervisor verification, enabling CMS to record closure. |
| Trigger | A complaint is Resolved and the applicable closure process requires Complaint Supervisor verification. |
| Preconditions | Complaint is Resolved; applicable closure process identifies Complaint Supervisor verification. |
| Main Success Scenario | 1. Complaint Supervisor opens the resolved complaint. | 2. Reviews resolution details. | 3. Records successful verification. | 4. CMS records closure and updates status to Closed. |
| Alternative Flows | If verification is not recorded/successful, CMS does not close the complaint under this verification-required path. |
| Success Postcondition | Resolved complaint is Closed after successful required Complaint Supervisor verification. |
| Related Business Rules | BR-CMS-016; BR-CMS-017 |
| Related Workflow(s) | CW-CMS-01 r7; BW-CMS-03 r5 |
UC-CMS-020 — Review Complaint Reopening Request
| Primary Actor | Complaint Supervisor |
| Goal / Description | Review a recorded complaint reopening request and record an approval/denial outcome. |
| Trigger | A reopening request exists for a Closed complaint. |
| Preconditions | Complaint is Closed; a valid reopening request is recorded. |
| Main Success Scenario | 1. Complaint Supervisor opens the reopening request. | 2. Reviews the request. | 3. Records approval or denial. | 4. CMS records the reopening outcome. | 5. If approved, CMS reopens the complaint and updates status accordingly. | 6. CMS triggers the reopening-outcome email notification event where applicable. |
| Alternative Flows | If denied, the complaint remains Closed and the denial outcome is recorded. |
| Success Postcondition | Outcome is recorded; denied complaints remain Closed; approved complaints are reopened with status updated according to policy. |
| Related Business Rules | BR-CMS-019; BR-CMS-020; BR-CMS-021; BR-CMS-034 |
| Related Workflow(s) | CW-CMS-02 r2-r3; BW-CMS-05/06 r2 |
UC-CMS-021 — Trigger Pre-Breach SLA Reminder
| Primary Actor | N.A. — Event-triggered |
| Goal / Description | Trigger the configured reminder notification when an unresolved complaint approaches its applicable SLA breach condition. |
| Trigger | Time/SLA event: an unresolved complaint approaches the applicable externally configured SLA breach condition. |
| Preconditions | Complaint remains unresolved; complaint priority is associated with an applicable SLA timeline; applicable SLA values are available to CMS but are not specified in this baseline. |
| Main Success Scenario | 1. The configured time/SLA condition is reached for an unresolved complaint. | 2. CMS evaluates the complaint against its applicable priority-SLA association. | 3. CMS triggers the pre-breach reminder notification event. |
| Alternative Flows | - If the complaint is already resolved, no pre-breach reminder is triggered for that resolved complaint. |
| Success Postcondition | The reminder notification trigger has been issued; complaint lifecycle and escalation status are unchanged by this use case. |
| Related Business Rules | BR-CMS-026; BR-CMS-027; BR-CMS-028; BR-CMS-034 |
| Related Workflow(s) | N/A — reminder is non-state-changing. |
UC-CMS-022 — Automatically Escalate Complaint on SLA Breach
| Primary Actor | N.A. — Event-triggered |
| Goal / Description | Automatically escalate an unresolved complaint when its applicable SLA timeline is breached. |
| Trigger | Time/SLA event: the applicable SLA timeline is breached while the complaint remains unresolved. |
| Preconditions | Complaint remains unresolved; complaint priority is associated with an applicable SLA timeline; complaint has not already been escalated for the same active condition. |
| Main Success Scenario | 1. The applicable SLA breach condition occurs while the complaint remains unresolved. | 2. CMS evaluates the complaint against the applicable SLA condition. | 3. CMS records automatic escalation and updates escalation status. | 4. CMS triggers the complaint-escalation email notification event. |
| Alternative Flows | - If the complaint has been resolved before the breach condition is processed, automatic escalation is not performed. |
| Success Postcondition | Complaint escalation status records automatic escalation; the escalated complaint is available for Complaint Supervisor monitoring. |
| Related Business Rules | BR-CMS-025; BR-CMS-026; BR-CMS-027; BR-CMS-029; BR-CMS-034 |
| Related Workflow(s) | BW-CMS-08 r1; CW-CMS-03 r2 |

## Business Rule Specifications v1.3
Fusion ERP — Complaint Management System
Business Rule Specifications · v1.3 FINAL
| Metadata Field | Value |
| Project | Fusion ERP |
| Module | Complaint Management System (CMS) |
| Artifact | Business Rule Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Status | FINAL SYNCHRONIZED — OPEN DOMAIN CLARIFICATIONS EXPLICIT |
| Governing method | Reusable governing logic; references synchronized to CFR/AFR and event-triggered UC model |
Rule Registry
| BR ID | Name | Type | Status |
| BR-CMS-001 | Complaint Submission Availability | Availability | Active |
| BR-CMS-002 | Mandatory Complaint Fields | Validation | Active |
| BR-CMS-003 | Submission Timestamp Recording | Compliance Recording | Active |
| BR-CMS-004 | Attachment Acceptance Constraint | Validation | Active |
| BR-CMS-005 | Attachment Constraint Boundary | Scope Boundary | Active |
| BR-CMS-006 | Unique Complaint Identifier | Compliance Recording | Active |
| BR-CMS-007 | Manual Assignment Rule | Workflow Constraint | Active |
| BR-CMS-008 | Complaint Category/Type Rule | Data Rule | Active |
| BR-CMS-009 | Priority Value Set | Validation | Active |
| BR-CMS-010 | Assignment and Priority Downstream Use | Compliance Recording | Active |
| BR-CMS-011 | Complaint Status and Progress History | Compliance Recording | Active |
| BR-CMS-012 | Complaint Lifecycle State Set | State Constraint | Active |
| BR-CMS-013 | Resolution Details Required | Validation | Active |
| BR-CMS-014 | Rejection Details Required | Validation | Active |
| BR-CMS-015 | Outcome and Status Notification Rule | Notification Rule | Active |
| BR-CMS-016 | Closure Verification Rule | Workflow Constraint | Active |
| BR-CMS-017 | Closure Recording Rule | Compliance Recording | Active |
| BR-CMS-018 | Reopening Eligibility Rule | Eligibility | Active |
| BR-CMS-019 | Reopening Review Ownership | Permission | Active |
| BR-CMS-020 | Approved Reopening Status Rule | State Constraint | Active |
| BR-CMS-021 | Reopening Outcome Recording | Compliance Recording | Active |
| BR-CMS-022 | Feedback Eligibility Rule | Eligibility | Active |
| BR-CMS-023 | Feedback Review Access Rule | Access Rule | Active |
| BR-CMS-024 | Manual Escalation Eligibility | Workflow Constraint | Active |
| BR-CMS-025 | Escalation Status Tracking | Compliance Recording | Active |
| BR-CMS-026 | Priority-SLA Association | Constraint | Active |
| BR-CMS-027 | SLA Duration Boundary | Scope Boundary | Active |
| BR-CMS-028 | Pre-Breach Reminder Rule | Trigger | Active |
| BR-CMS-029 | Automatic SLA Escalation Rule | Trigger | Active |
| BR-CMS-030 | Announcement Publishing Authority | Permission | Active |
| BR-CMS-031 | Announcement Notification Configuration | Notification Rule | Active |
| BR-CMS-032 | Reporting and Analytics Access Rule | Access Rule | Active |
| BR-CMS-033 | Analytics Scope Boundary | Scope Boundary | Active |
| BR-CMS-034 | Notification Triggering Boundary | Scope Boundary | Active |
| BR-CMS-035 | Time-Bound CMS Role Assignment | Permission | Active |
| BR-CMS-036 | Mid-Cycle Role Reassignment | Permission | Active |
| BR-CMS-037 | Active Role Cardinality | Constraint | Active |
| BR-CMS-038 | CMS Role Scope Boundary | Scope Boundary | Active |
| BR-CMS-039 | Excluded Cross-Module Functions | Scope Boundary | Active |
| BR-CMS-040 | External Service/Department Complaint Boundary | Scope Boundary | Active |
| BR-CMS-041 | External Policy Boundary | Scope Boundary | Active |
| BR-CMS-042 | System Not Primary Actor Rule | Retired / Modeling Convention | Retired |
BR-CMS-001 — Complaint Submission Availability
Statement: CMS permits User / Complainant complaint submission at any time.
Related UCs: UC-CMS-001
BR-CMS-002 — Mandatory Complaint Fields
Statement: CMS shall not accept a complaint submission unless mandatory complaint fields, including complaint category/type and description, are present.
Related UCs: UC-CMS-001
BR-CMS-003 — Submission Timestamp Recording
Statement: CMS records submission date/time for each accepted complaint submission.
Related UCs: UC-CMS-001
BR-CMS-004 — Attachment Acceptance Constraint
Statement: CMS validates accepted attachment constraints before accepting submitted attachments.
Related UCs: UC-CMS-001
BR-CMS-005 — Attachment Constraint Boundary
Statement: Exact file-type, file-size, and format limits are configurable or institutional constraints outside the frozen problem-statement details.
Related UCs: UC-CMS-001
BR-CMS-006 — Unique Complaint Identifier
Statement: Each accepted complaint submission shall receive a unique complaint identifier.
Related UCs: UC-CMS-001
BR-CMS-007 — Manual Assignment Rule
Statement: Submitted complaints are manually assigned by Complaint Handler for operational handling; automatic initial assignment is outside the baseline.
Related UCs: UC-CMS-004
BR-CMS-008 — Complaint Category/Type Rule
Statement: Complaints are categorized by complaint category/type.
Related UCs: UC-CMS-004
BR-CMS-009 — Priority Value Set
Statement: Complaint priority shall be assigned only as Low, Medium, or High.
Related UCs: UC-CMS-004
BR-CMS-010 — Assignment and Priority Downstream Use
Statement: CMS records assignment and priority information for downstream complaint handling, reminders, and escalation.
Related UCs: UC-CMS-004
BR-CMS-011 — Complaint Status and Progress History
Statement: CMS maintains complaint status history and complaint progress history throughout the lifecycle of each complaint.
Related UCs: UC-CMS-002; UC-CMS-005
BR-CMS-012 — Complaint Lifecycle State Set
Statement: CMS recognizes Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states.
Related UCs: UC-CMS-005; UC-CMS-006; UC-CMS-007
BR-CMS-013 — Resolution Details Required
Statement: CMS records complaint resolution details for resolved complaints; a complaint shall not be represented as resolved without recorded resolution details.
Related UCs: UC-CMS-006
BR-CMS-014 — Rejection Details Required
Statement: CMS records rejection details or rejection reason information for rejected complaints.
Related UCs: UC-CMS-006
BR-CMS-015 — Outcome and Status Notification Rule
Statement: CMS notifies Users / Complainants of complaint outcome and status updates.
Related UCs: UC-CMS-005; UC-CMS-006
BR-CMS-016 — Closure Verification Rule
Statement: When the applicable closure process requires verification, CMS supports verification by the User / Complainant or Complaint Supervisor before closure.
Related UCs: UC-CMS-007; UC-CMS-019
BR-CMS-017 — Closure Recording Rule
Statement: CMS records complaint closure after successful verification when verification is required.
Related UCs: UC-CMS-007; UC-CMS-019
BR-CMS-018 — Reopening Eligibility Rule
Statement: Users / Complainants may request reopening only for a closed complaint where dissatisfaction remains after closure.
Related UCs: UC-CMS-008
BR-CMS-019 — Reopening Review Ownership
Statement: Complaint Supervisor reviews complaint reopening requests.
Related UCs: UC-CMS-020
BR-CMS-020 — Approved Reopening Status Rule
Statement: If a reopening request is approved, CMS reopens the complaint and updates its status accordingly.
Related UCs: UC-CMS-020
BR-CMS-021 — Reopening Outcome Recording
Statement: CMS records the outcome of each complaint reopening request.
Related UCs: UC-CMS-020
BR-CMS-022 — Feedback Eligibility Rule
Statement: Users / Complainants may submit feedback after complaint resolution or closure.
Related UCs: UC-CMS-009
BR-CMS-023 — Feedback Review Access Rule
Statement: Complaint Handlers and Complaint Supervisors can review submitted feedback.
Related UCs: UC-CMS-010
BR-CMS-024 — Manual Escalation Eligibility
Statement: Complaints that remain unresolved may be escalated manually.
Related UCs: UC-CMS-011
BR-CMS-025 — Escalation Status Tracking
Statement: CMS tracks escalation status.
Related UCs: UC-CMS-011; UC-CMS-022
BR-CMS-026 — Priority-SLA Association
Statement: Complaint priority is associated with applicable SLA timelines.
Related UCs: UC-CMS-021; UC-CMS-022
BR-CMS-027 — SLA Duration Boundary
Statement: CMS shall not specify exact SLA duration values in the module baseline.
Related UCs: UC-CMS-021; UC-CMS-022
BR-CMS-028 — Pre-Breach Reminder Rule
Statement: CMS sends reminder notifications when a complaint approaches the applicable SLA breach condition.
Related UCs: UC-CMS-021
BR-CMS-029 — Automatic SLA Escalation Rule
Statement: CMS automatically escalates a complaint if it is not resolved within the applicable SLA timeline.
Related UCs: UC-CMS-022
BR-CMS-030 — Announcement Publishing Authority
Statement: Only Complaint Handlers and Complaint Supervisors may publish complaint-related announcements.
Related UCs: UC-CMS-013
BR-CMS-031 — Announcement Notification Configuration
Statement: CMS sends announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements.
Related UCs: UC-CMS-013; UC-CMS-014
BR-CMS-032 — Reporting and Analytics Access Rule
Statement: Complaint Handler, Complaint Supervisor, and System Admin receive only the report/summary/analytics visibility specified for their roles.
Related UCs: UC-CMS-015; UC-CMS-016; UC-CMS-017
BR-CMS-033 — Analytics Scope Boundary
Statement: CMS analytics scope is limited to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS.
Related UCs: UC-CMS-017
BR-CMS-034 — Notification Triggering Boundary
Statement: CMS responsibility is limited to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events.
Related UCs: All notification-producing actor-triggered/event-triggered UCs
BR-CMS-035 — Time-Bound CMS Role Assignment
Statement: System Admin may assign Complaint Handler and Complaint Supervisor roles to existing institutional users for a specified duration.
Related UCs: UC-CMS-018
BR-CMS-036 — Mid-Cycle Role Reassignment
Statement: System Admin may reassign Complaint Handler and Complaint Supervisor roles mid-cycle.
Related UCs: UC-CMS-018
BR-CMS-037 — Active Role Cardinality
Statement: CMS enforces exactly one active Complaint Handler role-holder and exactly one active Complaint Supervisor role-holder at a time within CMS.
Related UCs: UC-CMS-018
BR-CMS-038 — CMS Role Scope Boundary
Statement: CMS role assignment is limited to CMS-specific operational and supervisory roles and excludes HR master-data management, payroll, employment records, and platform-wide user-account administration.
Related UCs: UC-CMS-018
BR-CMS-039 — Excluded Cross-Module Functions
Statement: CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration.
Related UCs: All artifacts
BR-CMS-040 — External Service/Department Complaint Boundary
Statement: CMS limits complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information.
Related UCs: Complaint lifecycle artifacts
BR-CMS-041 — External Policy Boundary
Statement: External institutional policies, manuals, guidelines, and departmental processes are outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them.
Related UCs: All artifacts
BR-CMS-042 — System Not Primary Actor Rule
Statement: Retired as a Business Rule. Modeling convention retained: the system under specification is not its own UC actor; meaningful automatic services may be event-triggered UCs with Primary Actor = N.A. — Event-triggered, and System may appear in a workflow STT Actor column only for autonomous state-changing transitions.
Related UCs: UC modeling notes; UC-CMS-021; UC-CMS-022

## Workflow Specifications v1.3
Fusion ERP — Complaint Management System
Workflow Specifications · v1.3 FINAL
| Metadata Field | Value |
| Project | Fusion ERP |
| Module | Complaint Management System (CMS) |
| Artifact | Workflow Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Status | FINAL SYNCHRONIZED — OPEN DOMAIN CLARIFICATIONS EXPLICIT |
| Governing method | Validated state-changing UCs + BRs → Basis WF → Composite WF; event triggers in Trigger/Guard; System allowed in STT Actor only for autonomous state change |
Workflow Construction Notes
The State-Transition Table (STT) is authoritative. Informational use cases are not added as workflow steps. UC-CMS-021 is event-triggered but non-state-changing and therefore remains outside the workflow STTs. UC-CMS-022 is event-triggered and state-changing; its automatic escalation transition is represented with Actor = System in BW-CMS-08 and CW-CMS-03. No Complete Workflow is forced because the three Composite Workflows communicate the major progressions more clearly.
| Workflow ID | Name | Type | Constituent Workflows | Primary Related CFRs |
| BW-CMS-01 | Complaint Intake to Resolved | Basis | N/A |  |
| BW-CMS-02 | Complaint Intake to User-Verified Closure | Basis | N/A |  |
| BW-CMS-03 | Complaint Intake to Supervisor-Verified Closure | Basis | N/A |  |
| BW-CMS-04 | Complaint Intake to Rejection | Basis | N/A |  |
| BW-CMS-05 | Reopening Request Denied | Basis | N/A |  |
| BW-CMS-06 | Reopening Request Approved | Basis | N/A |  |
| BW-CMS-07 | Manual Escalation of Unresolved Complaint | Basis | N/A |  |
| BW-CMS-08 | Automatic SLA Escalation | Basis | N/A |  |
| CW-CMS-01 | Complaint Intake-to-Outcome Lifecycle | Composite | BW-CMS-01; BW-CMS-02; BW-CMS-03; BW-CMS-04 |  |
| CW-CMS-02 | Complaint Reopening Decision | Composite | BW-CMS-05; BW-CMS-06 |  |
| CW-CMS-03 | Complaint Escalation Paths | Composite | BW-CMS-07; BW-CMS-08 |  |
BW-CMS-01 — Complaint Intake to Resolved
| Field | Content |
| Workflow ID | BW-CMS-01 |
| Workflow Name | Complaint Intake to Resolved |
| Type | Basis |
| Purpose / Scope | One finite path from complaint creation through handling setup to a Resolved outcome, without forcing closure. |
| Trigger | User / Complainant submits a complaint. |
| Participants | User / Complainant; Complaint Handler |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-001; UC-CMS-004; UC-CMS-005; UC-CMS-006 |
| Related BRs | BR-CMS-001; 002; 004; 005; 006; 007; 008; 009; 010; 011; 012; 013; 015; 034 |
| Notes / TODO | Progress-update loop is represented as zero traversal or one traversal. ISS-CMS-010 leaves non-verification closure unspecified. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | No registered complaint | User / Complainant | UC-CMS-001 — Submit Complaint | Mandatory fields valid; attachment constraints satisfied where supplied | Submitted | BR-CMS-001, 002, 004, 005, 006, 034 |
| 2 | Submitted | Complaint Handler | UC-CMS-004 — Assign, Categorize, and Prioritize Complaint | Supported handling setup completed; priority ∈ {Low, Medium, High} | Handling setup recorded (lifecycle status not changed by assumption) | BR-CMS-007, 008, 009, 010 |
| 3 | Handling setup recorded | Complaint Handler | UC-CMS-005 — Update Complaint Progress | Optional progress update; zero traversal or exactly one traversal represented | Progress history updated; exact entry transition to In Progress is unspecified | BR-CMS-011, 015, 034 |
| 4 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Resolve AND resolution details recorded | Resolved | BR-CMS-012, 013, 015, 034 |
BW-CMS-02 — Complaint Intake to User-Verified Closure
| Field | Content |
| Workflow ID | BW-CMS-02 |
| Workflow Name | Complaint Intake to User-Verified Closure |
| Type | Basis |
| Purpose / Scope | Resolved complaint path where the applicable closure process requires User / Complainant verification. |
| Trigger | User / Complainant submits a complaint. |
| Participants | User / Complainant; Complaint Handler |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-001; UC-CMS-004; UC-CMS-005; UC-CMS-006; UC-CMS-007 |
| Related BRs | BR-CMS-001; 002; 004; 005; 006; 007; 008; 009; 010; 011; 012; 013; 015; 016; 017; 034 |
| Notes / TODO |  |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | No registered complaint | User / Complainant | UC-CMS-001 — Submit Complaint | Mandatory fields valid; attachment constraints satisfied where supplied | Submitted | BR-CMS-001, 002, 004, 005, 006, 034 |
| 2 | Submitted | Complaint Handler | UC-CMS-004 — Assign, Categorize, and Prioritize Complaint | Supported handling setup completed; priority ∈ {Low, Medium, High} | Handling setup recorded (lifecycle status not changed by assumption) | BR-CMS-007, 008, 009, 010 |
| 3 | Handling setup recorded | Complaint Handler | UC-CMS-005 — Update Complaint Progress | Optional progress update; zero traversal or exactly one traversal represented | Progress history updated; exact entry transition to In Progress is unspecified | BR-CMS-011, 015, 034 |
| 4 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Resolve AND resolution details recorded | Resolved | BR-CMS-012, 013, 015, 034 |
| 5 | Resolved | User / Complainant | UC-CMS-007 — Verify Resolved Complaint for Closure | User verification required AND successful | Closed | BR-CMS-016, 017 |
BW-CMS-03 — Complaint Intake to Supervisor-Verified Closure
| Field | Content |
| Workflow ID | BW-CMS-03 |
| Workflow Name | Complaint Intake to Supervisor-Verified Closure |
| Type | Basis |
| Purpose / Scope | Resolved complaint path where the applicable closure process requires Complaint Supervisor verification. |
| Trigger | User / Complainant submits a complaint. |
| Participants | User / Complainant; Complaint Handler; Complaint Supervisor |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-001; UC-CMS-004; UC-CMS-005; UC-CMS-006; UC-CMS-019 |
| Related BRs | BR-CMS-001; 002; 004; 005; 006; 007; 008; 009; 010; 011; 012; 013; 015; 016; 017; 034 |
| Notes / TODO |  |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | No registered complaint | User / Complainant | UC-CMS-001 — Submit Complaint | Mandatory fields valid; attachment constraints satisfied where supplied | Submitted | BR-CMS-001, 002, 004, 005, 006, 034 |
| 2 | Submitted | Complaint Handler | UC-CMS-004 — Assign, Categorize, and Prioritize Complaint | Supported handling setup completed; priority ∈ {Low, Medium, High} | Handling setup recorded (lifecycle status not changed by assumption) | BR-CMS-007, 008, 009, 010 |
| 3 | Handling setup recorded | Complaint Handler | UC-CMS-005 — Update Complaint Progress | Optional progress update; zero traversal or exactly one traversal represented | Progress history updated; exact entry transition to In Progress is unspecified | BR-CMS-011, 015, 034 |
| 4 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Resolve AND resolution details recorded | Resolved | BR-CMS-012, 013, 015, 034 |
| 5 | Resolved | Complaint Supervisor | UC-CMS-019 — Verify Resolved Complaint for Closure | Supervisor verification required AND successful | Closed | BR-CMS-016, 017 |
BW-CMS-04 — Complaint Intake to Rejection
| Field | Content |
| Workflow ID | BW-CMS-04 |
| Workflow Name | Complaint Intake to Rejection |
| Type | Basis |
| Purpose / Scope | One finite path from complaint creation through handling setup to a Rejected outcome. |
| Trigger | User / Complainant submits a complaint. |
| Participants | User / Complainant; Complaint Handler |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-01 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-001; UC-CMS-004; UC-CMS-005; UC-CMS-006 |
| Related BRs | BR-CMS-001; 002; 004; 005; 006; 007; 008; 009; 010; 011; 012; 014; 015; 034 |
| Notes / TODO |  |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | No registered complaint | User / Complainant | UC-CMS-001 — Submit Complaint | Mandatory fields valid; attachment constraints satisfied where supplied | Submitted | BR-CMS-001, 002, 004, 005, 006, 034 |
| 2 | Submitted | Complaint Handler | UC-CMS-004 — Assign, Categorize, and Prioritize Complaint | Supported handling setup completed; priority ∈ {Low, Medium, High} | Handling setup recorded (lifecycle status not changed by assumption) | BR-CMS-007, 008, 009, 010 |
| 3 | Handling setup recorded | Complaint Handler | UC-CMS-005 — Update Complaint Progress | Optional progress update; zero traversal or exactly one traversal represented | Progress history updated; exact entry transition to In Progress is unspecified | BR-CMS-011, 015, 034 |
| 4 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Reject AND rejection details/reason recorded | Rejected | BR-CMS-012, 014, 015, 034 |
BW-CMS-05 — Reopening Request Denied
| Field | Content |
| Workflow ID | BW-CMS-05 |
| Workflow Name | Reopening Request Denied |
| Type | Basis |
| Purpose / Scope | Closed complaint reopening request reviewed and denied by Complaint Supervisor. |
| Trigger | Dissatisfied User / Complainant requests reopening of a Closed complaint. |
| Participants | User / Complainant; Complaint Supervisor |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-02 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-008; UC-CMS-020 |
| Related BRs | BR-CMS-018; 019; 021; 034 |
| Notes / TODO | Complaint lifecycle state remains Closed throughout denial path. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Closed | User / Complainant | UC-CMS-008 — Request Complaint Reopening | Complaint is Closed AND dissatisfaction remains | Closed + reopening request pending | BR-CMS-018 |
| 2 | Closed + reopening request pending | Complaint Supervisor | UC-CMS-020 — Review Complaint Reopening Request | Decision = Deny | Closed + denial outcome recorded | BR-CMS-019, 021, 034 |
BW-CMS-06 — Reopening Request Approved
| Field | Content |
| Workflow ID | BW-CMS-06 |
| Workflow Name | Reopening Request Approved |
| Type | Basis |
| Purpose / Scope | Closed complaint reopening request reviewed and approved by Complaint Supervisor. |
| Trigger | Dissatisfied User / Complainant requests reopening of a Closed complaint. |
| Participants | User / Complainant; Complaint Supervisor |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-02 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-008; UC-CMS-020 |
| Related BRs | BR-CMS-018; 019; 020; 021; 034 |
| Notes / TODO | The baseline does not define whether approved reopening returns to Submitted, In Progress, or another state. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Closed | User / Complainant | UC-CMS-008 — Request Complaint Reopening | Complaint is Closed AND dissatisfaction remains | Closed + reopening request pending | BR-CMS-018 |
| 2 | Closed + reopening request pending | Complaint Supervisor | UC-CMS-020 — Review Complaint Reopening Request | Decision = Approve | Reopened — exact lifecycle state unspecified (ISS-CMS-008) | BR-CMS-019, 020, 021, 034 |
BW-CMS-07 — Manual Escalation of Unresolved Complaint
| Field | Content |
| Workflow ID | BW-CMS-07 |
| Workflow Name | Manual Escalation of Unresolved Complaint |
| Type | Basis |
| Purpose / Scope | Record a manual escalation handoff for an unresolved active complaint. |
| Trigger | Complaint Handler determines that an unresolved complaint requires escalation. |
| Participants | Complaint Handler; Complaint Supervisor (downstream monitoring) |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-03 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-011 |
| Related BRs | BR-CMS-024; 025; 034 |
| Notes / TODO | Single transition retained because it is a meaningful cross-role escalation handoff in the larger escalation progression. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Active unresolved; not escalated | Complaint Handler | UC-CMS-011 — Manually Escalate Unresolved Complaint | Complaint remains unresolved and manual escalation is chosen | Escalated (manual); escalation status recorded | BR-CMS-024, 025, 034 |
BW-CMS-08 — Automatic SLA Escalation
| Field | Content |
| Workflow ID | BW-CMS-08 |
| Workflow Name | Automatic SLA Escalation |
| Type | Basis |
| Purpose / Scope | Record the autonomous escalation state change when an unresolved complaint breaches its applicable SLA timeline. |
| Trigger | Time/SLA event: applicable SLA timeline is breached while complaint remains unresolved. |
| Participants | System; Complaint Supervisor (downstream monitoring) |
| Constituent Workflows | N/A |
| Related Workflows | CW-CMS-03 |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-022 |
| Related BRs | BR-CMS-025; 026; 027; 029; 034 |
| Notes / TODO | System appears only in the authoritative STT actor column for this autonomous state-changing transition; the UC itself is event-triggered. UC-CMS-021 pre-breach reminder is non-state-changing and therefore outside the STT. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Active unresolved; SLA applicable; not escalated | System | UC-CMS-022 — Automatically Escalate Complaint on SLA Breach | Applicable SLA breached AND complaint remains unresolved | Escalated (automatic); escalation status recorded | BR-CMS-025, 026, 027, 029, 034 |
CW-CMS-01 — Complaint Intake-to-Outcome Lifecycle
| Field | Content |
| Workflow ID | CW-CMS-01 |
| Workflow Name | Complaint Intake-to-Outcome Lifecycle |
| Type | Composite |
| Purpose / Scope | Combine shared intake/handling with supported resolution, rejection, and verification branches. |
| Trigger | User / Complainant submits a complaint. |
| Participants | User / Complainant; Complaint Handler; Complaint Supervisor |
| Constituent Workflows | BW-CMS-01; BW-CMS-02; BW-CMS-03; BW-CMS-04 |
| Related Workflows | CW-CMS-02; CW-CMS-03 as contextually applicable |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-001; UC-CMS-004; UC-CMS-005; UC-CMS-006; UC-CMS-007; UC-CMS-019 |
| Related BRs | BR-CMS-001; 002; 004; 005; 006; 007; 008; 009; 010; 011; 012; 013; 014; 015; 016; 017; 034 |
| Notes / TODO | No non-verification closure is invented. Entry to In Progress remains unspecified (ISS-CMS-007). |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | No registered complaint | User / Complainant | UC-CMS-001 — Submit Complaint | Mandatory fields valid; attachment constraints satisfied where supplied | Submitted | BR-CMS-001, 002, 004, 005, 006, 034 |
| 2 | Submitted | Complaint Handler | UC-CMS-004 — Assign, Categorize, and Prioritize Complaint | Supported handling setup completed; priority ∈ {Low, Medium, High} | Handling setup recorded (lifecycle status not changed by assumption) | BR-CMS-007, 008, 009, 010 |
| 3 | Handling setup recorded | Complaint Handler | UC-CMS-005 — Update Complaint Progress | Optional progress update; zero traversal or exactly one traversal represented | Progress history updated; exact entry transition to In Progress is unspecified | BR-CMS-011, 015, 034 |
| 4 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Resolve AND resolution details recorded | Resolved | BR-CMS-012, 013, 015, 034 |
| 5 | Handling setup recorded / progress updated | Complaint Handler | UC-CMS-006 — Resolve or Reject Complaint | Outcome = Reject AND rejection details/reason recorded | Rejected | BR-CMS-012, 014, 015, 034 |
| 6 | Resolved | User / Complainant | UC-CMS-007 — Verify Resolved Complaint for Closure | User verification required AND successful | Closed | BR-CMS-016, 017 |
| 7 | Resolved | Complaint Supervisor | UC-CMS-019 — Verify Resolved Complaint for Closure | Supervisor verification required AND successful | Closed | BR-CMS-016, 017 |
CW-CMS-02 — Complaint Reopening Decision
| Field | Content |
| Workflow ID | CW-CMS-02 |
| Workflow Name | Complaint Reopening Decision |
| Type | Composite |
| Purpose / Scope | Combine approved and denied reopening paths after closure. |
| Trigger | User / Complainant requests reopening of a Closed complaint. |
| Participants | User / Complainant; Complaint Supervisor |
| Constituent Workflows | BW-CMS-05; BW-CMS-06 |
| Related Workflows | CW-CMS-01; CW-CMS-03 as contextually applicable |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-008; UC-CMS-020 |
| Related BRs | BR-CMS-018; 019; 020; 021; 034 |
| Notes / TODO | Approved resulting lifecycle label remains explicitly unspecified (ISS-CMS-008). |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Closed | User / Complainant | UC-CMS-008 — Request Complaint Reopening | Closed AND dissatisfaction remains | Closed + reopening request pending | BR-CMS-018 |
| 2 | Closed + reopening request pending | Complaint Supervisor | UC-CMS-020 — Review Complaint Reopening Request | Decision = Deny | Closed + denial outcome recorded | BR-CMS-019, 021, 034 |
| 3 | Closed + reopening request pending | Complaint Supervisor | UC-CMS-020 — Review Complaint Reopening Request | Decision = Approve | Reopened — exact lifecycle state unspecified (ISS-CMS-008) | BR-CMS-019, 020, 021, 034 |
CW-CMS-03 — Complaint Escalation Paths
| Field | Content |
| Workflow ID | CW-CMS-03 |
| Workflow Name | Complaint Escalation Paths |
| Type | Composite |
| Purpose / Scope | Combine manual and SLA-triggered escalation state changes as cross-cutting behavior over active unresolved complaints. |
| Trigger | Manual escalation decision or time/SLA breach event. |
| Participants | Complaint Handler; Complaint Supervisor; System |
| Constituent Workflows | BW-CMS-07; BW-CMS-08 |
| Related Workflows | CW-CMS-01; CW-CMS-02 as contextually applicable |
| Related CFRs / key AFRs |  |
| Related UCs | UC-CMS-011; UC-CMS-022 |
| Related BRs | BR-CMS-024; 025; 026; 027; 029; 034 |
| Notes / TODO | Escalation is orthogonal to lifecycle state. UC-CMS-021 reminder remains outside the STT because it is non-state-changing. |
| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| 1 | Active unresolved; not escalated | Complaint Handler | UC-CMS-011 — Manually Escalate Unresolved Complaint | Manual escalation chosen | Escalated (manual) | BR-CMS-024, 025, 034 |
| 2 | Active unresolved; SLA applicable; not escalated | System | UC-CMS-022 — Automatically Escalate Complaint on SLA Breach | Applicable SLA breached AND complaint remains unresolved | Escalated (automatic) | BR-CMS-025, 026, 027, 029, 034 |
