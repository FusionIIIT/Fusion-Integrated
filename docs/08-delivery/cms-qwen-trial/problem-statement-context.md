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
