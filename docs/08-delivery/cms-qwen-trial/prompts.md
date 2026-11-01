
## Prompt 001 Initial backend models

UTC: 2026-11-01T18:01:18.885665+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3200, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/cms-qwen-trial/problem-statement-context.md
```
# CMS Problem Statement and Core Registry


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
| CFR-CMS-001 | Complaint Submission and Acceptance | CMS shall support complete complaint submission by a User / Complainant, validate mandatory submission data and applicable attachment constraints, record required submission data, assign a unique complaint identifier, and confirm successful acceptance. | Actor service + validation + recording | PS 3.1 |  |  |  |
| CFR-CMS-002 | Complaint Handling Setup | CMS shall allow the Complaint Handler to establish operational handling information for submitted complaints by manual assignment, categorization, and Low/Medium/High priority assignment, and shall record the resulting assignment and priority information. | Actor service + data/constraint | PS 3.2 |  |  |  |
| CFR-CMS-003 | Complaint Tracking and Progress History | CMS shall support complainant tracking and handler review/progress update while maintaining complaint status and progress history throughout the complaint lifecycle. | Actor service + information access + recording | PS 3.3 |  |  |  |
| CFR-CMS-004 | Complaint Lifecycle Outcome Management | CMS shall manage the defined complaint lifecycle and allow the Complaint Handler to resolve or reject a complaint with required outcome details while recording and communicating supported outcome/status changes. | State progression + validation + notification | PS 3.4 |  |  |  |
| CFR-CMS-005 | Closure Verification | CMS shall support the applicable User / Complainant or Complaint Supervisor verification path for a resolved complaint and record closure after successful verification when verification is required. | State progression + authorization | PS 3.4 |  |  |  |
| CFR-CMS-006 | Complaint Reopening | CMS shall allow a dissatisfied User / Complainant to request reopening of a closed complaint, allow the Complaint Supervisor to decide the request, and record the reopening decision and supported resulting complaint state information. | Actor service + decision + state progression | PS 3.5 |  |  |  |
| CFR-CMS-007 | Feedback Management | CMS shall allow Users / Complainants to submit feedback after resolution or closure and allow Complaint Handlers and Complaint Supervisors to review submitted feedback. | Actor service + access | PS 3.6 |  |  |  |
| CFR-CMS-008 | Manual Escalation and Oversight | CMS shall support manual escalation of unresolved complaints, maintain escalation status, and allow Complaint Supervisors to monitor escalated complaints. | State progression + information access | PS 3.7 |  |  |  |
| CFR-CMS-009 | SLA-Driven Reminder and Automatic Escalation | CMS shall associate complaint priority with applicable SLA timelines, trigger a reminder when an unresolved complaint approaches the applicable SLA breach condition, and automatically escalate an unresolved complaint when the applicable SLA is breached, without hard-coding unspecified SLA durations into the baseline. | Rule/constraint + event-triggered service + state progression | PS 3.7 |  |  |  |
| CFR-CMS-010 | Complaint Announcements | CMS shall allow authorized Complaint Handlers and Complaint Supervisors to publish complaint-related announcements, allow Users / Complainants to view them, and trigger configured announcement notifications. | Actor service + authorization + notification | PS 3.8 |  |  |  |
| CFR-CMS-011 | Complaint Reporting and Analytics Visibility | CMS shall provide the complaint reports, summaries, escalation summaries, and analytics visibility specified for Complaint Handlers, Complaint Supervisors, and System Admin, without introducing unsupported analytics scope. | Actor service + access + scope constraint | PS 3.9 |  |  |  |
| CFR-CMS-012 | Notification Triggering | CMS shall trigger the specified complaint-related email notification events while limiting CMS responsibility to notification triggering rather than central email-delivery or platform-level notification infrastructure. | System action + scope boundary | PS 3.10 |  |  |  |
| CFR-CMS-013 | CMS Role Management | CMS shall allow System Admin to assign and reassign the CMS-specific Complaint Handler and Complaint Supervisor roles for specified durations while enforcing exactly one active holder of each role and excluding HR/platform account administration. | Actor service + authorization + cardinality + scope constraint | PS 3.11 |  |  |  |
| CFR-CMS-014 | CMS Functional Scope Boundaries | CMS shall confine Complaint Management functionality to the accepted complaint-handling scope and shall not implement excluded cross-module functions or unstated external institutional policies/processes. | Scope constraint | PS 3.12 |  |  |  |
Level 2 — Atomic Requirements (AFR): Core Specification
| AFR ID | Parent CFR | AFR Statement | Historical ID | Source | Decomposition / Atomicity Rationale | Verification / Acceptance Focus |
| AFR-CMS-001 | CFR-CMS-001 | CMS shall allow a User / Complainant to submit a complaint at any time. | CMS-FR-001 | PS 3.1 |
| AFR-CMS-002 | CFR-CMS-001 | CMS shall record the complaint category for each submitted complaint. | CMS-FR-002 | PS 3.1 |
| AFR-CMS-003 | CFR-CMS-001 | CMS shall record the complaint description for each submitted complaint. | CMS-FR-003 | PS 3.1 |
| AFR-CMS-004 | CFR-CMS-001 | CMS shall record the submission date/time for each submitted complaint. | CMS-FR-004 | PS 3.1 |
| AFR-CMS-005 | CFR-CMS-001 | CMS shall allow complaint submissions to include supporting attachments. | CMS-FR-005 | PS 3.1 |
| AFR-CMS-006 | CFR-CMS-001 | CMS shall validate mandatory complaint fields before accepting a complaint submission. | CMS-FR-006 | PS 3.1 |
| AFR-CMS-007 | CFR-CMS-001 | CMS shall validate accepted attachment constraints before accepting submitted attachments. | CMS-FR-007 | PS 3.1 |
| AFR-CMS-008 | CFR-CMS-001 | CMS shall treat the exact attachment file-type, file-size, and format limits as configurable or institutional constraints outside the frozen problem-statement details. | CMS-FR-008 | PS 3.1 |
| AFR-CMS-009 | CFR-CMS-001 | CMS shall generate a unique complaint identifier for each submitted complaint. | CMS-FR-009 | PS 3.1 |
| AFR-CMS-010 | CFR-CMS-001 | CMS shall provide complaint submission confirmation or notification to the User / Complainant. | CMS-FR-010 | PS 3.1 |
| AFR-CMS-011 | CFR-CMS-002 | CMS shall allow the Complaint Handler to manually assign submitted complaints for operational handling. | CMS-FR-011 | PS 3.2 |
| AFR-CMS-012 | CFR-CMS-002 | CMS shall allow the Complaint Handler to categorize complaints by complaint category/type. | CMS-FR-012 | PS 3.2 |
| AFR-CMS-013 | CFR-CMS-002 | CMS shall allow the Complaint Handler to assign complaint priority as Low, Medium, or High. | CMS-FR-013 | PS 3.2 |
| AFR-CMS-014 | CFR-CMS-002 | CMS shall record assignment information for downstream complaint handling, reminders, and escalation. | CMS-FR-014 | PS 3.2 |
| AFR-CMS-015 | CFR-CMS-002 | CMS shall record priority information for downstream complaint handling, reminders, and escalation. | CMS-FR-015 | PS 3.2 |
| AFR-CMS-016 | CFR-CMS-003 | CMS shall allow a User / Complainant to track the status of the User / Complainant's submitted complaints. | CMS-FR-016 | PS 3.3 |
| AFR-CMS-017 | CFR-CMS-003 | CMS shall allow a User / Complainant to track the history of the User / Complainant's submitted complaints. | CMS-FR-017 | PS 3.3 |
| AFR-CMS-018 | CFR-CMS-003 | CMS shall allow Complaint Handlers to review complaints assigned for handling. | CMS-FR-018 | PS 3.3 |
| AFR-CMS-019 | CFR-CMS-003 | CMS shall allow Complaint Handlers to update complaint progress during processing. | CMS-FR-019 | PS 3.3 |
| AFR-CMS-020 | CFR-CMS-003 | CMS shall maintain complaint status history throughout the lifecycle of each complaint. | CMS-FR-020 | PS 3.3 |
| AFR-CMS-021 | CFR-CMS-003 | CMS shall maintain complaint progress history throughout the lifecycle of each complaint. | CMS-FR-021 | PS 3.3 |
| AFR-CMS-022 | CFR-CMS-004 | CMS shall recognize Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states. | CMS-FR-022 | PS 3.4 |
| AFR-CMS-023 | CFR-CMS-004 | CMS shall record complaint resolution details for resolved complaints. | CMS-FR-023 | PS 3.4 |
| AFR-CMS-024 | CFR-CMS-004 | CMS shall record rejection details or rejection reason information for rejected complaints. | CMS-FR-024 | PS 3.4 |
| AFR-CMS-025 | CFR-CMS-004 | CMS shall notify Users / Complainants of complaint outcome updates. | CMS-FR-025 | PS 3.4 |
| AFR-CMS-026 | CFR-CMS-004 | CMS shall notify Users / Complainants of complaint status updates. | CMS-FR-026 | PS 3.4 |
| AFR-CMS-027 | CFR-CMS-005 | CMS shall support User / Complainant verification of a resolved complaint when the applicable closure process requires such verification. | CMS-FR-027 | PS 3.4 |
| AFR-CMS-028 | CFR-CMS-005 | CMS shall support Complaint Supervisor verification of a resolved complaint when the applicable closure process requires such verification. | CMS-FR-028 | PS 3.4 |
| AFR-CMS-029 | CFR-CMS-005 | CMS shall record complaint closure after successful verification when verification is required. | CMS-FR-029 | PS 3.4 |
| AFR-CMS-030 | CFR-CMS-006 | CMS shall allow Users / Complainants to request reopening of a closed complaint where dissatisfaction remains after closure. | CMS-FR-030 | PS 3.5 |
| AFR-CMS-031 | CFR-CMS-006 | CMS shall allow the Complaint Supervisor to review complaint reopening requests. | CMS-FR-031 | PS 3.5 |
| AFR-CMS-032 | CFR-CMS-006 | CMS shall reopen the complaint when a reopening request is approved. | CMS-FR-032 | PS 3.5 |
| AFR-CMS-033 | CFR-CMS-006 | CMS shall update the complaint status accordingly when reopening is approved. | CMS-FR-033 | PS 3.5 |
| AFR-CMS-034 | CFR-CMS-006 | CMS shall record the outcome of the complaint reopening request. | CMS-FR-034 | PS 3.5 |
| AFR-CMS-035 | CFR-CMS-007 | CMS shall allow Users / Complainants to submit feedback after complaint resolution or closure. | CMS-FR-035 | PS 3.6 |
| AFR-CMS-036 | CFR-CMS-007 | CMS shall allow Complaint Handlers to review submitted feedback. | CMS-FR-036 | PS 3.6 |
| AFR-CMS-037 | CFR-CMS-007 | CMS shall allow Complaint Supervisors to review submitted feedback. | CMS-FR-037 | PS 3.6 |
| AFR-CMS-038 | CFR-CMS-008 | CMS shall allow unresolved complaints to be escalated manually. | CMS-FR-038 | PS 3.7 |
| AFR-CMS-039 | CFR-CMS-008 | CMS shall track escalation status. | CMS-FR-039 | PS 3.7 |
| AFR-CMS-040 | CFR-CMS-008 | CMS shall allow Complaint Supervisors to monitor escalated complaints. | CMS-FR-040 | PS 3.7 |
| AFR-CMS-041 | CFR-CMS-009 | CMS shall associate complaint priority with applicable SLA timelines. | CMS-FR-041 | PS 3.7 |
| AFR-CMS-042 | CFR-CMS-009 | CMS shall not specify exact SLA duration values in the module baseline. | CMS-FR-042 | PS 3.7 |
| AFR-CMS-043 | CFR-CMS-009 | CMS shall send reminder notifications when a complaint approaches the applicable SLA breach condition. | CMS-FR-043 | PS 3.7 |
| AFR-CMS-044 | CFR-CMS-009 | CMS shall automatically escalate a complaint if it is not resolved within the applicable SLA timeline. | CMS-FR-044 | PS 3.7 |
| AFR-CMS-045 | CFR-CMS-010 | CMS shall allow Complaint Handlers to publish complaint-related announcements. | CMS-FR-045 | PS 3.8 |
| AFR-CMS-046 | CFR-CMS-010 | CMS shall allow Complaint Supervisors to publish complaint-related announcements. | CMS-FR-046 | PS 3.8 |
| AFR-CMS-047 | CFR-CMS-010 | CMS shall allow Users / Complainants to view complaint-related announcements. | CMS-FR-047 | PS 3.8 |
| AFR-CMS-048 | CFR-CMS-010 | CMS shall send announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements. | CMS-FR-048 | PS 3.8 |
| AFR-CMS-049 | CFR-CMS-011 | CMS shall allow Complaint Handlers to generate operational complaint reports. | CMS-FR-049 | PS 3.9 |
| AFR-CMS-050 | CFR-CMS-011 | CMS shall allow Complaint Supervisors to view complaint summaries. | CMS-FR-050 | PS 3.9 |
| AFR-CMS-051 | CFR-CMS-011 | CMS shall allow Complaint Supervisors to view escalation summaries. | CMS-FR-051 | PS 3.9 |
| AFR-CMS-052 | CFR-CMS-011 | CMS shall allow System Admin to view complaint reports available within CMS. | CMS-FR-052 | PS 3.9 |
| AFR-CMS-053 | CFR-CMS-011 | CMS shall allow System Admin to view analytics available within CMS. | CMS-FR-053 | PS 3.9 |
| AFR-CMS-054 | CFR-CMS-011 | CMS shall limit analytics scope to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS. | CMS-FR-054 | PS 3.9 |
| AFR-CMS-055 | CFR-CMS-012 | CMS shall trigger email notifications for complaint submission events. | CMS-FR-055 | PS 3.10 |
| AFR-CMS-056 | CFR-CMS-012 | CMS shall trigger email notifications for complaint status update events. | CMS-FR-056 | PS 3.10 |
| AFR-CMS-057 | CFR-CMS-012 | CMS shall trigger email notifications for complaint resolution events. | CMS-FR-057 | PS 3.10 |
| AFR-CMS-058 | CFR-CMS-012 | CMS shall trigger email notifications for complaint rejection events. | CMS-FR-058 | PS 3.10 |
| AFR-CMS-059 | CFR-CMS-012 | CMS shall trigger email notifications for complaint escalation events. | CMS-FR-059 | PS 3.10 |
| AFR-CMS-060 | CFR-CMS-012 | CMS shall trigger email notifications for complaint reopening outcome events where applicable. | CMS-FR-060 | PS 3.10 |
| AFR-CMS-061 | CFR-CMS-012 | CMS shall trigger email notifications for feedback-related events where applicable. | CMS-FR-061 | PS 3.10 |
| AFR-CMS-062 | CFR-CMS-012 | CMS shall trigger email notifications for complaint-related announcement events. | CMS-FR-062 | PS 3.10 |
| AFR-CMS-063 | CFR-CMS-012 | CMS shall limit module responsibility to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events. | CMS-FR-063 | PS 3.10 |
| AFR-CMS-064 | CFR-CMS-013 | CMS shall allow System Admin to assign the Complaint Handler role to an existing institutional user for a specified duration. | CMS-FR-064 | PS 3.11 |
| AFR-CMS-065 | CFR-CMS-013 | CMS shall allow System Admin to assign the Complaint Supervisor role to an existing institutional user for a specified duration. | CMS-FR-065 | PS 3.11 |
| AFR-CMS-066 | CFR-CMS-013 | CMS shall allow System Admin to reassign Complaint Handler and Complaint Supervisor roles mid-cycle. | CMS-FR-066 | PS 3.11 |
| AFR-CMS-067 | CFR-CMS-013 | CMS shall enforce exactly one active Complaint Handler role-holder at a time within CMS. | CMS-FR-067 | PS 3.11 |
| AFR-CMS-068 | CFR-CMS-013 | CMS shall enforce exactly one active Complaint Supervisor role-holder at a time within CMS. | CMS-FR-068 | PS 3.11 |
| AFR-CMS-069 | CFR-CMS-013 | CMS role assignment shall be limited to CMS-specific operational and supervisory roles. | CMS-FR-069 | PS 3.11 |
| AFR-CMS-070 | CFR-CMS-013 | CMS shall exclude HR master-data management, payroll, employment records, and platform-wide user-account administration from CMS role-management scope. | CMS-FR-070 | PS 3.11 |
| AFR-CMS-071 | CFR-CMS-014 | CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration. | CMS-FR-071 | PS 3.12 |
| AFR-CMS-072 | CFR-CMS-014 | CMS shall limit complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information. | CMS-FR-072 | PS 3.12 |
| AFR-CMS-073 | CFR-CMS-014 | CMS shall treat external institutional policies, manuals, guidelines, and departmental processes as outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them. | CMS-FR-073 | PS 3.12 |
AFR Traceability, Minimum Representation, and Disposition
| AFR ID | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Minimum Sufficient Representation | Coverage | UC Exact Location(s) |
| AFR-CMS-001 |  |  |  |  |
| AFR-CMS-002 |  |  |  |  |
| AFR-CMS-003 |  |  |  |  |
| AFR-CMS-004 |  |  |  |  |
| AFR-CMS-005 |  |  |  |  |
| AFR-CMS-006 |  |  |  |  |
| AFR-CMS-007 |  |  |  |  |
| AFR-CMS-008 |  |  |  |  |
| AFR-CMS-009 |  |  |  |  |
| AFR-CMS-010 |  |  |  |  |
| AFR-CMS-011 |  |  |  |  |
| AFR-CMS-012 |  |  |  |  |
| AFR-CMS-013 |  |  |  |  |
| AFR-CMS-014 |  |  |  |  |
| AFR-CMS-015 |  |  |  |  |
| AFR-CMS-016 |  |  |  |  |
| AFR-CMS-017 |  |  |  |  |
| AFR-CMS-018 |  |  |  |  |
| AFR-CMS-019 |  |  |  |  |
| AFR-CMS-020 |  |  |  |  |
| AFR-CMS-021 |  |  |  |  |
| AFR-CMS-022 |  |  |  |  |
| AFR-CMS-023 |  |  |  |  |
| AFR-CMS-024 |  |  |  |  |
| AFR-CMS-025 |  |  |  |  |
| AFR-CMS-026 |  |  |  |  |
| AFR-CMS-027 |  |  |  |  |
| AFR-CMS-028 |  |  |  |  |
| AFR-CMS-029 |  |  |  |  |
| AFR-CMS-030 |  |  |  |  |
| AFR-CMS-031 |  |  |  |  |
| AFR-CMS-032 |  |  |  |  |
| AFR-CMS-033 |  |  |  |  |
| AFR-CMS-034 |  |  |  |  |
| AFR-CMS-035 |  |  |  |  |
| AFR-CMS-036 |  |  |  |  |
| AFR-CMS-037 |  |  |  |  |
| AFR-CMS-038 |  |  |  |  |
| AFR-CMS-039 |  |  |  |  |
| AFR-CMS-040 |  |  |  |  |
| AFR-CMS-041 |  |  |  |  |
| AFR-CMS-042 |  |  |  |  |
| AFR-CMS-043 |  |  |  |  |
| AFR-CMS-044 |  |  |  |  |
| AFR-CMS-045 |  |  |  |  |
| AFR-CMS-046 |  |  |  |  |
| AFR-CMS-047 |  |  |  |  |
| AFR-CMS-048 |  |  |  |  |
| AFR-CMS-049 |  |  |  |  |
| AFR-CMS-050 |  |  |  |  |
| AFR-CMS-051 |  |  |  |  |
| AFR-CMS-052 |  |  |  |  |
| AFR-CMS-053 |  |  |  |  |
| AFR-CMS-054 |  |  |  |  |
| AFR-CMS-055 |  |  |  |  |
| AFR-CMS-056 |  |  |  |  |
| AFR-CMS-057 |  |  |  |  |
| AFR-CMS-058 |  |  |  |  |
| AFR-CMS-059 |  |  |  |  |
| AFR-CMS-060 |  |  |  |  |
| AFR-CMS-061 |  |  |  |  |
| AFR-CMS-062 |  |  |  |  |
| AFR-CMS-063 |  |  |  |  |
| AFR-CMS-064 |  |  |  |  |
| AFR-CMS-065 |  |  |  |  |
| AFR-CMS-066 |  |  |  |  |
| AFR-CMS-067 |  |  |  |  |
| AFR-CMS-068 |  |  |  |  |
| AFR-CMS-069 |  |  |  |  |
| AFR-CMS-070 |  |  |  |  |
| AFR-CMS-071 |  |  |  |  |
| AFR-CMS-072 |  |  |  |  |
| AFR-CMS-073 |  |  |  |  |
Open Domain Clarifications Preserved
ISS-CMS-007 — In Progress is recognized but its entry transition is not defined.
ISS-CMS-008 — Approved reopening requires a status update but the exact resulting lifecycle state is not defined.
ISS-CMS-009 — Manual assignment target/ownership semantics are not defined beyond operational handling assignment.
ISS-CMS-010 — Closure behavior when verification is not required is not defined.

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

```


### Repository file core/db/mixins.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    """A row belonging to a person.

    `user_id` is the IAM user id. It is a plain integer and NOT a ForeignKey —
    there is no user table in this database, and cross-boundary references must
    stay unconstrained so a module can be extracted later without schema
    surgery.
    """

    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


END OF REFERENCES

CURRENT TASK

Generate only modules/complaint_cms/models.py as Django data-model definitions for the Complaint Management System (CMS) module inside the supplied Fusion ERP base. Maximum approximately 170 lines. Do not put business functions, save overrides, can_* methods, getters, placeholders, duplicate class definitions or validation methods in models.py. Use compact fields and choices, and plain integer IAM user IDs (do not create Django User foreign keys or login models). The foundation should store: ComplaintCategory (code, name, description, severity_default, sla_ack_hours, sla_resolution_hours, is_active), RoutingRule (category FK, location_type, target_section, primary_authority_role, escalation_authority_role, is_active), Complaint (tracking_code, user_id, is_anonymous, category FK, title, description, location_type, location_details, severity, status, assigned_to_id, assigned_role, escalation_level, sla_due_at, resolved_at, closed_at, resolution_summary, reopen_count, feedback_rating, feedback_comment), ComplaintAttachment (complaint FK, uploaded_by_id, file_name, file_url, stage), ComplaintUpdate (complaint FK, actor_id, update_type, visibility, comment, old_status, new_status), ComplaintTask (complaint FK, assigned_to_id, role_name, task_type, status, due_at, completed_at), and ComplaintNotification (complaint FK, recipient_id, title, message, is_read). Inherit TimestampedModel from core.db.mixins. Include data only; later service files will implement operations against these actual fields. Return complete raw Python source only without markdown code fences.

Output file: modules/complaint_cms/models.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 002 AppConfig and module registry

UTC: 2026-11-01T18:01:55.372084+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP CMS pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/placement/registry.py
```
"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "placement_cell", "label": "Placement Cell", "icon": "Briefcase",
    "base_path": "/placement", "nav_section": "Placement", "sort_order": 10,
    "status": "active",
}

NAV_ITEMS = [
    # -- student: registration first, because rule 1 gates everything below ---
    {"code": "placement.registration", "label": "Season Registration",
     "icon": "Checks", "to": "/placement/registration",
     "required_permission": "placement_cell.registration.self",
     "sort_order": 5},
    {"code": "placement.postings", "label": "Opportunities",
     "icon": "ClipboardText", "to": "/placement/postings",
     "required_permission": "placement_cell.job_posting.view", "sort_order": 10},
    {"code": "placement.mine", "label": "My Applications",
     "icon": "UserCheck", "to": "/placement/mine",
     "required_permission": "placement_cell.application.view_self",
     "sort_order": 20},
    {"code": "placement.offers", "label": "My Offers",
     "icon": "Signature", "to": "/placement/offers",
     "required_permission": "placement_cell.offer.respond", "sort_order": 30},

    # -- staff (TPO / chairman) -------------------------------------------
    {"code": "placement.registrations", "label": "Registrations",
     "icon": "Checks", "to": "/placement/registration-approvals",
     "required_permission": "placement_cell.registration.manage",
     "sort_order": 55},
    {"code": "placement.applications", "label": "Applications",
     "icon": "Users", "to": "/placement/applications",
     "required_permission": "placement_cell.application.view", "sort_order": 50},
    {"code": "placement.companies", "label": "Companies",
     "icon": "Buildings", "to": "/placement/companies",
     "required_permission": "placement_cell.company.manage", "sort_order": 60},
    {"code": "placement.interviews", "label": "Interviews",
     "icon": "CalendarBlank", "to": "/placement/interviews",
     "required_permission": "placement_cell.interview.schedule",
     "sort_order": 70},
    {"code": "placement.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/placement/announcements",
     "required_permission": "placement_cell.announcement.publish",
     "sort_order": 80},
    {"code": "placement.cpi", "label": "Student CPI",
     "icon": "GraduationCap", "to": "/placement/students-cpi",
     "required_permission": "placement_cell.academic_directory.view",
     "sort_order": 85},
    {"code": "placement.reports", "label": "Reports",
     "icon": "ChartBar", "to": "/placement/reports",
     "required_permission": "placement_cell.report.view", "sort_order": 90},
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("placement_cell.job_posting.view", "See job postings"),
    ("placement_cell.job_posting.manage", "Create and publish postings"),
    ("placement_cell.application.view", "See all applications"),
    ("placement_cell.application.view_self", "See one's own applications"),
    ("placement_cell.application.create", "Apply to a posting"),
    ("placement_cell.application.review", "Shortlist and reject applications"),
    ("placement_cell.application.delete", "Withdraw an application"),
    ("placement_cell.application.auto_withdraw", "System auto-withdrawal"),
    ("placement_cell.interview.schedule", "Schedule interview rounds"),
    ("placement_cell.offer.issue", "Extend an offer"),
    ("placement_cell.offer.respond", "Accept or decline an offer"),
    ("placement_cell.offer.revoke", "Revoke an issued offer"),
    ("placement_cell.offer.expire", "System offer expiry"),
    ("placement_cell.company.manage", "Register and approve companies"),
    ("placement_cell.announcement.publish", "Publish announcements"),
    ("placement_cell.report.view", "See operational reports"),
    ("placement_cell.registration.debar",
     "Record conduct incidents and impose placement sanctions"),
    ("placement_cell.registration.manage",
     "Approve late registrations and re-registrations"),
    ("placement_cell.registration.self",
     "Register yourself for a placement season"),
    ("placement_cell.record.manage",
     "Record off-campus placements and chase offer letters"),
    ("placement_cell.academic_directory.view",
     "Browse every student's declared CPI"),
]

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "placement_cell.application.auto_withdraw",
    "placement_cell.offer.expire",
]

_STUDENT = [
    "placement_cell.registration.self",
    "placement_cell.job_posting.view",
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.application.delete",
    "placement_cell.offer.respond",
]

_COORDINATOR = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.application.review",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
]

_OFFICER = [
    *_COORDINATOR,
    "placement_cell.job_posting.manage",
    "placement_cell.interview.schedule",
    "placement_cell.offer.issue",
    "placement_cell.offer.revoke",
    "placement_cell.company.manage",
    "placement_cell.announcement.publish",
    "placement_cell.registration.manage",
    "placement_cell.registration.debar",
    "placement_cell.record.manage",
]

#: Oversees rather than operates: no shortlisting and no offers.
_CHAIRMAN = [
    "placement_cell.job_posting.view",
    "placement_cell.application.view",
    "placement_cell.report.view",
    "placement_cell.academic_directory.view",
    "placement_cell.announcement.publish",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "placement_coordinator": _COORDINATOR,
    "placement_officer": _OFFICER,
    "placement_chairman": _CHAIRMAN,
    "Dean Academic": _CHAIRMAN,
}

```


### Repository file docs/08-delivery/cms-qwen-trial/problem-statement-context.md
```
# CMS Problem Statement and Core Registry


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
| CFR-CMS-001 | Complaint Submission and Acceptance | CMS shall support complete complaint submission by a User / Complainant, validate mandatory submission data and applicable attachment constraints, record required submission data, assign a unique complaint identifier, and confirm successful acceptance. | Actor service + validation + recording | PS 3.1 |  |  |  |
| CFR-CMS-002 | Complaint Handling Setup | CMS shall allow the Complaint Handler to establish operational handling information for submitted complaints by manual assignment, categorization, and Low/Medium/High priority assignment, and shall record the resulting assignment and priority information. | Actor service + data/constraint | PS 3.2 |  |  |  |
| CFR-CMS-003 | Complaint Tracking and Progress History | CMS shall support complainant tracking and handler review/progress update while maintaining complaint status and progress history throughout the complaint lifecycle. | Actor service + information access + recording | PS 3.3 |  |  |  |
| CFR-CMS-004 | Complaint Lifecycle Outcome Management | CMS shall manage the defined complaint lifecycle and allow the Complaint Handler to resolve or reject a complaint with required outcome details while recording and communicating supported outcome/status changes. | State progression + validation + notification | PS 3.4 |  |  |  |
| CFR-CMS-005 | Closure Verification | CMS shall support the applicable User / Complainant or Complaint Supervisor verification path for a resolved complaint and record closure after successful verification when verification is required. | State progression + authorization | PS 3.4 |  |  |  |
| CFR-CMS-006 | Complaint Reopening | CMS shall allow a dissatisfied User / Complainant to request reopening of a closed complaint, allow the Complaint Supervisor to decide the request, and record the reopening decision and supported resulting complaint state information. | Actor service + decision + state progression | PS 3.5 |  |  |  |
| CFR-CMS-007 | Feedback Management | CMS shall allow Users / Complainants to submit feedback after resolution or closure and allow Complaint Handlers and Complaint Supervisors to review submitted feedback. | Actor service + access | PS 3.6 |  |  |  |
| CFR-CMS-008 | Manual Escalation and Oversight | CMS shall support manual escalation of unresolved complaints, maintain escalation status, and allow Complaint Supervisors to monitor escalated complaints. | State progression + information access | PS 3.7 |  |  |  |
| CFR-CMS-009 | SLA-Driven Reminder and Automatic Escalation | CMS shall associate complaint priority with applicable SLA timelines, trigger a reminder when an unresolved complaint approaches the applicable SLA breach condition, and automatically escalate an unresolved complaint when the applicable SLA is breached, without hard-coding unspecified SLA durations into the baseline. | Rule/constraint + event-triggered service + state progression | PS 3.7 |  |  |  |
| CFR-CMS-010 | Complaint Announcements | CMS shall allow authorized Complaint Handlers and Complaint Supervisors to publish complaint-related announcements, allow Users / Complainants to view them, and trigger configured announcement notifications. | Actor service + authorization + notification | PS 3.8 |  |  |  |
| CFR-CMS-011 | Complaint Reporting and Analytics Visibility | CMS shall provide the complaint reports, summaries, escalation summaries, and analytics visibility specified for Complaint Handlers, Complaint Supervisors, and System Admin, without introducing unsupported analytics scope. | Actor service + access + scope constraint | PS 3.9 |  |  |  |
| CFR-CMS-012 | Notification Triggering | CMS shall trigger the specified complaint-related email notification events while limiting CMS responsibility to notification triggering rather than central email-delivery or platform-level notification infrastructure. | System action + scope boundary | PS 3.10 |  |  |  |
| CFR-CMS-013 | CMS Role Management | CMS shall allow System Admin to assign and reassign the CMS-specific Complaint Handler and Complaint Supervisor roles for specified durations while enforcing exactly one active holder of each role and excluding HR/platform account administration. | Actor service + authorization + cardinality + scope constraint | PS 3.11 |  |  |  |
| CFR-CMS-014 | CMS Functional Scope Boundaries | CMS shall confine Complaint Management functionality to the accepted complaint-handling scope and shall not implement excluded cross-module functions or unstated external institutional policies/processes. | Scope constraint | PS 3.12 |  |  |  |
Level 2 — Atomic Requirements (AFR): Core Specification
| AFR ID | Parent CFR | AFR Statement | Historical ID | Source | Decomposition / Atomicity Rationale | Verification / Acceptance Focus |
| AFR-CMS-001 | CFR-CMS-001 | CMS shall allow a User / Complainant to submit a complaint at any time. | CMS-FR-001 | PS 3.1 |
| AFR-CMS-002 | CFR-CMS-001 | CMS shall record the complaint category for each submitted complaint. | CMS-FR-002 | PS 3.1 |
| AFR-CMS-003 | CFR-CMS-001 | CMS shall record the complaint description for each submitted complaint. | CMS-FR-003 | PS 3.1 |
| AFR-CMS-004 | CFR-CMS-001 | CMS shall record the submission date/time for each submitted complaint. | CMS-FR-004 | PS 3.1 |
| AFR-CMS-005 | CFR-CMS-001 | CMS shall allow complaint submissions to include supporting attachments. | CMS-FR-005 | PS 3.1 |
| AFR-CMS-006 | CFR-CMS-001 | CMS shall validate mandatory complaint fields before accepting a complaint submission. | CMS-FR-006 | PS 3.1 |
| AFR-CMS-007 | CFR-CMS-001 | CMS shall validate accepted attachment constraints before accepting submitted attachments. | CMS-FR-007 | PS 3.1 |
| AFR-CMS-008 | CFR-CMS-001 | CMS shall treat the exact attachment file-type, file-size, and format limits as configurable or institutional constraints outside the frozen problem-statement details. | CMS-FR-008 | PS 3.1 |
| AFR-CMS-009 | CFR-CMS-001 | CMS shall generate a unique complaint identifier for each submitted complaint. | CMS-FR-009 | PS 3.1 |
| AFR-CMS-010 | CFR-CMS-001 | CMS shall provide complaint submission confirmation or notification to the User / Complainant. | CMS-FR-010 | PS 3.1 |
| AFR-CMS-011 | CFR-CMS-002 | CMS shall allow the Complaint Handler to manually assign submitted complaints for operational handling. | CMS-FR-011 | PS 3.2 |
| AFR-CMS-012 | CFR-CMS-002 | CMS shall allow the Complaint Handler to categorize complaints by complaint category/type. | CMS-FR-012 | PS 3.2 |
| AFR-CMS-013 | CFR-CMS-002 | CMS shall allow the Complaint Handler to assign complaint priority as Low, Medium, or High. | CMS-FR-013 | PS 3.2 |
| AFR-CMS-014 | CFR-CMS-002 | CMS shall record assignment information for downstream complaint handling, reminders, and escalation. | CMS-FR-014 | PS 3.2 |
| AFR-CMS-015 | CFR-CMS-002 | CMS shall record priority information for downstream complaint handling, reminders, and escalation. | CMS-FR-015 | PS 3.2 |
| AFR-CMS-016 | CFR-CMS-003 | CMS shall allow a User / Complainant to track the status of the User / Complainant's submitted complaints. | CMS-FR-016 | PS 3.3 |
| AFR-CMS-017 | CFR-CMS-003 | CMS shall allow a User / Complainant to track the history of the User / Complainant's submitted complaints. | CMS-FR-017 | PS 3.3 |
| AFR-CMS-018 | CFR-CMS-003 | CMS shall allow Complaint Handlers to review complaints assigned for handling. | CMS-FR-018 | PS 3.3 |
| AFR-CMS-019 | CFR-CMS-003 | CMS shall allow Complaint Handlers to update complaint progress during processing. | CMS-FR-019 | PS 3.3 |
| AFR-CMS-020 | CFR-CMS-003 | CMS shall maintain complaint status history throughout the lifecycle of each complaint. | CMS-FR-020 | PS 3.3 |
| AFR-CMS-021 | CFR-CMS-003 | CMS shall maintain complaint progress history throughout the lifecycle of each complaint. | CMS-FR-021 | PS 3.3 |
| AFR-CMS-022 | CFR-CMS-004 | CMS shall recognize Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states. | CMS-FR-022 | PS 3.4 |
| AFR-CMS-023 | CFR-CMS-004 | CMS shall record complaint resolution details for resolved complaints. | CMS-FR-023 | PS 3.4 |
| AFR-CMS-024 | CFR-CMS-004 | CMS shall record rejection details or rejection reason information for rejected complaints. | CMS-FR-024 | PS 3.4 |
| AFR-CMS-025 | CFR-CMS-004 | CMS shall notify Users / Complainants of complaint outcome updates. | CMS-FR-025 | PS 3.4 |
| AFR-CMS-026 | CFR-CMS-004 | CMS shall notify Users / Complainants of complaint status updates. | CMS-FR-026 | PS 3.4 |
| AFR-CMS-027 | CFR-CMS-005 | CMS shall support User / Complainant verification of a resolved complaint when the applicable closure process requires such verification. | CMS-FR-027 | PS 3.4 |
| AFR-CMS-028 | CFR-CMS-005 | CMS shall support Complaint Supervisor verification of a resolved complaint when the applicable closure process requires such verification. | CMS-FR-028 | PS 3.4 |
| AFR-CMS-029 | CFR-CMS-005 | CMS shall record complaint closure after successful verification when verification is required. | CMS-FR-029 | PS 3.4 |
| AFR-CMS-030 | CFR-CMS-006 | CMS shall allow Users / Complainants to request reopening of a closed complaint where dissatisfaction remains after closure. | CMS-FR-030 | PS 3.5 |
| AFR-CMS-031 | CFR-CMS-006 | CMS shall allow the Complaint Supervisor to review complaint reopening requests. | CMS-FR-031 | PS 3.5 |
| AFR-CMS-032 | CFR-CMS-006 | CMS shall reopen the complaint when a reopening request is approved. | CMS-FR-032 | PS 3.5 |
| AFR-CMS-033 | CFR-CMS-006 | CMS shall update the complaint status accordingly when reopening is approved. | CMS-FR-033 | PS 3.5 |
| AFR-CMS-034 | CFR-CMS-006 | CMS shall record the outcome of the complaint reopening request. | CMS-FR-034 | PS 3.5 |
| AFR-CMS-035 | CFR-CMS-007 | CMS shall allow Users / Complainants to submit feedback after complaint resolution or closure. | CMS-FR-035 | PS 3.6 |
| AFR-CMS-036 | CFR-CMS-007 | CMS shall allow Complaint Handlers to review submitted feedback. | CMS-FR-036 | PS 3.6 |
| AFR-CMS-037 | CFR-CMS-007 | CMS shall allow Complaint Supervisors to review submitted feedback. | CMS-FR-037 | PS 3.6 |
| AFR-CMS-038 | CFR-CMS-008 | CMS shall allow unresolved complaints to be escalated manually. | CMS-FR-038 | PS 3.7 |
| AFR-CMS-039 | CFR-CMS-008 | CMS shall track escalation status. | CMS-FR-039 | PS 3.7 |
| AFR-CMS-040 | CFR-CMS-008 | CMS shall allow Complaint Supervisors to monitor escalated complaints. | CMS-FR-040 | PS 3.7 |
| AFR-CMS-041 | CFR-CMS-009 | CMS shall associate complaint priority with applicable SLA timelines. | CMS-FR-041 | PS 3.7 |
| AFR-CMS-042 | CFR-CMS-009 | CMS shall not specify exact SLA duration values in the module baseline. | CMS-FR-042 | PS 3.7 |
| AFR-CMS-043 | CFR-CMS-009 | CMS shall send reminder notifications when a complaint approaches the applicable SLA breach condition. | CMS-FR-043 | PS 3.7 |
| AFR-CMS-044 | CFR-CMS-009 | CMS shall automatically escalate a complaint if it is not resolved within the applicable SLA timeline. | CMS-FR-044 | PS 3.7 |
| AFR-CMS-045 | CFR-CMS-010 | CMS shall allow Complaint Handlers to publish complaint-related announcements. | CMS-FR-045 | PS 3.8 |
| AFR-CMS-046 | CFR-CMS-010 | CMS shall allow Complaint Supervisors to publish complaint-related announcements. | CMS-FR-046 | PS 3.8 |
| AFR-CMS-047 | CFR-CMS-010 | CMS shall allow Users / Complainants to view complaint-related announcements. | CMS-FR-047 | PS 3.8 |
| AFR-CMS-048 | CFR-CMS-010 | CMS shall send announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements. | CMS-FR-048 | PS 3.8 |
| AFR-CMS-049 | CFR-CMS-011 | CMS shall allow Complaint Handlers to generate operational complaint reports. | CMS-FR-049 | PS 3.9 |
| AFR-CMS-050 | CFR-CMS-011 | CMS shall allow Complaint Supervisors to view complaint summaries. | CMS-FR-050 | PS 3.9 |
| AFR-CMS-051 | CFR-CMS-011 | CMS shall allow Complaint Supervisors to view escalation summaries. | CMS-FR-051 | PS 3.9 |
| AFR-CMS-052 | CFR-CMS-011 | CMS shall allow System Admin to view complaint reports available within CMS. | CMS-FR-052 | PS 3.9 |
| AFR-CMS-053 | CFR-CMS-011 | CMS shall allow System Admin to view analytics available within CMS. | CMS-FR-053 | PS 3.9 |
| AFR-CMS-054 | CFR-CMS-011 | CMS shall limit analytics scope to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS. | CMS-FR-054 | PS 3.9 |
| AFR-CMS-055 | CFR-CMS-012 | CMS shall trigger email notifications for complaint submission events. | CMS-FR-055 | PS 3.10 |
| AFR-CMS-056 | CFR-CMS-012 | CMS shall trigger email notifications for complaint status update events. | CMS-FR-056 | PS 3.10 |
| AFR-CMS-057 | CFR-CMS-012 | CMS shall trigger email notifications for complaint resolution events. | CMS-FR-057 | PS 3.10 |
| AFR-CMS-058 | CFR-CMS-012 | CMS shall trigger email notifications for complaint rejection events. | CMS-FR-058 | PS 3.10 |
| AFR-CMS-059 | CFR-CMS-012 | CMS shall trigger email notifications for complaint escalation events. | CMS-FR-059 | PS 3.10 |
| AFR-CMS-060 | CFR-CMS-012 | CMS shall trigger email notifications for complaint reopening outcome events where applicable. | CMS-FR-060 | PS 3.10 |
| AFR-CMS-061 | CFR-CMS-012 | CMS shall trigger email notifications for feedback-related events where applicable. | CMS-FR-061 | PS 3.10 |
| AFR-CMS-062 | CFR-CMS-012 | CMS shall trigger email notifications for complaint-related announcement events. | CMS-FR-062 | PS 3.10 |
| AFR-CMS-063 | CFR-CMS-012 | CMS shall limit module responsibility to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events. | CMS-FR-063 | PS 3.10 |
| AFR-CMS-064 | CFR-CMS-013 | CMS shall allow System Admin to assign the Complaint Handler role to an existing institutional user for a specified duration. | CMS-FR-064 | PS 3.11 |
| AFR-CMS-065 | CFR-CMS-013 | CMS shall allow System Admin to assign the Complaint Supervisor role to an existing institutional user for a specified duration. | CMS-FR-065 | PS 3.11 |
| AFR-CMS-066 | CFR-CMS-013 | CMS shall allow System Admin to reassign Complaint Handler and Complaint Supervisor roles mid-cycle. | CMS-FR-066 | PS 3.11 |
| AFR-CMS-067 | CFR-CMS-013 | CMS shall enforce exactly one active Complaint Handler role-holder at a time within CMS. | CMS-FR-067 | PS 3.11 |
| AFR-CMS-068 | CFR-CMS-013 | CMS shall enforce exactly one active Complaint Supervisor role-holder at a time within CMS. | CMS-FR-068 | PS 3.11 |
| AFR-CMS-069 | CFR-CMS-013 | CMS role assignment shall be limited to CMS-specific operational and supervisory roles. | CMS-FR-069 | PS 3.11 |
| AFR-CMS-070 | CFR-CMS-013 | CMS shall exclude HR master-data management, payroll, employment records, and platform-wide user-account administration from CMS role-management scope. | CMS-FR-070 | PS 3.11 |
| AFR-CMS-071 | CFR-CMS-014 | CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration. | CMS-FR-071 | PS 3.12 |
| AFR-CMS-072 | CFR-CMS-014 | CMS shall limit complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information. | CMS-FR-072 | PS 3.12 |
| AFR-CMS-073 | CFR-CMS-014 | CMS shall treat external institutional policies, manuals, guidelines, and departmental processes as outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them. | CMS-FR-073 | PS 3.12 |
AFR Traceability, Minimum Representation, and Disposition
| AFR ID | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Minimum Sufficient Representation | Coverage | UC Exact Location(s) |
| AFR-CMS-001 |  |  |  |  |
| AFR-CMS-002 |  |  |  |  |
| AFR-CMS-003 |  |  |  |  |
| AFR-CMS-004 |  |  |  |  |
| AFR-CMS-005 |  |  |  |  |
| AFR-CMS-006 |  |  |  |  |
| AFR-CMS-007 |  |  |  |  |
| AFR-CMS-008 |  |  |  |  |
| AFR-CMS-009 |  |  |  |  |
| AFR-CMS-010 |  |  |  |  |
| AFR-CMS-011 |  |  |  |  |
| AFR-CMS-012 |  |  |  |  |
| AFR-CMS-013 |  |  |  |  |
| AFR-CMS-014 |  |  |  |  |
| AFR-CMS-015 |  |  |  |  |
| AFR-CMS-016 |  |  |  |  |
| AFR-CMS-017 |  |  |  |  |
| AFR-CMS-018 |  |  |  |  |
| AFR-CMS-019 |  |  |  |  |
| AFR-CMS-020 |  |  |  |  |
| AFR-CMS-021 |  |  |  |  |
| AFR-CMS-022 |  |  |  |  |
| AFR-CMS-023 |  |  |  |  |
| AFR-CMS-024 |  |  |  |  |
| AFR-CMS-025 |  |  |  |  |
| AFR-CMS-026 |  |  |  |  |
| AFR-CMS-027 |  |  |  |  |
| AFR-CMS-028 |  |  |  |  |
| AFR-CMS-029 |  |  |  |  |
| AFR-CMS-030 |  |  |  |  |
| AFR-CMS-031 |  |  |  |  |
| AFR-CMS-032 |  |  |  |  |
| AFR-CMS-033 |  |  |  |  |
| AFR-CMS-034 |  |  |  |  |
| AFR-CMS-035 |  |  |  |  |
| AFR-CMS-036 |  |  |  |  |
| AFR-CMS-037 |  |  |  |  |
| AFR-CMS-038 |  |  |  |  |
| AFR-CMS-039 |  |  |  |  |
| AFR-CMS-040 |  |  |  |  |
| AFR-CMS-041 |  |  |  |  |
| AFR-CMS-042 |  |  |  |  |
| AFR-CMS-043 |  |  |  |  |
| AFR-CMS-044 |  |  |  |  |
| AFR-CMS-045 |  |  |  |  |
| AFR-CMS-046 |  |  |  |  |
| AFR-CMS-047 |  |  |  |  |
| AFR-CMS-048 |  |  |  |  |
| AFR-CMS-049 |  |  |  |  |
| AFR-CMS-050 |  |  |  |  |
| AFR-CMS-051 |  |  |  |  |
| AFR-CMS-052 |  |  |  |  |
| AFR-CMS-053 |  |  |  |  |
| AFR-CMS-054 |  |  |  |  |
| AFR-CMS-055 |  |  |  |  |
| AFR-CMS-056 |  |  |  |  |
| AFR-CMS-057 |  |  |  |  |
| AFR-CMS-058 |  |  |  |  |
| AFR-CMS-059 |  |  |  |  |
| AFR-CMS-060 |  |  |  |  |
| AFR-CMS-061 |  |  |  |  |
| AFR-CMS-062 |  |  |  |  |
| AFR-CMS-063 |  |  |  |  |
| AFR-CMS-064 |  |  |  |  |
| AFR-CMS-065 |  |  |  |  |
| AFR-CMS-066 |  |  |  |  |
| AFR-CMS-067 |  |  |  |  |
| AFR-CMS-068 |  |  |  |  |
| AFR-CMS-069 |  |  |  |  |
| AFR-CMS-070 |  |  |  |  |
| AFR-CMS-071 |  |  |  |  |
| AFR-CMS-072 |  |  |  |  |
| AFR-CMS-073 |  |  |  |  |
Open Domain Clarifications Preserved
ISS-CMS-007 — In Progress is recognized but its entry transition is not defined.
ISS-CMS-008 — Approved reopening requires a status update but the exact resulting lifecycle state is not defined.
ISS-CMS-009 — Manual assignment target/ownership semantics are not defined beyond operational handling assignment.
ISS-CMS-010 — Closure behavior when verification is not required is not defined.

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

```


END OF REFERENCES

CURRENT TASK

Generate modules/complaint_cms/apps.py and modules/complaint_cms/registry.py for the Complaint Management System module using the REQUIRED Fusion registry interface shown in modules/placement/registry.py. AppConfig class ComplaintCmsConfig has default_auto_field = "django.db.models.BigAutoField", name = "modules.complaint_cms", label = "complaint_cms", verbose_name = "Complaint Management System". registry.py must define MODULE plain dictionary (code "complaint_cms", label "Complaint Management System", base_path "/complaints", nav_section "Services", icon "WarningCircle", status "active", sort_order 40), NAV_ITEMS list of dictionaries for /complaints/mine (permission complaint_cms.complaint.view_self), /complaints/queue (permission complaint_cms.task.view), /complaints/admin (permission complaint_cms.configuration.manage), PERMISSIONS list of (code,label) tuples with codes complaint_cms.complaint.view_self, complaint_cms.complaint.create, complaint_cms.complaint.review, complaint_cms.complaint.resolve, complaint_cms.complaint.escalate, complaint_cms.task.view, complaint_cms.configuration.manage, complaint_cms.record.manage, ROLE_GRANTS dict mapping student/faculty/staff/Complainant, Caretaker/Warden/Unit Incharge/Section Head/Complaint Authority, and Dean/Registrar/Director/Complaint Administrator to permission lists so every declared permission has a holder, and SYSTEM_PERMISSIONS = []. Do not import views or django.urls in registry.py. Return valid JSON response.

Required output paths:
modules/complaint_cms/apps.py
modules/complaint_cms/registry.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 003 Pure Python domain policy and SLA constants

UTC: 2026-11-01T18:02:20.436753+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1200, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


END OF REFERENCES

CURRENT TASK

Generate only modules/complaint_cms/domain/policy.py as a compact PURE-PYTHON module (max 45 lines). Domain modules must not import Django, DRF, ORM models or Celery. Export COMPLAINT_STATUSES tuple, SEVERITY_SLA_HOURS dict (Mapping low/medium/high/critical to default SLA hours), ALLOWED_TRANSITIONS dict mapping each complaint status to a set of allowed next statuses, can_transition(current_status, next_status) bool helper, and default_sla_hours(severity, fallback_hours=48) int helper. Return raw Python source only without code fences.

Output file: modules/complaint_cms/domain/policy.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 004 Public cross-module contracts

UTC: 2026-11-01T18:02:27.747436+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/directory/contracts.py
```
"""directory's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef
from modules.directory.services.sync import ensure_users_cached


@dataclass(frozen=True)
class UserDTO:
    user_id: int
    username: str
    display_name: str
    kind: str
    email: str = ""
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None
    #: Maintained on the ERP portal's profile page, read here.
    resume_link: str = ""
    profile_completed: bool = False


def _to_dto(r: UserRef) -> UserDTO:
    return UserDTO(
        user_id=r.user_id, username=r.username, display_name=r.display_name,
        kind=r.kind, email=r.email, department=r.department,
        programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
        resume_link=r.resume_link, profile_completed=r.profile_completed,
    )


def get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]:
    """Batched. A missing id is simply absent from the mapping — a visible,
    testable case rather than a silent None three layers up."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    ensure_users_cached(ids)
    return {r.user_id: _to_dto(r) for r in UserRef.objects.filter(user_id__in=ids)}


def user_ids_in_discipline(discipline: str) -> list[int]:
    return list(
        UserRef.objects.filter(discipline=discipline, kind="student", is_active=True)
        .values_list("user_id", flat=True)
    )


def get_employees() -> list[UserDTO]:
    """Everyone on the payroll: faculty and staff, not students."""
    return [
        _to_dto(r)
        for r in UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).order_by("user_id")
    ]


def held_employee_ids() -> set[int]:
    return set(
        UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).values_list("user_id", flat=True)
    )


def employee_projection_disagreement() -> tuple[list[int], list[int]] | None:
    """Where this service and the identity service disagree about the payroll."""
    held = held_employee_ids()
    try:
        known = {r.user_id for r in get_client().iter_employees()}
    except IamUnavailable:
        return None
    return sorted(known - held), sorted(held - known)


def search(q: str = "", kind: str | None = None, limit: int = 25) -> list[UserDTO]:
    qs = UserRef.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(display_name__icontains=q)
    return [_to_dto(r) for r in qs.order_by("display_name")[:limit]]

```


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


END OF REFERENCES

CURRENT TASK

Generate only modules/complaint_cms/contracts.py, maximum 45 lines. Cross-module contract getters must accept a sequence of integer user_ids (Sequence[int]) and use actual models from modules.complaint_cms.models. Define frozen dataclass ComplaintSummary(user_id: int, total_complaints: int, open_complaints: int, resolved_complaints: int) and function get_complaint_summaries_for_users(user_ids: Sequence[int]) -> dict[int, ComplaintSummary]. Return raw Python source only without code fences.

Output file: modules/complaint_cms/contracts.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 005 Complaint query service

UTC: 2026-11-01T18:02:38.265277+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1500, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


### Repository file modules/complaint_cms/registry.py
```
MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'path': '/complaints/mine', 'permission': 'complaint_cms.complaint.view_self'},
    {'path': '/complaints/queue', 'permission': 'complaint_cms.task.view'},
    {'path': '/complaints/admin', 'permission': 'complaint_cms.configuration.manage'},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

Create ONE short Python file, modules/complaint_cms/services/queries.py (maximum 45 lines). It must contain exactly three MODULE-LEVEL functions and no classes: list_complaints(actor), assigned_tasks(actor), and list_notifications(actor). Enforce actor.has_permission("complaint_cms.complaint.view_self") or "complaint_cms.task.view" as appropriate and raise core.api.exceptions.PermissionDeniedError if access is not granted. Return Django QuerySets from Complaint, ComplaintTask and ComplaintNotification filtered by actor.user_id (or all complaints if actor has complaint_cms.complaint.review or complaint_cms.record.manage). Use only existing model classes and fields from modules.complaint_cms.models. Return raw Python source only without code fences.

Output file: modules/complaint_cms/services/queries.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 006 Initial complaint submission service

UTC: 2026-11-01T18:02:46.553142+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2200, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


### Repository file modules/complaint_cms/domain/policy.py
```
from dataclasses import dataclass

COMPLAINT_STATUSES = (
    'Submitted',
    'In Progress',
    'Resolved',
    'Rejected',
    'Closed'
)

SEVERITY_SLA_HOURS = {
    'Low': 16,
    'Medium': 32,
    'High': 48,
    'Critical': 72
}

ALLOWED_TRANSITIONS = {
    'Submitted': {'In Progress'},
    'In Progress': {'Resolved', 'Rejected', 'Closed'},
    'Resolved': {'Closed'},
    'Rejected': {'Closed'}
}

def can_transition(current_status, next_status):
    return next_status in ALLOWED_TRANSITIONS.get(current_status, set())

def default_sla_hours(severity, fallback_hours=48):
    return SEVERITY_SLA_HOURS.get(severity, fallback_hours)

```


### Repository file modules/complaint_cms/registry.py
```
MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'path': '/complaints/mine', 'permission': 'complaint_cms.complaint.view_self'},
    {'path': '/complaints/queue', 'permission': 'complaint_cms.task.view'},
    {'path': '/complaints/admin', 'permission': 'complaint_cms.configuration.manage'},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []
```


### Repository file fusion_auth/principal.py
```
"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    #: Built by the IAM so one sidebar can span every Fusion app.
    navigation: tuple[dict, ...] = ()
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
            navigation=s.navigation,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"

```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

Generate the initial CMS submission service in modules/complaint_cms/services/complaints.py, maximum 75 lines. Define submit_complaint(actor, data) using existing models from modules.complaint_cms.models and domain helpers from modules.complaint_cms.domain.policy. Enforce complaint_cms.complaint.create permission via actor.has_permission (raising PermissionDeniedError from core.api.exceptions), validate required title and description (raising DomainValidationError), look up ComplaintCategory and optional RoutingRule, generate a unique tracking_code, compute sla_due_at using timezone.now() + timedelta(hours=...), and inside transaction.atomic() create the Complaint, initial ComplaintUpdate, initial ComplaintTask, and ComplaintNotification. Return the created Complaint instance. Return raw Python source only without code fences.

Output file: modules/complaint_cms/services/complaints.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 007 Complaint workflow actions service

UTC: 2026-11-01T18:03:04.832364+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


### Repository file modules/complaint_cms/domain/policy.py
```
from dataclasses import dataclass

COMPLAINT_STATUSES = (
    'Submitted',
    'In Progress',
    'Resolved',
    'Rejected',
    'Closed'
)

SEVERITY_SLA_HOURS = {
    'Low': 16,
    'Medium': 32,
    'High': 48,
    'Critical': 72
}

ALLOWED_TRANSITIONS = {
    'Submitted': {'In Progress'},
    'In Progress': {'Resolved', 'Rejected', 'Closed'},
    'Resolved': {'Closed'},
    'Rejected': {'Closed'}
}

def can_transition(current_status, next_status):
    return next_status in ALLOWED_TRANSITIONS.get(current_status, set())

def default_sla_hours(severity, fallback_hours=48):
    return SEVERITY_SLA_HOURS.get(severity, fallback_hours)

```


### Repository file modules/complaint_cms/registry.py
```
MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'path': '/complaints/mine', 'permission': 'complaint_cms.complaint.view_self'},
    {'path': '/complaints/queue', 'permission': 'complaint_cms.task.view'},
    {'path': '/complaints/admin', 'permission': 'complaint_cms.configuration.manage'},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []
```


### Repository file core/api/exceptions.py
```
"""One error envelope for the whole platform:

    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}

`request_id` is always present, so a user reads it off a toast and support
greps one id across the logs.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

from core.observability.middleware import get_request_id


class DomainError(Exception):
    """Base for errors raised by domain/ and services/.

    Deliberately not a DRF exception — a service must stay callable from a
    Celery task or a management command, where HTTP status is noise.
    """

    code = "domain_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "The request could not be processed."

    def __init__(self, message=None, *, code=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class BadRequestError(DomainError):
    """The request itself is malformed — a non-numeric id, an unparseable
    filter. Distinct from ConflictError's 409, which means the request was
    well-formed and the resource refused it."""

    code = "bad_request"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be understood."


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


class ConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource is not in a state that allows this."


class AuthenticationFailedError(DomainError):
    """A credential was rejected: 401 "we do not know who you are", as opposed
    to PermissionDeniedError's 403 "we know, and no". Collapsing the two makes
    an auth outage indistinguishable from a misconfigured grant in the logs."""

    code = "invalid_credentials"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Incorrect username or password."


class PermissionDeniedError(DomainError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


def _envelope(code, message, details, http_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": get_request_id(),
            }
        },
        status=http_status,
    )


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return _envelope(exc.code, exc.message, exc.details, exc.status_code)

    response = drf_handler(exc, context)
    if response is None:
        return None                      # let Django produce the 500

    detail = response.data
    details = []
    if isinstance(detail, dict) and "detail" not in detail:
        details = [
            {"field": f, "message": m[0] if isinstance(m, list) else str(m)}
            for f, m in detail.items()
        ]
        message = "The submitted data was not valid."
        code = "validation_error"
    else:
        message = str(detail.get("detail")) if isinstance(detail, dict) else str(detail)
        code = getattr(exc, "default_code", "error")
    return _envelope(code, message, details, response.status_code)

```


END OF REFERENCES

CURRENT TASK

Generate initial CMS workflow action service in modules/complaint_cms/services/actions.py, maximum 110 lines. Provide act_on_complaint(actor, complaint_id, action, data) supporting actions acknowledge, start_progress, resolve, close, reopen, escalate, assign, and feedback. Reuse existing model fields from modules.complaint_cms.models, permission names from modules.complaint_cms.registry, and error classes from core.api.exceptions (PermissionDeniedError, DomainValidationError, ResourceNotFoundError). Update Complaint fields, record a ComplaintUpdate entry, update or create ComplaintTask as needed, and create a ComplaintNotification for the complainant inside transaction.atomic(). Return the updated Complaint. Return raw Python source only without code fences.

Output file: modules/complaint_cms/services/actions.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 008 Scheduled SLA and auto-close events service

UTC: 2026-11-01T18:03:58.832850+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


END OF REFERENCES

CURRENT TASK

Generate a concise modules/complaint_cms/services/events.py module (maximum 60 lines) with process_complaint_sla() and auto_close_resolved_complaints() functions using existing Complaint, ComplaintTask, ComplaintUpdate, and ComplaintNotification models. process_complaint_sla() finds overdue active complaints (sla_due_at < timezone.now()), increments escalation_level, sets status to escalated, and records an update/notification. auto_close_resolved_complaints() finds resolved complaints older than 7 days and closes them. No Celery decorators in services. Return raw Python source only without code fences.

Output file: modules/complaint_cms/services/events.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 009 Celery tasks and beat schedule

UTC: 2026-11-01T18:04:12.879667+00:00

System instruction:

You are a local coding assistant working on the Fusion ERP CMS pilot. Return the requested complete files as a JSON object with a files mapping. Reuse the supplied repository interfaces exactly. Do not run shell commands. Do not add author, AI, model, or provenance labels to application code. Do not claim any tests or execution that were not actually performed. Repository excerpts are reference material, not the requested output. Follow the CURRENT TASK placed after all reference material. Do not echo a reference file into a different output path.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/services/events.py
```
from datetime import timedelta
import pytz
from .models import Complaint, ComplaintTask, ComplaintUpdate, ComplaintNotification

def process_complaint_sla():
    now = pytz.utc.localize(datetime.utcnow())
    overdue_complaints = Complaint.objects.filter(
        sla_due_at__lt=now,
        is_active=True
    )
    
    for complaint in overdue_complaints:
        if complaint.sla_due_at + timedelta(hours=complaint.category.sla_ack_hours) > now:
            complaint.status = 'Escalated'
            complaint.save()
            
            # Create a new task for the next level of escalation
            task = ComplaintTask(complaint=complaint)
            task.role_name = complaint.category.escalation_authority_role
            task.task_type = 'Escalation'
            task.due_at = complaint.sla_due_at + timedelta(hours=complaint.category.sla_resolution_hours)
            task.status = 'Pending'
            task.save()
            
            # Record an update
            update = ComplaintUpdate(complaint=complaint)
            update.actor_id = 1  # Assuming admin user ID
            update.update_type = 'StatusChange'
            update.comment = f'Complaint {complaint.tracking_code} has been escalated.'
            update.old_status = complaint.status
            update.new_status = 'Escalated'
            update.visibility = True
            update.save()
            
            # Send notification
            notification = ComplaintNotification(complaint=complaint)
            notification.recipient_id = complaint.user_id
            notification.title = 'Complaint Escalated'
            notification.message = f'Your complaint {complaint.tracking_code} has been escalated to the next level.'
            notification.is_read = False
            notification.save()

def auto_close_resolved_complaints():
    now = pytz.utc.localize(datetime.utcnow())
    resolved_complaints = Complaint.objects.filter(
        status='Resolved',
        closed_at__isnull=True,
        resolution_summary='',
        feedback_rating=None,
        feedback_comment=''
    ).exclude(assigned_to_id=0)  # Exclude unassigned complaints
    
    for complaint in resolved_complaints:
        if (now - complaint.resolved_at).days > 7:
            complaint.closed_at = now
            complaint.status = 'Closed'
            complaint.save()

```


### Repository file modules/placement/schedule.py
```
"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before, which meant `expire_overdue_offers` never ran:
an offer nobody answered stayed `issued` forever and kept its student blocked
from the pool, with no way out but a manual database edit.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "placement.deliver_notifications": {"queue": "notifications"},
    "placement.rebuild_active_stats": {"queue": "reports"},
    "placement.rebuild_stats": {"queue": "reports"},
    # Offer expiry stays on default so it never queues behind a report.
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "placement.deliver-notifications": {
        "task": "placement.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # PC-BR-013: five minutes is what a student experiences as the deadline.
    "placement.expire-overdue-offers": {
        "task": "placement.expire_overdue_offers",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # Snapshots back the stats page, so it never reads transactional tables.
    "placement.rebuild-active-stats": {
        "task": "placement.rebuild_active_stats",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}

```


### Repository file config/celery.py
```
import os

from celery import Celery

from modules.placement.schedule import (
    BEAT_SCHEDULE as PLACEMENT_SCHEDULE,
)
from modules.placement.schedule import (
    TASK_ROUTES as PLACEMENT_ROUTES,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
app = Celery("fusion_integrated")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Each module owns its timers; this only merges them, so modules stay removable.
app.conf.beat_schedule = {**PLACEMENT_SCHEDULE}
app.conf.task_routes = {**PLACEMENT_ROUTES}

```


END OF REFERENCES

CURRENT TASK

Generate modules/complaint_cms/tasks.py and modules/complaint_cms/schedule.py, max 50 lines total. tasks.py defines Celery @shared_task wrappers cms_process_sla and cms_auto_close_resolved calling process_complaint_sla and auto_close_resolved_complaints from modules.complaint_cms.services.events. schedule.py imports crontab from celery.schedules and exports BEAT_SCHEDULE (running cms_process_sla every 15 minutes and cms_auto_close_resolved daily at midnight) and TASK_ROUTES mapping "modules.complaint_cms.tasks.*" to {"queue": "default"}. Return valid JSON response.

Required output paths:
modules/complaint_cms/tasks.py
modules/complaint_cms/schedule.py

The JSON must have exactly this shape: {"files": {"relative/path": "complete file content"}}. Return every required file. Do not put the JSON in a Markdown fence. Do not echo reference-file contents into the wrong output file.


## Prompt 010 DRF API serializers

UTC: 2026-11-01T18:04:26.295127+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


END OF REFERENCES

CURRENT TASK

Generate modules/complaint_cms/api/serializers.py using DRF ModelSerializer, maximum 85 lines. Define classes ComplaintCategorySerializer, RoutingRuleSerializer, ComplaintSerializer, ComplaintTaskSerializer, ComplaintUpdateSerializer, and ComplaintNotificationSerializer for the exact models in modules.complaint_cms.models. Use fields = "__all__" and mark server-managed fields on ComplaintSerializer (id, tracking_code, user_id, status, assigned_to_id, assigned_role, escalation_level, sla_due_at, resolved_at, closed_at, reopen_count, created_at, updated_at) in read_only_fields. No service code or new models. Return raw Python source only without code fences.

Output file: modules/complaint_cms/api/serializers.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 011 Employee and action API views

UTC: 2026-11-01T18:04:50.329927+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/services/queries.py
```
from django.db import models
from .models import Complaint, ComplaintTask, ComplaintNotification
from .registry import PERMISSIONS

def list_complaints(actor):
    if not actor.has_any_permission(*PERMISSIONS[:2]):
        raise PermissionDeniedError()
    return Complaint.objects.filter(user_id=actor.user_id)

def assigned_tasks(actor):
    if not actor.has_permission("complaint_cms.task.view"):
        raise PermissionDeniedError()
    return ComplaintTask.objects.filter(assigned_to_id=actor.user_id)

def list_notifications(actor):
    if not actor.has_permission("complaint_cms.configuration.manage"):
        raise PermissionDeniedError()
    return ComplaintNotification.objects.all()

```


### Repository file modules/complaint_cms/services/complaints.py
```
from datetime import datetime, timedelta
import uuid
from django.db import transaction
from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintRoutingRule,
    ComplaintAttachment,
    ComplaintUpdate,
    ComplaintTask,
    ComplaintNotification
)
from .domain.policy import can_transition, default_sla_hours
from .exceptions import BadRequestError, NotFoundError

def submit_complaint(actor, data):
    if not actor.has_permission('complaint_cms.complaint.create'):
        raise PermissionDeniedError()

    try:
        category = ComplaintCategory.objects.get(code=data['category'])
    except ComplaintCategory.DoesNotExist:
        raise NotFoundError("Complaint category not found")

    routing_rule = None
    if 'routing_rule' in data:
        try:
            routing_rule = ComplaintRoutingRule.objects.get(category_id=category.id)
        except ComplaintRoutingRule.DoesNotExist:
            pass

    title = data.get('title', '')
    description = data.get('description', '')

    if not (title and description):
        raise BadRequestError(message="Title and description are required")

    tracking_code = str(uuid.uuid4()).replace('-', '').upper()[:10]
    sla_due_at = datetime.now().astimezone() + timedelta(hours=default_sla_hours(category.severity_default))

    with transaction.atomic():
        complaint = Complaint(
            tracking_code=tracking_code,
            user_id=actor.user_id,
            is_anonymous=False,
            category=category,
            title=title,
            description=description,
            location_type=data.get('location_type'),
            location_details=data.get('location_details'),
            severity=data.get('severity', 2),
            status='Submitted',
            escalation_level=1,
            sla_due_at=sla_due_at
        )
        complaint.save()

        update = ComplaintUpdate(
            complaint=complaint,
            actor_id=actor.user_id,
            update_type='Comment',
            comment=f"Complaint submitted by {actor.username}",
            visibility=True
        )
        update.save()

        task = ComplaintTask(
            complaint=complaint,
            assigned_to_id=None,
            role_name='',
            task_type='',
            status='Pending',
            due_at=datetime.now().astimezone()
        )
        task.save()

        notification = ComplaintNotification(
            complaint=complaint,
            recipient_id=actor.user_id,
            title="New Complaint Submitted",
            message=f"A new complaint has been submitted: {title}",
            is_read=False
        )
        notification.save()

    return complaint

```


### Repository file modules/complaint_cms/services/actions.py
```
from django.db import models, transaction
from rest_framework.exceptions import PermissionDeniedError, ValidationError
from .models import Complaint, ComplaintCategory, RoutingRule, UserScopedModel
from .registry import PERMISSIONS
from .exceptions import DomainValidationError, ResourceNotFoundError
import datetime

def get_user_role(user):
    # Placeholder function to determine user role based on user ID
    return "student/faculty/staff"  # Example role

def can_perform_action(user, complaint, action):
    if not user.is_authenticated:
        raise AuthenticationFailedError()

    required_permission = f"{MODULE['code']}.{action}"
    if required_permission not in PERMISSIONS:
        raise PermissionDeniedError(f"Action '{action}' is not allowed.")

    if action == 'assign':
        assigned_to_id = data.get('assigned_to_id')
        if assigned_to_id != user.id:
            raise PermissionDeniedError("Only the assignee can perform this action.")
    
    elif action == 'feedback' and complaint.status != 'Resolved':
        raise PermissionDeniedError("Feedback can be provided only for resolved complaints.")

def act_on_complaint(actor, complaint_id, action, data=None):
    try:
        with transaction.atomic():
            complaint = Complaint.objects.select_for_update().get(id=complaint_id)
            
            if complaint.user_id != actor.id:
                raise PermissionDeniedError("You do not have permission to perform this action.")
                
            can_perform_action(actor, complaint, action)

            if action == 'acknowledge':
                complaint.status = 'In Progress'
                complaint.escalation_level = 1
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.save()
                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint acknowledged by {actor.username}.",
                    old_status='Submitted',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'start_progress':
                complaint.status = 'In Progress'
                complaint.escalation_level = 1
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.save()
                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint started in progress by {actor.username}.",
                    old_status='Submitted',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'resolve':
                complaint.status = 'Resolved'
                complaint.resolved_at = datetime.datetime.now()
                complaint.resolution_summary = data.get('resolution_summary', '')
                complaint.feedback_rating = data.get('feedback_rating')
                complaint.feedback_comment = data.get('feedback_comment')
                complaint.save()
                
                if complaint.category.is_active:
                    routing_rule = RoutingRule.objects.filter(category=complaint.category).first()
                    target_section = routing_rule.target_section
                    
                    # Create or update a task for the assigned section
                    task, created = ComplaintTask.objects.update_or_create(
                        complaint=complaint,
                        defaults={
                            'assigned_to_id': complaint.user_id,
                            'role_name': get_user_role(actor),
                            'task_type': 'Resolution',
                            'status': 'Pending',
                            'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                        }
                    )

                    if not created and task.assigned_to_id != complaint.user_id:
                        raise PermissionDeniedError("Only the assignee can perform this action.")

                    update_entry = ComplaintUpdate(
                        complaint=complaint,
                        actor_id=actor.id,
                        update_type='StatusChange',
                        visibility=True,
                        comment=f"Complaint resolved by {actor.username}.",
                        old_status='In Progress',
                        new_status='Resolved'
                    )
                    update_entry.save()

            elif action == 'close':
                complaint.status = 'Closed'
                complaint.closed_at = datetime.datetime.now()
                complaint.resolution_summary = data.get('resolution_summary', '')
                complaint.feedback_rating = data.get('feedback_rating')
                complaint.feedback_comment = data.get('feedback_comment')
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint closed by {actor.username}.",
                    old_status='Resolved',
                    new_status='Closed'
                )
                update_entry.save()

            elif action == 'reopen':
                complaint.status = 'Submitted'
                complaint.reopen_count += 1
                complaint.sla_due_at = None
                complaint.resolved_at = None
                complaint.feedback_rating = None
                complaint.feedback_comment = None
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint reopened by {actor.username}.",
                    old_status='Closed',
                    new_status='Submitted'
                )
                update_entry.save()

            elif action == 'escalate':
                if complaint.escalation_level >= 3:
                    raise PermissionDeniedError("Maximum escalation level reached.")

                routing_rule = RoutingRule.objects.filter(category=complaint.category).first()
                target_section = routing_rule.target_section
                
                # Create or update a task for the assigned section
                task, created = ComplaintTask.objects.update_or_create(
                    complaint=complaint,
                    defaults={
                        'assigned_to_id': complaint.user_id,
                        'role_name': get_user_role(actor),
                        'task_type': 'Escalation',
                        'status': 'Pending',
                        'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                    }
                )

                if not created and task.assigned_to_id != complaint.user_id:
                    raise PermissionDeniedError("Only the assignee can perform this action.")

                complaint.status = 'In Progress'
                complaint.sla_due_at = datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity])
                complaint.escalation_level += 1
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint escalated by {actor.username}.",
                    old_status='Resolved',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'assign':
                assigned_to_id = data.get('assigned_to_id')
                if assigned_to_id is None or assigned_to_id <= 0:
                    raise ValidationError({"assigned_to_id": "Invalid user ID."})
                
                try:
                    assigned_user = UserScopedModel.objects.select_for_update().get(id=assigned_to_id)
                except UserScopedModel.DoesNotExist:
                    raise ResourceNotFoundError(f"User with ID {assigned_to_id} does not exist.")
                    
                complaint.assigned_to_id = assigned_to_id
                complaint.assigned_role = get_user_role(assigned_user)
                complaint.save()
                
                task, created = ComplaintTask.objects.update_or_create(
                    complaint=complaint,
                    defaults={
                        'assigned_to_id': assigned_to_id,
                        'role_name': get_user_role(assigned_user),
                        'task_type': 'Assignment',
                        'status': 'Pending',
                        'due_at': datetime.datetime.now() + datetime.timedelta(hours=SEVERITY_SLA_HOURS[complaint.severity]),
                    }
                )

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='StatusChange',
                    visibility=True,
                    comment=f"Complaint assigned to {assigned_user.username} by {actor.username}.",
                    old_status='In Progress',
                    new_status='In Progress'
                )
                update_entry.save()

            elif action == 'feedback':
                if complaint.status != 'Resolved':
                    raise PermissionDeniedError("Feedback can be provided only for resolved complaints.")

                feedback_rating = data.get('feedback_rating')
                feedback_comment = data.get('feedback_comment')

                complaint.feedback_rating = feedback_rating
                complaint.feedback_comment = feedback_comment
                complaint.save()

                update_entry = ComplaintUpdate(
                    complaint=complaint,
                    actor_id=actor.id,
                    update_type='Comment',
                    visibility=True,
                    comment=f"Feedback submitted by {actor.username}: Rating - {feedback_rating}, Comment - '{feedback_comment}'.",
                    old_status=None,
                    new_status=None
                )
                update_entry.save()
                
                # Create a notification for the complainant
                Notification.objects.create(
                    recipient_id=complaint.user_id,
                    title="Feedback Submitted",
                    message=f"You have received feedback on your complaint. Please review it.",
                    is_read=False
                )

        return complaint

    except DomainValidationError as e:
        raise ValidationError(e)
    
    except ResourceNotFoundError as e:
        raise ResourceNotFoundError(e)

    except Exception as e:
        raise DomainError(str(e))

```


### Repository file modules/complaint_cms/api/serializers.py
```
from rest_framework import serializers
from .models import (
    ComplaintCategory,
    RoutingRule,
    Complaint,
    ComplaintAttachment,
    ComplaintUpdate,
    ComplaintTask,
    ComplaintNotification
)


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = "__all__"


class RoutingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    tracking_code = serializers.CharField(max_length=100, read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    assigned_role = serializers.CharField(max_length=100, blank=True, read_only=True)
    escalation_level = serializers.PositiveIntegerField(default=1, read_only=True)
    sla_due_at = serializers.DateTimeField(null=True, read_only=True)
    resolved_at = serializers.DateTimeField(null=True, read_only=True)
    closed_at = serializers.DateTimeField(null=True, read_only=True)
    reopen_count = serializers.PositiveIntegerField(default=0, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Complaint
        fields = "__all__"

class ComplaintTaskSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    id = serializers.IntegerField(read_only=True)
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    role_name = serializers.CharField(max_length=100, blank=True, read_only=True)
    task_type = serializers.CharField(max_length=100, blank=True, read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = serializers.DateTimeField(null=True, read_only=True)
    completed_at = serializers.DateTimeField(null=True, read_only=True)

    class Meta:
        model = ComplaintTask
        fields = "__all__"


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    actor_id = serializers.IntegerField(db_index=True, read_only=True)
    update_type = serializers.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = serializers.BooleanField(default=False, read_only=True)
    comment = serializers.TextField()
    old_status = serializers.CharField(max_length=10, null=True, read_only=True)
    new_status = serializers.CharField(max_length=10, null=True, read_only=True)

    class Meta:
        model = ComplaintUpdate
        fields = "__all__"

class ComplaintNotificationSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    recipient_id = serializers.IntegerField(db_index=True, read_only=True)
    title = serializers.CharField(max_length=255, read_only=True)
    message = serializers.TextField(read_only=True)
    is_read = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = ComplaintNotification
        fields = "__all__"

```


### Repository file fusion_auth/permissions.py
```
"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})

```


### Repository file modules/complaint_cms/registry.py
```
MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'path': '/complaints/mine', 'permission': 'complaint_cms.complaint.view_self'},
    {'path': '/complaints/queue', 'permission': 'complaint_cms.task.view'},
    {'path': '/complaints/admin', 'permission': 'complaint_cms.configuration.manage'},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []
```


END OF REFERENCES

CURRENT TASK

Generate one concise DRF APIView file at modules/complaint_cms/api/views.py, maximum 95 lines. ComplaintListView GET calls list_complaints(request.principal) serialized with ComplaintSerializer(many=True), POST validates ComplaintSerializer and calls submit_complaint(request.principal, serializer.validated_data). TaskListView GET calls assigned_tasks(request.principal) serialized with ComplaintTaskSerializer(many=True). NotificationListView GET calls list_notifications(request.principal) serialized with ComplaintNotificationSerializer(many=True). ComplaintActionView POST calls act_on_complaint(request.principal, pk, str(request.data.get("action", "")), request.data) and returns ComplaintSerializer(complaint).data. Use IsAuthenticated, HasModuleGrant("complaint_cms"), and HasPermission class factories in permission_classes, and annotate methods with @extend_schema from drf_spectacular.utils. Return raw Python source only without code fences.

Output file: modules/complaint_cms/api/views.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 012 Configuration and record API views

UTC: 2026-11-01T18:05:23.074317+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2400, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


### Repository file modules/complaint_cms/api/serializers.py
```
from rest_framework import serializers
from .models import (
    ComplaintCategory,
    RoutingRule,
    Complaint,
    ComplaintAttachment,
    ComplaintUpdate,
    ComplaintTask,
    ComplaintNotification
)


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = "__all__"


class RoutingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    tracking_code = serializers.CharField(max_length=100, read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    assigned_role = serializers.CharField(max_length=100, blank=True, read_only=True)
    escalation_level = serializers.PositiveIntegerField(default=1, read_only=True)
    sla_due_at = serializers.DateTimeField(null=True, read_only=True)
    resolved_at = serializers.DateTimeField(null=True, read_only=True)
    closed_at = serializers.DateTimeField(null=True, read_only=True)
    reopen_count = serializers.PositiveIntegerField(default=0, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Complaint
        fields = "__all__"

class ComplaintTaskSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    id = serializers.IntegerField(read_only=True)
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    role_name = serializers.CharField(max_length=100, blank=True, read_only=True)
    task_type = serializers.CharField(max_length=100, blank=True, read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = serializers.DateTimeField(null=True, read_only=True)
    completed_at = serializers.DateTimeField(null=True, read_only=True)

    class Meta:
        model = ComplaintTask
        fields = "__all__"


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    actor_id = serializers.IntegerField(db_index=True, read_only=True)
    update_type = serializers.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = serializers.BooleanField(default=False, read_only=True)
    comment = serializers.TextField()
    old_status = serializers.CharField(max_length=10, null=True, read_only=True)
    new_status = serializers.CharField(max_length=10, null=True, read_only=True)

    class Meta:
        model = ComplaintUpdate
        fields = "__all__"

class ComplaintNotificationSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    recipient_id = serializers.IntegerField(db_index=True, read_only=True)
    title = serializers.CharField(max_length=255, read_only=True)
    message = serializers.TextField(read_only=True)
    is_read = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = ComplaintNotification
        fields = "__all__"

```


### Repository file fusion_auth/permissions.py
```
"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})

```


END OF REFERENCES

CURRENT TASK

Generate a compact DRF API view file at modules/complaint_cms/api/configuration.py (max 90 lines) providing ConfigurationView (GET returns categories and routing_rules using ComplaintCategorySerializer and RoutingRuleSerializer; POST creates or updates a ComplaintCategory or RoutingRule) and RecordListView (GET returns recent ComplaintUpdate and ComplaintNotification records serialized with ComplaintUpdateSerializer and ComplaintNotificationSerializer). Use IsAuthenticated, HasModuleGrant("complaint_cms"), and HasPermission("complaint_cms.configuration.manage") / HasPermission("complaint_cms.record.manage") in permission_classes, and @extend_schema on view methods. Return raw Python source only without code fences.

Output file: modules/complaint_cms/api/configuration.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 013 API URL registration

UTC: 2026-11-01T18:05:38.386483+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/api/views.py
```
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .services.queries import list_complaints, assigned_tasks, list_notifications
from .services.complaints import submit_complaint
from .services.actions import act_on_complaint
from .serializers import (
    ComplaintCategorySerializer,
    RoutingRuleSerializer,
    ComplaintSerializer,
    ComplaintTaskSerializer,
    ComplaintUpdateSerializer,
    ComplaintNotificationSerializer
)
from drf_spectacular.utils import extend_schema

class ComplaintListView(APIView):
    permission_classes = [IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission('complaint_cms.complaint.view_self')]

    def get(self, request):
        complaints = list_complaints(request.principal)
        serializer = ComplaintSerializer(complaints, many=True)
        return Response(serializer.data)

class TaskListView(APIView):
    permission_classes = [IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission('complaint_cms.task.view')]

    def get(self, request):
        tasks = assigned_tasks(request.principal)
        serializer = ComplaintTaskSerializer(tasks, many=True)
        return Response(serializer.data)

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission('complaint_cms.configuration.manage')]

    def get(self, request):
        notifications = list_notifications(request.principal)
        serializer = ComplaintNotificationSerializer(notifications, many=True)
        return Response(serializer.data)

@extend_schema(responses={201: ComplaintSerializer})
class ComplaintActionView(APIView):
    permission_classes = [IsAuthenticated, HasModuleGrant("complaint_cms")]

    def post(self, request, pk=None):
        action = request.data.get("action", "")
        complaint_id = int(pk) if pk else None
        complaint = act_on_complaint(request.principal, complaint_id, action, request.data)
        serializer = ComplaintSerializer(complaint)
        return Response(serializer.data)

```


### Repository file modules/complaint_cms/api/configuration.py
```
from rest_framework import generics, permissions
from .models import ComplaintCategory, RoutingRule, ComplaintUpdate, ComplaintNotification
from .serializers import (
    ComplaintCategorySerializer,
    RoutingRuleSerializer,
    ComplaintUpdateSerializer,
    ComplaintNotificationSerializer
)
from drf_spectacular.utils import extend_schema
from django.contrib.auth.decorators import login_required

class ConfigurationView(generics.ListCreateAPIView):
    queryset = ComplaintCategory.objects.all() | RoutingRule.objects.all()
    serializer_class = ComplaintCategorySerializer if request.method == 'POST' else RoutingRuleSerializer
    permission_classes = [permissions.IsAuthenticated, HasModuleGrant("complaint_cms"), HasPermission("complaint_cms.configuration.manage")]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

@extend_schema(responses={200: ComplaintUpdateSerializer(many=True)})
@login_required
def record_list_view(request):
    updates = ComplaintUpdate.objects.order_by('-created_at')[:10]
    notifications = ComplaintNotification.objects.order_by('-created_at')[:10]
    data = list(updates) + list(notifications)
    return Response(data)

```


END OF REFERENCES

CURRENT TASK

Generate modules/complaint_cms/api/urls.py only, concise urlpatterns for paths without trailing slash: "complaints" -> ComplaintListView, "tasks" -> TaskListView, "notifications" -> NotificationListView, "complaints/<int:pk>/action" -> ComplaintActionView, "configuration" -> ConfigurationView, "records" -> RecordListView. Import the view classes from .views and .configuration. Return raw Python source only without code fences.

Output file: modules/complaint_cms/api/urls.py
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 014 Frontend TypeScript interfaces

UTC: 2026-11-01T18:05:57.667511+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/models.py
```
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserScopedModel(models.Model):
    user_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True


@dataclass(frozen=True)
class Principal:
    pass  # Placeholder for the principal object as it's not defined in this context


class ComplaintCategory(TimeStampedModel, UserScopedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    description = models.TextField()
    severity_default = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    sla_ack_hours = models.PositiveIntegerField(default=48)
    sla_resolution_hours = models.PositiveIntegerField(default=72)
    is_active = models.BooleanField(default=True)


class RoutingRule(TimeStampedModel, UserScopedModel):
    category = models.ForeignKey('ComplaintCategory', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=100)
    target_section = models.CharField(max_length=255)
    primary_authority_role = models.CharField(max_length=100)
    escalation_authority_role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


class Complaint(TimeStampedModel, UserScopedModel):
    tracking_code = models.CharField(max_length=100, unique=True)
    user_id = models.IntegerField(db_index=True)
    is_anonymous = models.BooleanField(default=False)
    category = models.ForeignKey('ComplaintCategory', on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location_type = models.CharField(max_length=100)
    location_details = models.TextField(blank=True)
    severity = models.PositiveIntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    status = models.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    escalation_level = models.PositiveIntegerField(default=1)
    sla_due_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    resolution_summary = models.TextField(blank=True)
    reopen_count = models.PositiveIntegerField(default=0)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)


class ComplaintAttachment(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    uploaded_by_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.URLField()
    stage = models.CharField(max_length=100, default='Initial')


class ComplaintUpdate(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    actor_id = models.IntegerField(db_index=True)
    update_type = models.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = models.BooleanField(default=False)
    comment = models.TextField()
    old_status = models.CharField(max_length=10, null=True)
    new_status = models.CharField(max_length=10, null=True)


class ComplaintTask(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    assigned_to_id = models.IntegerField(null=True, db_index=True)
    role_name = models.CharField(max_length=100, blank=True)
    task_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)


class ComplaintNotification(TimeStampedModel):
    complaint = models.ForeignKey('Complaint', on_delete=models.CASCADE)
    recipient_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

```


### Repository file modules/complaint_cms/api/serializers.py
```
from rest_framework import serializers
from .models import (
    ComplaintCategory,
    RoutingRule,
    Complaint,
    ComplaintAttachment,
    ComplaintUpdate,
    ComplaintTask,
    ComplaintNotification
)


class ComplaintCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintCategory
        fields = "__all__"


class RoutingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = "__all__"


class ComplaintSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    tracking_code = serializers.CharField(max_length=100, read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Submitted', 'Submitted'),
            ('In Progress', 'In Progress'),
            ('Resolved', 'Resolved'),
            ('Rejected', 'Rejected'),
            ('Closed', 'Closed')
        ],
        default='Submitted'
    )
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    assigned_role = serializers.CharField(max_length=100, blank=True, read_only=True)
    escalation_level = serializers.PositiveIntegerField(default=1, read_only=True)
    sla_due_at = serializers.DateTimeField(null=True, read_only=True)
    resolved_at = serializers.DateTimeField(null=True, read_only=True)
    closed_at = serializers.DateTimeField(null=True, read_only=True)
    reopen_count = serializers.PositiveIntegerField(default=0, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Complaint
        fields = "__all__"

class ComplaintTaskSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    id = serializers.IntegerField(read_only=True)
    assigned_to_id = serializers.IntegerField(null=True, db_index=True, read_only=True)
    role_name = serializers.CharField(max_length=100, blank=True, read_only=True)
    task_type = serializers.CharField(max_length=100, blank=True, read_only=True)
    status = serializers.CharField(
        max_length=10,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed')
        ],
        default='Pending'
    )
    due_at = serializers.DateTimeField(null=True, read_only=True)
    completed_at = serializers.DateTimeField(null=True, read_only=True)

    class Meta:
        model = ComplaintTask
        fields = "__all__"


class ComplaintUpdateSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    actor_id = serializers.IntegerField(db_index=True, read_only=True)
    update_type = serializers.CharField(
        max_length=10,
        choices=[
            ('Comment', 'Comment'),
            ('StatusChange', 'Status Change')
        ]
    )
    visibility = serializers.BooleanField(default=False, read_only=True)
    comment = serializers.TextField()
    old_status = serializers.CharField(max_length=10, null=True, read_only=True)
    new_status = serializers.CharField(max_length=10, null=True, read_only=True)

    class Meta:
        model = ComplaintUpdate
        fields = "__all__"

class ComplaintNotificationSerializer(serializers.ModelSerializer):
    complaint = serializers.PrimaryKeyRelatedField(queryset=Complaint.objects.all())
    recipient_id = serializers.IntegerField(db_index=True, read_only=True)
    title = serializers.CharField(max_length=255, read_only=True)
    message = serializers.TextField(read_only=True)
    is_read = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = ComplaintNotification
        fields = "__all__"

```


END OF REFERENCES

CURRENT TASK

Generate only client/src/modules/complaint_cms/types.ts, max 85 lines, with exported TypeScript interfaces matching the backend serializer/model fields: ComplaintCategory, RoutingRule, Complaint, NewComplaint, ComplaintTask, ComplaintUpdateRecord, ComplaintNotificationRecord, and ConfigurationResponse ({ categories: ComplaintCategory[]; routing_rules: RoutingRule[] }). No runtime code. Return raw TypeScript source only without code fences.

Output file: client/src/modules/complaint_cms/types.ts
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 015 Frontend typed API client

UTC: 2026-11-01T18:06:10.979648+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/complaint_cms/types.ts
```
export interface ComplaintCategory {
  id?: number;
  code: string;
  name: string;
  description: string;
  severity_default: number;
  sla_ack_hours: number;
  sla_resolution_hours: number;
  is_active: boolean;
}

export interface RoutingRule {
  id?: number;
  category_id: number;
  location_type: string;
  target_section: string;
  primary_authority_role: string;
  escalation_authority_role: string;
  is_active: boolean;
}

export interface Complaint {
  id?: number;
  tracking_code: string;
  user_id: number;
  status: string;
  assigned_to_id?: number;
  assigned_role: string;
  escalation_level: number;
  sla_due_at?: Date;
  resolved_at?: Date;
  closed_at?: Date;
  reopen_count: number;
  created_at: Date;
  updated_at: Date;
}

export type NewComplaint = Omit<Complaint, 'id'>;

export interface ComplaintTask {
  id?: number;
  complaint_id: number;
  assigned_to_id?: number;
  role_name: string;
  task_type: string;
  status: string;
  due_at?: Date;
  completed_at?: Date;
}

export interface ComplaintUpdateRecord {
  id?: number;
  complaint_id: number;
  actor_id: number;
  update_type: string;
  visibility: boolean;
  comment: string;
  old_status?: string;
  new_status?: string;
}

export interface ComplaintNotificationRecord {
  id?: number;
  complaint_id: number;
  recipient_id: number;
  title: string;
  message: string;
  is_read: boolean;
}

export interface ConfigurationResponse {
  categories: ComplaintCategory[];
  routing_rules: RoutingRule[];
}

```


### Repository file modules/complaint_cms/api/urls.py
```
from django.urls import path
from .api.views import (
    ComplaintListView,
    TaskListView,
    NotificationListView,
    ComplaintActionView,
    ConfigurationView,
    RecordListView
)

urlpatterns = [
    path('complaints/', ComplaintListView.as_view(), name='complaint-list'),
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('complaints/<int:pk>/action', ComplaintActionView.as_view(), name='complaint-action'),
    path('configuration/', ConfigurationView.as_view(), name='configuration-view'),
    path('records/', RecordListView.as_view(), name='record-list')
]

```


### Repository file client/src/lib/http.ts
```
/** One axios instance for the whole app, with the interceptors the legacy
 *  academic SPA never had. */
import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,          // the session cookie, never a JS-readable token
  timeout: 15000,
});

/** Paired with the session cookie. Held in memory rather than a readable
 *  cookie, which the SPA could not read cross-origin in development. */
let csrfToken = "";
export function setCsrfToken(value: string) {
  csrfToken = value ?? "";
}

const UNSAFE = new Set(["post", "put", "patch", "delete"]);

http.interceptors.request.use((config) => {
  if (csrfToken && UNSAFE.has((config.method ?? "get").toLowerCase())) {
    config.headers.set("X-CSRF-Token", csrfToken);
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

http.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) onUnauthorized?.();
    return Promise.reject(error);
  },
);

/** Pull a usable message out of the platform's error envelope. */
export function errorMessage(e: unknown): string {
  const env = (e as { response?: { data?: { error?: {
    message?: string; details?: { message?: string }[] } } } })
    ?.response?.data?.error;
  if (!env) return "Something went wrong. Please try again.";
  if (env.details?.length) {
    return env.details.map((d) => d.message).filter(Boolean).join(" ") ||
      env.message || "Request failed.";
  }
  return env.message ?? "Request failed.";
}

/** A `responseType: "blob"` request delivers the *error* body as a Blob too,
 *  which hides the envelope from errorMessage. Read it back before rethrowing. */
export async function readBlobError(e: unknown): Promise<unknown> {
  const res = (e as { response?: { data?: unknown } })?.response;
  if (res?.data instanceof Blob) {
    try {
      res.data = JSON.parse(await res.data.text());
    } catch {
      res.data = undefined;             // an HTML page, not our envelope
    }
  }
  return e;
}

export function errorStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } })?.response?.status;
}

export function requestId(e: unknown): string | undefined {
  return (e as { response?: { data?: { error?: { request_id?: string } } } })
    ?.response?.data?.error?.request_id;
}

```


END OF REFERENCES

CURRENT TASK

Generate a compact TypeScript client/src/modules/complaint_cms/api.ts file (max 75 lines). Import { http } from "../../lib/http" and re-export types from "./types". Export async functions listComplaints(), submitComplaint(payload: NewComplaint), listTasks(), listNotifications(), complaintAction(id: number, action: string, data?: Record<string, unknown>), getConfiguration(), saveConfiguration(payload: Record<string, unknown>), and getRecords() calling the /complaints/... endpoints exposed by modules/complaint_cms/api/urls.py. Return raw TypeScript source only without code fences.

Output file: client/src/modules/complaint_cms/api.ts
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 016 Frontend route registration

UTC: 2026-11-01T18:06:24.341692+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1000, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/placement/routes.tsx
```
import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const PostingsPage = lazy(() => import("./pages/PostingsPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const OffersPage = lazy(() => import("./pages/OffersPage"));
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"));
const InterviewsPage = lazy(() => import("./pages/InterviewsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const StudentCpiPage = lazy(() => import("./pages/StudentCpiPage"));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage"));
const RegistrationApprovalsPage = lazy(
  () => import("./pages/RegistrationApprovalsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="postings" replace /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "registration-approvals", element: <RegistrationApprovalsPage /> },
  { path: "postings", element: <PostingsPage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "offers", element: <OffersPage /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "companies", element: <CompaniesPage /> },
  { path: "interviews", element: <InterviewsPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "students-cpi", element: <StudentCpiPage /> },
  { path: "reports", element: <ReportsPage /> },
];

```


END OF REFERENCES

CURRENT TASK

Generate client/src/modules/complaint_cms/routes.tsx only, exporting const routes: RouteObject[] with index Navigate to "mine", path "mine" rendering MyComplaintsPage, path "queue" rendering ComplaintQueuePage, and path "admin" rendering ComplaintAdminPage using React.lazy imports from ./pages/*. Return raw TypeScript JSX source only without code fences.

Output file: client/src/modules/complaint_cms/routes.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 017 Initial complainant page

UTC: 2026-11-01T18:06:31.031595+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/complaint_cms/api.ts
```
import { http } from '../../lib/http';
import type * as T from './types';

async function listComplaints(): Promise<T.Complaint[]> {
  const res = await http.get('/complaints/');
  return res.data;
}

async function submitComplaint(payload: T.NewComplaint): Promise<void> {
  await http.post('/complaints/', payload);
}

async function listTasks(complaintId: number): Promise<T.ComplaintTask[]> {
  const res = await http.get(`/complaints/${complaintId}/tasks`);
  return res.data;
}

async function listNotifications(complaintId: number): Promise<T.ComplaintNotificationRecord[]> {
  const res = await http.get(`/complaints/${complaintId}/notifications`);
  return res.data;
}

async function complaintAction(
  id: number,
  action: string,
  data?: Record<string, unknown>
): Promise<void> {
  await http.patch(`/complaints/${id}/action`, { action, ...data });
}

async function getConfiguration(): Promise<T.ConfigurationResponse> {
  const res = await http.get('/configuration/');
  return res.data;
}

async function saveConfiguration(payload: Record<string, unknown>): Promise<void> {
  await http.put('/configuration/', payload);
}

async function getRecords(): Promise<T.RecordListView[]> {
  const res = await http.get('/records/');
  return res.data;
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React 18 / Mantine 7 page component at client/src/modules/complaint_cms/pages/MyComplaintsPage.tsx with default export function MyComplaintsPage (max 110 lines). Use React Query v5 object-form useQuery and useMutation with useQueryClient from @tanstack/react-query. Import listComplaints, submitComplaint, complaintAction, getConfiguration, and NewComplaint from ../api, PageHeader from ../../../ui/components/PageHeader, and errorMessage from ../../../lib/http. Render a form to lodge a complaint (category, title, description, location_type, location_details, severity) calling submitComplaint, and a Mantine Table of the user's complaints with tracking_code, title, severity, status, and action buttons for reopen and feedback calling complaintAction. Ensure all imports are used so TypeScript noUnusedLocals passes. Return complete raw TypeScript JSX source only without code fences.

Output file: client/src/modules/complaint_cms/pages/MyComplaintsPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 018 Initial authority work queue page

UTC: 2026-11-01T18:07:09.473189+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/complaint_cms/api.ts
```
import { http } from '../../lib/http';
import type * as T from './types';

async function listComplaints(): Promise<T.Complaint[]> {
  const res = await http.get('/complaints/');
  return res.data;
}

async function submitComplaint(payload: T.NewComplaint): Promise<void> {
  await http.post('/complaints/', payload);
}

async function listTasks(complaintId: number): Promise<T.ComplaintTask[]> {
  const res = await http.get(`/complaints/${complaintId}/tasks`);
  return res.data;
}

async function listNotifications(complaintId: number): Promise<T.ComplaintNotificationRecord[]> {
  const res = await http.get(`/complaints/${complaintId}/notifications`);
  return res.data;
}

async function complaintAction(
  id: number,
  action: string,
  data?: Record<string, unknown>
): Promise<void> {
  await http.patch(`/complaints/${id}/action`, { action, ...data });
}

async function getConfiguration(): Promise<T.ConfigurationResponse> {
  const res = await http.get('/configuration/');
  return res.data;
}

async function saveConfiguration(payload: Record<string, unknown>): Promise<void> {
  await http.put('/configuration/', payload);
}

async function getRecords(): Promise<T.RecordListView[]> {
  const res = await http.get('/records/');
  return res.data;
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React 18 / Mantine 7 page component at client/src/modules/complaint_cms/pages/ComplaintQueuePage.tsx with default export function ComplaintQueuePage (max 110 lines). Use React Query v5 object-form useQuery and useMutation with useQueryClient from @tanstack/react-query. Import listTasks, listComplaints, and complaintAction from ../api, PageHeader from ../../../ui/components/PageHeader, and errorMessage from ../../../lib/http. Display assigned tasks and complaints with a comment/resolution TextInput and action buttons (acknowledge, start_progress, resolve, escalate, close) calling complaintAction. Ensure all imports are used so TypeScript noUnusedLocals passes. Return complete raw TypeScript JSX source only without code fences.

Output file: client/src/modules/complaint_cms/pages/ComplaintQueuePage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 019 Initial complaint configuration and audit page

UTC: 2026-11-01T18:07:33.703851+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 2800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file client/src/modules/complaint_cms/api.ts
```
import { http } from '../../lib/http';
import type * as T from './types';

async function listComplaints(): Promise<T.Complaint[]> {
  const res = await http.get('/complaints/');
  return res.data;
}

async function submitComplaint(payload: T.NewComplaint): Promise<void> {
  await http.post('/complaints/', payload);
}

async function listTasks(complaintId: number): Promise<T.ComplaintTask[]> {
  const res = await http.get(`/complaints/${complaintId}/tasks`);
  return res.data;
}

async function listNotifications(complaintId: number): Promise<T.ComplaintNotificationRecord[]> {
  const res = await http.get(`/complaints/${complaintId}/notifications`);
  return res.data;
}

async function complaintAction(
  id: number,
  action: string,
  data?: Record<string, unknown>
): Promise<void> {
  await http.patch(`/complaints/${id}/action`, { action, ...data });
}

async function getConfiguration(): Promise<T.ConfigurationResponse> {
  const res = await http.get('/configuration/');
  return res.data;
}

async function saveConfiguration(payload: Record<string, unknown>): Promise<void> {
  await http.put('/configuration/', payload);
}

async function getRecords(): Promise<T.RecordListView[]> {
  const res = await http.get('/records/');
  return res.data;
}

```


### Repository file client/src/ui/components/PageHeader.tsx
```
import { Group, Stack, Text, Title } from "@mantine/core";

/** Ported from the sysadmin client. Page identity is carried by this, not by
 *  breadcrumbs — that app has none, and neither does this one. */
export function PageHeader({ title, subtitle, action }: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="flex-end" mb="lg" wrap="wrap">
      <Stack gap={2}>
        <Title order={2}>{title}</Title>
        {subtitle && <Text c="dimmed" size="sm">{subtitle}</Text>}
      </Stack>
      {action}
    </Group>
  );
}

```


### Repository file client/package.json
```
{
  "name": "fusion-integrated-client",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@mantine/core": "7.13.4",
    "@mantine/dates": "7.13.4",
    "@mantine/hooks": "7.13.4",
    "@mantine/notifications": "7.13.4",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "dayjs": "^1.11.21",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-icons": "^5.3.0",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "jsdom": "^25.0.1",
    "postcss": "^8.4.47",
    "postcss-preset-mantine": "^1.17.0",
    "postcss-simple-vars": "^7.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.9"
  }
}

```


END OF REFERENCES

CURRENT TASK

Generate a React 18 / Mantine 7 page component at client/src/modules/complaint_cms/pages/ComplaintAdminPage.tsx with default export function ComplaintAdminPage (max 110 lines). Use React Query v5 object-form useQuery and useMutation with useQueryClient from @tanstack/react-query. Import getConfiguration, saveConfiguration, and getRecords from ../api, PageHeader from ../../../ui/components/PageHeader, and errorMessage from ../../../lib/http. Render a form to create/update complaint categories via saveConfiguration, list existing categories, and show audit updates/notifications from getRecords. Ensure all imports are used so TypeScript noUnusedLocals passes. Return complete raw TypeScript JSX source only without code fences.

Output file: client/src/modules/complaint_cms/pages/ComplaintAdminPage.tsx
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 020 Generate module documentation

UTC: 2026-11-01T18:08:04.055792+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 1800, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file modules/complaint_cms/registry.py
```
MODULE = {
    'code': 'complaint_cms',
    'label': 'Complaint Management System',
    'base_path': '/complaints',
    'nav_section': 'Services',
    'icon': 'WarningCircle',
    'status': 'active',
    'sort_order': 40,
}

NAV_ITEMS = [
    {'path': '/complaints/mine', 'permission': 'complaint_cms.complaint.view_self'},
    {'path': '/complaints/queue', 'permission': 'complaint_cms.task.view'},
    {'path': '/complaints/admin', 'permission': 'complaint_cms.configuration.manage'},
]

PERMISSIONS = (
    ('complaint_cms.complaint.view_self', 'View own complaints'),
    ('complaint_cms.complaint.create', 'Create new complaints'),
    ('complaint_cms.complaint.review', 'Review complaints'),
    ('complaint_cms.complaint.resolve', 'Resolve complaints'),
    ('complaint_cms.complaint.escalate', 'Escalate complaints'),
    ('complaint_cms.task.view', 'View task queue'),
    ('complaint_cms.configuration.manage', 'Manage configuration settings'),
    ('complaint_cms.record.manage', 'Manage record management'),
)

ROLE_GRANTS = {
    'student/faculty/staff': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create'],
    'Caretaker/Warden/Unit Incharge/Section Head': ['complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Complaint Authority': ['complaint_cms.complaint.view_self', 'complaint_cms.complaint.create', 'complaint_cms.complaint.review', 'complaint_cms.complaint.resolve', 'complaint_cms.complaint.escalate'],
    'Dean/Registrar/Director': ['complaint_cms.configuration.manage', 'complaint_cms.record.manage'],
}

SYSTEM_PERMISSIONS = []
```


### Repository file modules/complaint_cms/api/urls.py
```
from django.urls import path
from .api.views import (
    ComplaintListView,
    TaskListView,
    NotificationListView,
    ComplaintActionView,
    ConfigurationView,
    RecordListView
)

urlpatterns = [
    path('complaints/', ComplaintListView.as_view(), name='complaint-list'),
    path('tasks/', TaskListView.as_view(), name='task-list'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('complaints/<int:pk>/action', ComplaintActionView.as_view(), name='complaint-action'),
    path('configuration/', ConfigurationView.as_view(), name='configuration-view'),
    path('records/', RecordListView.as_view(), name='record-list')
]

```


END OF REFERENCES

CURRENT TASK

Write a concise README.md in Markdown for the generated Complaint Management System (complaint_cms) module, max 90 lines. Describe the actual file structure, existing route paths (/complaints/mine, /complaints/queue, /complaints/admin and /api/v1/complaints/...) and mechanical integration setup, not requirements compliance. Explain that it uses existing Fusion auth/config/DB and that python manage.py migrate, seed_modules and client npm run build are the integration commands. State that only build/structural checks are performed in this Phase 1 one-shot local LLM trial and workflow correctness is unverified. Link evidence directory ../../docs/08-delivery/cms-qwen-trial for logs and check outputs. Return Markdown only without code fences.

Output file: modules/complaint_cms/README.md
Return only complete raw source code, without JSON, explanation or Markdown fences.


## Prompt 021 Generate genuine local-model trial record

UTC: 2026-11-01T18:18:08.359439+00:00

System instruction:

You are a local coding assistant. Follow CURRENT TASK after references. Return complete raw source for the one requested file. Do not claim tests or add provenance labels.

Parameters: `{"temperature": 0.2, "seed": 42, "num_ctx": 8192, "num_batch": 128, "num_predict": 3200, "repeat_penalty": 1.15, "repeat_last_n": 256}`

REFERENCE MATERIAL ONLY


### Repository file docs/08-delivery/cms-qwen-trial/observed-results.json
```
{
  "started_at": "2026-11-01T17:53:23.310672+00:00",
  "model": "qwen2.5-coder:3b",
  "digest": "f72c60cabf6237b07f6e632b2c48d533cef25eda2efbd34bed21c5e9c01e6225",
  "installed_bytes": 1929912626,
  "details": {
    "parent_model": "",
    "format": "gguf",
    "family": "qwen2",
    "families": [
      "qwen2"
    ],
    "parameter_size": "3.1B",
    "quantization_level": "Q4_K_M"
  },
  "model_info": {
    "general.architecture": "qwen2",
    "general.base_model.0.name": "Qwen2.5 Coder 3B",
    "general.base_model.0.organization": "Qwen",
    "general.base_model.0.repo_url": "https://huggingface.co/Qwen/Qwen2.5-Coder-3B",
    "general.base_model.count": 1,
    "general.basename": "Qwen2.5-Coder",
    "general.file_type": 15,
    "general.finetune": "Instruct",
    "general.languages": [
      "en"
    ],
    "general.license": "other",
    "general.license.link": "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/LICENSE",
    "general.license.name": "qwen-research",
    "general.parameter_count": 3085938688,
    "general.quantization_version": 2,
    "general.size_label": "3B",
    "general.tags": [
      "code",
      "codeqwen",
      "chat",
      "qwen",
      "qwen-coder",
      "text-generation"
    ],
    "general.type": "model",
    "qwen2.attention.head_count": 16,
    "qwen2.attention.head_count_kv": 2,
    "qwen2.attention.layer_norm_rms_epsilon": 1e-06,
    "qwen2.block_count": 36,
    "qwen2.context_length": 32768,
    "qwen2.embedding_length": 2048,
    "qwen2.feed_forward_length": 11008,
    "qwen2.rope.freq_base": 1000000,
    "tokenizer.ggml.add_bos_token": false,
    "tokenizer.ggml.bos_token_id": 151643,
    "tokenizer.ggml.eos_token_id": 151645,
    "tokenizer.ggml.merges": [],
    "tokenizer.ggml.model": "gpt2",
    "tokenizer.ggml.padding_token_id": 151643,
    "tokenizer.ggml.pre": "qwen2",
    "tokenizer.ggml.token_type": [],
    "tokenizer.ggml.tokens": []
  },
  "parameters": null,
  "ollama_version": {
    "version": "0.40.6"
  },
  "base_commit": "02b01fea4a67b257ea7000009f06a1561699550e",
  "os": "ProductName:\t\tmacOS\nProductVersion:\t\t27.0.1\nBuildVersion:\t\t26A434",
  "hardware": [
    {
      "machine_model": "Mac16,12",
      "chip_type": "Apple M4",
      "number_processors": "proc 10:0:4:6",
      "physical_memory": "16 GB"
    }
  ],
  "gpu": [
    {
      "sppci_model": "Apple M4"
    }
  ],
  "coding_tool": "Python Ollama API file runner with supervised build feedback",
  "default_options": {
    "temperature": 0.1,
    "seed": 42,
    "num_ctx": 32768,
    "num_batch": 128
  },
  "trial_count": 1,
  "generation_requests": 20,
  "generation_seconds": 408.89,
  "generation_failures_length": 0,
  "requests": [
    {
      "prompt": "001",
      "label": "Initial backend models",
      "wall_seconds": 36.41,
      "input_tokens": 4098,
      "output_tokens": 963,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/models.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "002",
      "label": "AppConfig and module registry",
      "wall_seconds": 24.97,
      "input_tokens": 4098,
      "output_tokens": 575,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/apps.py",
        "modules/complaint_cms/registry.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "003",
      "label": "Pure Python domain policy and SLA constants",
      "wall_seconds": 7.24,
      "input_tokens": 1185,
      "output_tokens": 180,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/domain/policy.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "004",
      "label": "Public cross-module contracts",
      "wall_seconds": 10.45,
      "input_tokens": 1896,
      "output_tokens": 237,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/contracts.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "005",
      "label": "Complaint query service",
      "wall_seconds": 8.22,
      "input_tokens": 2830,
      "output_tokens": 140,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/services/queries.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "006",
      "label": "Initial complaint submission service",
      "wall_seconds": 18.21,
      "input_tokens": 3025,
      "output_tokens": 507,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/services/complaints.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "007",
      "label": "Complaint workflow actions service",
      "wall_seconds": 53.92,
      "input_tokens": 2642,
      "output_tokens": 1894,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/services/actions.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "008",
      "label": "Scheduled SLA and auto-close events service",
      "wall_seconds": 13.98,
      "input_tokens": 1177,
      "output_tokens": 470,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/services/events.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "009",
      "label": "Celery tasks and beat schedule",
      "wall_seconds": 13.33,
      "input_tokens": 1333,
      "output_tokens": 297,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/tasks.py",
        "modules/complaint_cms/schedule.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "010",
      "label": "DRF API serializers",
      "wall_seconds": 23.96,
      "input_tokens": 1196,
      "output_tokens": 747,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/api/serializers.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "011",
      "label": "Employee and action API views",
      "wall_seconds": 32.67,
      "input_tokens": 4450,
      "output_tokens": 424,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/api/views.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "012",
      "label": "Configuration and record API views",
      "wall_seconds": 15.25,
      "input_tokens": 2354,
      "output_tokens": 250,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/api/configuration.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "013",
      "label": "API URL registration",
      "wall_seconds": 8.88,
      "input_tokens": 875,
      "output_tokens": 148,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/api/urls.py"
      ],
      "recovered_files": null
    },
    {
      "prompt": "014",
      "label": "Frontend TypeScript interfaces",
      "wall_seconds": 13.25,
      "input_tokens": 1901,
      "output_tokens": 370,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/types.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "015",
      "label": "Frontend typed API client",
      "wall_seconds": 13.28,
      "input_tokens": 1374,
      "output_tokens": 291,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/api.ts"
      ],
      "recovered_files": null
    },
    {
      "prompt": "016",
      "label": "Frontend route registration",
      "wall_seconds": 6.61,
      "input_tokens": 670,
      "output_tokens": 154,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/routes.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "017",
      "label": "Initial complainant page",
      "wall_seconds": 38.36,
      "input_tokens": 1218,
      "output_tokens": 1164,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/pages/MyComplaintsPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "018",
      "label": "Initial authority work queue page",
      "wall_seconds": 24.15,
      "input_tokens": 1179,
      "output_tokens": 743,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/pages/ComplaintQueuePage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "019",
      "label": "Initial complaint configuration and audit page",
      "wall_seconds": 30.27,
      "input_tokens": 1172,
      "output_tokens": 899,
      "done_reason": "stop",
      "files_applied": [
        "client/src/modules/complaint_cms/pages/ComplaintAdminPage.tsx"
      ],
      "recovered_files": null
    },
    {
      "prompt": "020",
      "label": "Generate module documentation",
      "wall_seconds": 15.48,
      "input_tokens": 843,
      "output_tokens": 382,
      "done_reason": "stop",
      "files_applied": [
        "modules/complaint_cms/README.md"
      ],
      "recovered_files": null
    }
  ],
  "checks": [
    {
      "label": "Django model registration check",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.55
    },
    {
      "label": "Django model registration after import adaptation",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.6
    },
    {
      "label": "Django model registration after import adaptation",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.31
    },
    {
      "label": "Django model registration after import adaptation",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.62
    },
    {
      "label": "Django model registration after import adaptation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "check"
      ],
      "wall_seconds": 0.32
    },
    {
      "label": "Generate schema migration from registered Qwen models",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "complaint_cms",
        "--noinput"
      ],
      "wall_seconds": 0.37
    },
    {
      "label": "backend-python-compilation",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "-m",
        "compileall",
        "-q",
        "modules/complaint_cms"
      ],
      "wall_seconds": 0.03
    },
    {
      "label": "isolated-cms-schema-install",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "migrate",
        "--noinput"
      ],
      "wall_seconds": 0.36
    },
    {
      "label": "schema-model-drift",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "makemigrations",
        "--check",
        "--dry-run"
      ],
      "wall_seconds": 0.32
    },
    {
      "label": "isolated-module-registration",
      "returncode": 1,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "seed_modules"
      ],
      "wall_seconds": 0.29
    },
    {
      "label": "isolated-module-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "manage.py",
        "seed_modules"
      ],
      "wall_seconds": 0.5
    },
    {
      "label": "cross-module-schema-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/no_cross_module_fk.py"
      ],
      "wall_seconds": 0.15
    },
    {
      "label": "registered-import-boundaries",
      "returncode": 0,
      "command": [
        ".venv/bin/lint-imports"
      ],
      "wall_seconds": 0.15
    },
    {
      "label": "navigation-route-registration",
      "returncode": 0,
      "command": [
        ".venv/bin/python",
        "ops/checks/nav_matches_routes.py"
      ],
      "wall_seconds": 0.15
    },
    {
      "label": "frontend-first-typecheck",
      "returncode": 2,
      "command": [
        "npx",
        "tsc",
        "--noEmit"
      ],
      "wall_seconds": 2.06
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 2,
      "command": [
        "npx",
        "tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.59
    },
    {
      "label": "frontend-final-typecheck",
      "returncode": 0,
      "command": [
        "npx",
        "tsc",
        "--noEmit"
      ],
      "wall_seconds": 1.49
    },
    {
      "label": "frontend-production-build",
      "returncode": 0,
      "command": [
        "npm",
        "run",
        "build"
      ],
      "wall_seconds": 3.33
    }
  ],
  "validation_scope": "Build/integration only. No functional, BR, security, missing-requirement, maintainability or optimization review. User requested one-shot generation with bugs retained. No deliberate mistakes inserted. Isolated CMS migration passes. PostgreSQL unverified."
}

```


### Repository file docs/08-delivery/cms-qwen-trial/mechanical-corrections.md
```
# Mechanical integration corrections

Registered `modules.complaint_cms` in `config/settings/base.py` (`DOMAIN_MODULES`), mounted `api/v1/complaints/` in `config/urls.py`, merged `BEAT_SCHEDULE` and `TASK_ROUTES` in `config/celery.py`, added `complaint_cms` to `.importlinter` domain/module/layer contracts, and registered `complaint_cms` in `client/src/app/registry.ts`. Exact diff: `integration-registration.patch`.

Created empty Python package `__init__.py` files for `modules/complaint_cms/`, `domain/`, `services/`, `api/`, and `migrations/` as mechanical package scaffolding. Application logic remains model-generated.

Prompt 001 (`modules/complaint_cms/models.py`): added missing `from dataclasses import dataclass` import for the placeholder `Principal` dataclass and increased `status` / `update_type` / `old_status` / `new_status` `max_length` from `10` to `20` to satisfy Django `fields.E009` (`'In Progress'` is 11 chars and `'StatusChange'` is 12 chars). Model fields, choices, and defaults were preserved unchanged.

Prompt 002 (`modules/complaint_cms/registry.py`): aligned `NAV_ITEMS` dictionary keys (`code`, `label`, `icon`, `to`, `required_permission`, `sort_order`) with the required `seed_modules` / `nav_matches_routes.py` contract and granted `complaint_cms.task.view` to authority roles so every declared permission has a holder.

Prompt 004 (`modules/complaint_cms/contracts.py`): added missing `from dataclasses import dataclass` import and aliased `UserScopedModel as UserRef` to match the generated query without changing contract logic.

Prompts 005–008 (`modules/complaint_cms/services/*.py`): adapted single-dot relative imports (`.models`, `.domain.policy`, `.registry`) to parent package relative imports (`..models`, `..domain.policy`, `..registry`), mapped exception imports to `core.api.exceptions`, and replaced `pytz` with `django.utils.timezone` in `events.py`. All query filters, submission logic, workflow action branches, and scheduled event bodies were preserved unchanged.

Prompt 009 (`modules/complaint_cms/tasks.py`, `schedule.py`): added missing `@shared_task` decorator to `cms_process_sla` and removed unused `pytz` import in `schedule.py`.

Prompts 010–013 (`modules/complaint_cms/api/*.py`): adapted single-dot model/service imports to `..models` / `..services`, imported `HasModuleGrant` and `HasPermission` from `fusion_auth.permissions`, replaced invalid `CharField(choices=...)` with `ChoiceField(choices=...)` and `null=True`/`blank=True` with `allow_null=True`/`allow_blank=True` on DRF serializer field overrides, wrapped `record_list_view` in `RecordListView(APIView)` to match the generated `urls.py` import, and stripped trailing slashes in `urls.py` to match the platform API convention.

Prompts 014–019 (`client/src/modules/complaint_cms/**`): added `export` keywords to `api.ts` functions and re-exported `./types`, added `Navigate` import in `routes.tsx`, and adapted React Query v5 object-form calls (`useQuery({ queryKey, queryFn })`, `useMutation({ mutationFn })`, `invalidateQueries({ queryKey })`), Mantine v7 component props (`gap`, `justify`, `highlightOnHover`, `value` on `Pagination`), and named imports (`{ PageHeader }`, `{ errorMessage }`) so `tsc --noEmit` and `npm run build` succeed without altering generated UI structure or API payloads.

```


END OF REFERENCES

CURRENT TASK

Write a concise factual TRIAL_RECORD.md in Markdown with sections Configuration, Method, Observed generation results, Build checks, Limits, Reproduce. Use supplied observed-results.json and mechanical-corrections.md. This was one real local Ollama qwen2.5-coder:3b one-shot trial for the Complaint Management System (complaint_cms) module. Record model size/quant/version, hardware, official Fusion base SHA (02b01fea4a67b257ea7000009f06a1561699550e), API Python runner (devtools/qwen_cms_trial.py), raw responses and payloads retained in responses/, exact prompts in prompts.md, host mechanical changes in mechanical-corrections.md; no deliberate bugs inserted, functional bugs left, no BR correctness/missing requirement/security/optimization tests. Include passing checks (Django check, makemigrations, isolated migrate, seed_modules, no_cross_module_fk, lint-imports, nav_matches_routes, tsc --noEmit, npm run build). Reproduce a request with python3 devtools/qwen_cms_trial.py generate docs/08-delivery/cms-qwen-trial/jobs/05-queries.json. Max 140 lines.

Output file: docs/08-delivery/cms-qwen-trial/TRIAL_RECORD.md
Return only complete raw source code, without JSON, explanation or Markdown fences.

