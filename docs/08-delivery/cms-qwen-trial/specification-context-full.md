# CMS supplied specification context


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
| Field | Content |
| Rule ID / Name | BR-CMS-001 — Complaint Submission Availability |
| Rule Type | Availability |
| Rule Statement | CMS permits User / Complainant complaint submission at any time. |
| Applies To | Complaint submission |
| Condition / Trigger | When the referenced complaint submission behavior/condition applies. |
| Required Outcome / Constraint | CMS permits User / Complainant complaint submission at any time. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | CW-CMS-01 r1 |
| Status / Notes / TODO | Active |
BR-CMS-002 — Mandatory Complaint Fields
| Field | Content |
| Rule ID / Name | BR-CMS-002 — Mandatory Complaint Fields |
| Rule Type | Validation |
| Rule Statement | CMS shall not accept a complaint submission unless mandatory complaint fields, including complaint category/type and description, are present. |
| Applies To | Complaint submission |
| Condition / Trigger | When the referenced complaint submission behavior/condition applies. |
| Required Outcome / Constraint | CMS shall not accept a complaint submission unless mandatory complaint fields, including complaint category/type and description, are present. |
| Exceptions / Exclusions | Submission remains unaccepted until corrected. |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | CW-CMS-01 r1 |
| Status / Notes / TODO | Active |
BR-CMS-003 — Submission Timestamp Recording
| Field | Content |
| Rule ID / Name | BR-CMS-003 — Submission Timestamp Recording |
| Rule Type | Compliance Recording |
| Rule Statement | CMS records submission date/time for each accepted complaint submission. |
| Applies To | Complaint submission |
| Condition / Trigger | When the referenced complaint submission behavior/condition applies. |
| Required Outcome / Constraint | CMS records submission date/time for each accepted complaint submission. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-004 — Attachment Acceptance Constraint
| Field | Content |
| Rule ID / Name | BR-CMS-004 — Attachment Acceptance Constraint |
| Rule Type | Validation |
| Rule Statement | CMS validates accepted attachment constraints before accepting submitted attachments. |
| Applies To | Complaint attachments |
| Condition / Trigger | When the referenced complaint attachments behavior/condition applies. |
| Required Outcome / Constraint | CMS validates accepted attachment constraints before accepting submitted attachments. |
| Exceptions / Exclusions | Attachment is not accepted until corrected or removed. |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | CW-CMS-01 r1 |
| Status / Notes / TODO | Active |
BR-CMS-005 — Attachment Constraint Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-005 — Attachment Constraint Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | Exact file-type, file-size, and format limits are configurable or institutional constraints outside the frozen problem-statement details. |
| Applies To | Complaint attachments |
| Condition / Trigger | When the referenced complaint attachments behavior/condition applies. |
| Required Outcome / Constraint | Exact file-type, file-size, and format limits are configurable or institutional constraints outside the frozen problem-statement details. |
| Exceptions / Exclusions | CMS only applies configured constraints available to it. |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | CW-CMS-01 r1 |
| Status / Notes / TODO | Active |
BR-CMS-006 — Unique Complaint Identifier
| Field | Content |
| Rule ID / Name | BR-CMS-006 — Unique Complaint Identifier |
| Rule Type | Compliance Recording |
| Rule Statement | Each accepted complaint submission shall receive a unique complaint identifier. |
| Applies To | Complaint submission |
| Condition / Trigger | When the referenced complaint submission behavior/condition applies. |
| Required Outcome / Constraint | Each accepted complaint submission shall receive a unique complaint identifier. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.1 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-001 |
| Related WFs | CW-CMS-01 r1 |
| Status / Notes / TODO | Active |
BR-CMS-007 — Manual Assignment Rule
| Field | Content |
| Rule ID / Name | BR-CMS-007 — Manual Assignment Rule |
| Rule Type | Workflow Constraint |
| Rule Statement | Submitted complaints are manually assigned by Complaint Handler for operational handling; automatic initial assignment is outside the baseline. |
| Applies To | Assignment |
| Condition / Trigger | When the referenced assignment behavior/condition applies. |
| Required Outcome / Constraint | Submitted complaints are manually assigned by Complaint Handler for operational handling; automatic initial assignment is outside the baseline. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.2 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-004 |
| Related WFs | CW-CMS-01 r2 |
| Status / Notes / TODO | Active |
BR-CMS-008 — Complaint Category/Type Rule
| Field | Content |
| Rule ID / Name | BR-CMS-008 — Complaint Category/Type Rule |
| Rule Type | Data Rule |
| Rule Statement | Complaints are categorized by complaint category/type. |
| Applies To | Categorization |
| Condition / Trigger | When the referenced categorization behavior/condition applies. |
| Required Outcome / Constraint | Complaints are categorized by complaint category/type. |
| Exceptions / Exclusions | No taxonomy is invented by this baseline. |
| Source / Rationale | Frozen PS 3.2 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-004 |
| Related WFs | CW-CMS-01 r2 |
| Status / Notes / TODO | Active |
BR-CMS-009 — Priority Value Set
| Field | Content |
| Rule ID / Name | BR-CMS-009 — Priority Value Set |
| Rule Type | Validation |
| Rule Statement | Complaint priority shall be assigned only as Low, Medium, or High. |
| Applies To | Priority assignment |
| Condition / Trigger | When the referenced priority assignment behavior/condition applies. |
| Required Outcome / Constraint | Complaint priority shall be assigned only as Low, Medium, or High. |
| Exceptions / Exclusions | Invalid priority value is not accepted. |
| Source / Rationale | Frozen PS 3.2 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-004 |
| Related WFs | CW-CMS-01 r2 |
| Status / Notes / TODO | Active |
BR-CMS-010 — Assignment and Priority Downstream Use
| Field | Content |
| Rule ID / Name | BR-CMS-010 — Assignment and Priority Downstream Use |
| Rule Type | Compliance Recording |
| Rule Statement | CMS records assignment and priority information for downstream complaint handling, reminders, and escalation. |
| Applies To | Assignment/Priority |
| Condition / Trigger | When the referenced assignment/priority behavior/condition applies. |
| Required Outcome / Constraint | CMS records assignment and priority information for downstream complaint handling, reminders, and escalation. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.2 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-004 |
| Related WFs | CW-CMS-01 r2 |
| Status / Notes / TODO | Active |
BR-CMS-011 — Complaint Status and Progress History
| Field | Content |
| Rule ID / Name | BR-CMS-011 — Complaint Status and Progress History |
| Rule Type | Compliance Recording |
| Rule Statement | CMS maintains complaint status history and complaint progress history throughout the lifecycle of each complaint. |
| Applies To | Tracking/Progress |
| Condition / Trigger | When the referenced tracking/progress behavior/condition applies. |
| Required Outcome / Constraint | CMS maintains complaint status history and complaint progress history throughout the lifecycle of each complaint. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.3 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-002; UC-CMS-005 |
| Related WFs | CW-CMS-01 r3 |
| Status / Notes / TODO | Active |
BR-CMS-012 — Complaint Lifecycle State Set
| Field | Content |
| Rule ID / Name | BR-CMS-012 — Complaint Lifecycle State Set |
| Rule Type | State Constraint |
| Rule Statement | CMS recognizes Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states. |
| Applies To | Lifecycle management |
| Condition / Trigger | When the referenced lifecycle management behavior/condition applies. |
| Required Outcome / Constraint | CMS recognizes Submitted, In Progress, Resolved, Rejected, and Closed as complaint lifecycle states. |
| Exceptions / Exclusions | No additional lifecycle states are introduced by this baseline. |
| Source / Rationale | Frozen PS 3.4 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-005; UC-CMS-006; UC-CMS-007 |
| Related WFs | CW-CMS-01 r4-r7 |
| Status / Notes / TODO | Active |
BR-CMS-013 — Resolution Details Required
| Field | Content |
| Rule ID / Name | BR-CMS-013 — Resolution Details Required |
| Rule Type | Validation |
| Rule Statement | CMS records complaint resolution details for resolved complaints; a complaint shall not be represented as resolved without recorded resolution details. |
| Applies To | Resolution |
| Condition / Trigger | When the referenced resolution behavior/condition applies. |
| Required Outcome / Constraint | CMS records complaint resolution details for resolved complaints; a complaint shall not be represented as resolved without recorded resolution details. |
| Exceptions / Exclusions | Resolution cannot be completed without details. |
| Source / Rationale | Frozen PS 3.4 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-006 |
| Related WFs | CW-CMS-01 r4 |
| Status / Notes / TODO | Active |
BR-CMS-014 — Rejection Details Required
| Field | Content |
| Rule ID / Name | BR-CMS-014 — Rejection Details Required |
| Rule Type | Validation |
| Rule Statement | CMS records rejection details or rejection reason information for rejected complaints. |
| Applies To | Rejection |
| Condition / Trigger | When the referenced rejection behavior/condition applies. |
| Required Outcome / Constraint | CMS records rejection details or rejection reason information for rejected complaints. |
| Exceptions / Exclusions | Rejection cannot be completed without details/reason. |
| Source / Rationale | Frozen PS 3.4 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-006 |
| Related WFs | CW-CMS-01 r5 |
| Status / Notes / TODO | Active |
BR-CMS-015 — Outcome and Status Notification Rule
| Field | Content |
| Rule ID / Name | BR-CMS-015 — Outcome and Status Notification Rule |
| Rule Type | Notification Rule |
| Rule Statement | CMS notifies Users / Complainants of complaint outcome and status updates. |
| Applies To | Resolution/Rejection/Progress |
| Condition / Trigger | When the referenced resolution/rejection/progress behavior/condition applies. |
| Required Outcome / Constraint | CMS notifies Users / Complainants of complaint outcome and status updates. |
| Exceptions / Exclusions | Notification delivery infrastructure is outside CMS scope. |
| Source / Rationale | Frozen PS 3.4/3.10 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-005; UC-CMS-006 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-016 — Closure Verification Rule
| Field | Content |
| Rule ID / Name | BR-CMS-016 — Closure Verification Rule |
| Rule Type | Workflow Constraint |
| Rule Statement | When the applicable closure process requires verification, CMS supports verification by the User / Complainant or Complaint Supervisor before closure. |
| Applies To | Closure |
| Condition / Trigger | When the referenced closure behavior/condition applies. |
| Required Outcome / Constraint | When the applicable closure process requires verification, CMS supports verification by the User / Complainant or Complaint Supervisor before closure. |
| Exceptions / Exclusions | The policy deciding when each verifier applies is outside this baseline. |
| Source / Rationale | Frozen PS 3.4 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-007; UC-CMS-019 |
| Related WFs | CW-CMS-01 r6-r7 |
| Status / Notes / TODO | Active |
BR-CMS-017 — Closure Recording Rule
| Field | Content |
| Rule ID / Name | BR-CMS-017 — Closure Recording Rule |
| Rule Type | Compliance Recording |
| Rule Statement | CMS records complaint closure after successful verification when verification is required. |
| Applies To | Closure |
| Condition / Trigger | When the referenced closure behavior/condition applies. |
| Required Outcome / Constraint | CMS records complaint closure after successful verification when verification is required. |
| Exceptions / Exclusions | If verification is required and not recorded, closure is not recorded. |
| Source / Rationale | Frozen PS 3.4 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-007; UC-CMS-019 |
| Related WFs | CW-CMS-01 r6-r7 |
| Status / Notes / TODO | Active |
BR-CMS-018 — Reopening Eligibility Rule
| Field | Content |
| Rule ID / Name | BR-CMS-018 — Reopening Eligibility Rule |
| Rule Type | Eligibility |
| Rule Statement | Users / Complainants may request reopening only for a closed complaint where dissatisfaction remains after closure. |
| Applies To | Reopening |
| Condition / Trigger | When the referenced reopening behavior/condition applies. |
| Required Outcome / Constraint | Users / Complainants may request reopening only for a closed complaint where dissatisfaction remains after closure. |
| Exceptions / Exclusions | If complaint is not closed, it is not processed as reopening. |
| Source / Rationale | Frozen PS 3.5 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-008 |
| Related WFs | CW-CMS-02 r1 |
| Status / Notes / TODO | Active |
BR-CMS-019 — Reopening Review Ownership
| Field | Content |
| Rule ID / Name | BR-CMS-019 — Reopening Review Ownership |
| Rule Type | Permission |
| Rule Statement | Complaint Supervisor reviews complaint reopening requests. |
| Applies To | Reopening |
| Condition / Trigger | When the referenced reopening behavior/condition applies. |
| Required Outcome / Constraint | Complaint Supervisor reviews complaint reopening requests. |
| Exceptions / Exclusions | No other review role is introduced. |
| Source / Rationale | Frozen PS 3.5 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-020 |
| Related WFs | CW-CMS-02 r2-r3 |
| Status / Notes / TODO | Active |
BR-CMS-020 — Approved Reopening Status Rule
| Field | Content |
| Rule ID / Name | BR-CMS-020 — Approved Reopening Status Rule |
| Rule Type | State Constraint |
| Rule Statement | If a reopening request is approved, CMS reopens the complaint and updates its status accordingly. |
| Applies To | Reopening |
| Condition / Trigger | When the referenced reopening behavior/condition applies. |
| Required Outcome / Constraint | If a reopening request is approved, CMS reopens the complaint and updates its status accordingly. |
| Exceptions / Exclusions | If not approved, complaint remains closed and outcome is recorded. |
| Source / Rationale | Frozen PS 3.5 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-020 |
| Related WFs | CW-CMS-02 r3 |
| Status / Notes / TODO | Active |
BR-CMS-021 — Reopening Outcome Recording
| Field | Content |
| Rule ID / Name | BR-CMS-021 — Reopening Outcome Recording |
| Rule Type | Compliance Recording |
| Rule Statement | CMS records the outcome of each complaint reopening request. |
| Applies To | Reopening |
| Condition / Trigger | When the referenced reopening behavior/condition applies. |
| Required Outcome / Constraint | CMS records the outcome of each complaint reopening request. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.5 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-020 |
| Related WFs | CW-CMS-02 r2-r3 |
| Status / Notes / TODO | Active |
BR-CMS-022 — Feedback Eligibility Rule
| Field | Content |
| Rule ID / Name | BR-CMS-022 — Feedback Eligibility Rule |
| Rule Type | Eligibility |
| Rule Statement | Users / Complainants may submit feedback after complaint resolution or closure. |
| Applies To | Feedback |
| Condition / Trigger | When the referenced feedback behavior/condition applies. |
| Required Outcome / Constraint | Users / Complainants may submit feedback after complaint resolution or closure. |
| Exceptions / Exclusions | Feedback outside this condition is not treated as post-resolution/closure feedback. |
| Source / Rationale | Frozen PS 3.6 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-009 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-023 — Feedback Review Access Rule
| Field | Content |
| Rule ID / Name | BR-CMS-023 — Feedback Review Access Rule |
| Rule Type | Access Rule |
| Rule Statement | Complaint Handlers and Complaint Supervisors can review submitted feedback. |
| Applies To | Feedback |
| Condition / Trigger | When the referenced feedback behavior/condition applies. |
| Required Outcome / Constraint | Complaint Handlers and Complaint Supervisors can review submitted feedback. |
| Exceptions / Exclusions | No additional feedback-review actors are introduced. |
| Source / Rationale | Frozen PS 3.6 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-010 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-024 — Manual Escalation Eligibility
| Field | Content |
| Rule ID / Name | BR-CMS-024 — Manual Escalation Eligibility |
| Rule Type | Workflow Constraint |
| Rule Statement | Complaints that remain unresolved may be escalated manually. |
| Applies To | Escalation |
| Condition / Trigger | When the referenced escalation behavior/condition applies. |
| Required Outcome / Constraint | Complaints that remain unresolved may be escalated manually. |
| Exceptions / Exclusions | Resolved, rejected, or closed complaints are not treated as unresolved for manual escalation. |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-011 |
| Related WFs | CW-CMS-03 r1 |
| Status / Notes / TODO | Active |
BR-CMS-025 — Escalation Status Tracking
| Field | Content |
| Rule ID / Name | BR-CMS-025 — Escalation Status Tracking |
| Rule Type | Compliance Recording |
| Rule Statement | CMS tracks escalation status. |
| Applies To | Escalation |
| Condition / Trigger | When the referenced escalation behavior/condition applies. |
| Required Outcome / Constraint | CMS tracks escalation status. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-011; UC-CMS-022 |
| Related WFs | CW-CMS-03 r1 |
| Status / Notes / TODO | Active |
BR-CMS-026 — Priority-SLA Association
| Field | Content |
| Rule ID / Name | BR-CMS-026 — Priority-SLA Association |
| Rule Type | Constraint |
| Rule Statement | Complaint priority is associated with applicable SLA timelines. |
| Applies To | SLA management |
| Condition / Trigger | When the referenced sla management behavior/condition applies. |
| Required Outcome / Constraint | Complaint priority is associated with applicable SLA timelines. |
| Exceptions / Exclusions | Exact SLA values are not specified by this baseline. |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-021; UC-CMS-022 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-027 — SLA Duration Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-027 — SLA Duration Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | CMS shall not specify exact SLA duration values in the module baseline. |
| Applies To | SLA management |
| Condition / Trigger | When the referenced sla management behavior/condition applies. |
| Required Outcome / Constraint | CMS shall not specify exact SLA duration values in the module baseline. |
| Exceptions / Exclusions | SLA values are applicable/configured externally. |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-021; UC-CMS-022 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-028 — Pre-Breach Reminder Rule
| Field | Content |
| Rule ID / Name | BR-CMS-028 — Pre-Breach Reminder Rule |
| Rule Type | Trigger |
| Rule Statement | CMS sends reminder notifications when a complaint approaches the applicable SLA breach condition. |
| Applies To | SLA management |
| Condition / Trigger | When the referenced sla management behavior/condition applies. |
| Required Outcome / Constraint | CMS sends reminder notifications when a complaint approaches the applicable SLA breach condition. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-021 |
| Related WFs | N/A — reminder is non-state-changing |
| Status / Notes / TODO | Active |
BR-CMS-029 — Automatic SLA Escalation Rule
| Field | Content |
| Rule ID / Name | BR-CMS-029 — Automatic SLA Escalation Rule |
| Rule Type | Trigger |
| Rule Statement | CMS automatically escalates a complaint if it is not resolved within the applicable SLA timeline. |
| Applies To | SLA management |
| Condition / Trigger | When the referenced sla management behavior/condition applies. |
| Required Outcome / Constraint | CMS automatically escalates a complaint if it is not resolved within the applicable SLA timeline. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.7 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-022 |
| Related WFs | BW-CMS-08 r1; CW-CMS-03 r2 |
| Status / Notes / TODO | Active |
BR-CMS-030 — Announcement Publishing Authority
| Field | Content |
| Rule ID / Name | BR-CMS-030 — Announcement Publishing Authority |
| Rule Type | Permission |
| Rule Statement | Only Complaint Handlers and Complaint Supervisors may publish complaint-related announcements. |
| Applies To | Announcements |
| Condition / Trigger | When the referenced announcements behavior/condition applies. |
| Required Outcome / Constraint | Only Complaint Handlers and Complaint Supervisors may publish complaint-related announcements. |
| Exceptions / Exclusions | No additional announcement publishers are introduced. |
| Source / Rationale | Frozen PS 3.8 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-013 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-031 — Announcement Notification Configuration
| Field | Content |
| Rule ID / Name | BR-CMS-031 — Announcement Notification Configuration |
| Rule Type | Notification Rule |
| Rule Statement | CMS sends announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements. |
| Applies To | Announcements |
| Condition / Trigger | When the referenced announcements behavior/condition applies. |
| Required Outcome / Constraint | CMS sends announcement-related notifications to Users / Complainants where CMS is configured to notify them about such announcements. |
| Exceptions / Exclusions | Notification may be absent if CMS is not configured to notify. |
| Source / Rationale | Frozen PS 3.8 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-013; UC-CMS-014 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-032 — Reporting and Analytics Access Rule
| Field | Content |
| Rule ID / Name | BR-CMS-032 — Reporting and Analytics Access Rule |
| Rule Type | Access Rule |
| Rule Statement | Complaint Handler, Complaint Supervisor, and System Admin receive only the report/summary/analytics visibility specified for their roles. |
| Applies To | Reports/Analytics |
| Condition / Trigger | When the referenced reports/analytics behavior/condition applies. |
| Required Outcome / Constraint | Complaint Handler, Complaint Supervisor, and System Admin receive only the report/summary/analytics visibility specified for their roles. |
| Exceptions / Exclusions | No unsupported analytics or routine operations are introduced. |
| Source / Rationale | Frozen PS 3.9 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-015; UC-CMS-016; UC-CMS-017 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-033 — Analytics Scope Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-033 — Analytics Scope Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | CMS analytics scope is limited to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS. |
| Applies To | Reports/Analytics |
| Condition / Trigger | When the referenced reports/analytics behavior/condition applies. |
| Required Outcome / Constraint | CMS analytics scope is limited to complaint reports, complaint summaries, escalation summaries, and analytics visibility explicitly available within CMS. |
| Exceptions / Exclusions | Unsupported analytics are outside scope. |
| Source / Rationale | Frozen PS 3.9 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-017 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-034 — Notification Triggering Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-034 — Notification Triggering Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | CMS responsibility is limited to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events. |
| Applies To | Notifications |
| Condition / Trigger | When the referenced notifications behavior/condition applies. |
| Required Outcome / Constraint | CMS responsibility is limited to notification triggering, not central email delivery infrastructure or platform-level notification infrastructure, unless explicitly represented as CMS notification records or events. |
| Exceptions / Exclusions | Email delivery and platform notification infrastructure remain outside CMS scope. |
| Source / Rationale | Frozen PS 3.10 |
| Related CFRs / AFRs |  |
| Related UCs | All notification-producing actor-triggered/event-triggered UCs |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-035 — Time-Bound CMS Role Assignment
| Field | Content |
| Rule ID / Name | BR-CMS-035 — Time-Bound CMS Role Assignment |
| Rule Type | Permission |
| Rule Statement | System Admin may assign Complaint Handler and Complaint Supervisor roles to existing institutional users for a specified duration. |
| Applies To | Role management |
| Condition / Trigger | When the referenced role management behavior/condition applies. |
| Required Outcome / Constraint | System Admin may assign Complaint Handler and Complaint Supervisor roles to existing institutional users for a specified duration. |
| Exceptions / Exclusions | Target user identity/master data is outside CMS. |
| Source / Rationale | Frozen PS 3.11 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-018 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-036 — Mid-Cycle Role Reassignment
| Field | Content |
| Rule ID / Name | BR-CMS-036 — Mid-Cycle Role Reassignment |
| Rule Type | Permission |
| Rule Statement | System Admin may reassign Complaint Handler and Complaint Supervisor roles mid-cycle. |
| Applies To | Role management |
| Condition / Trigger | When the referenced role management behavior/condition applies. |
| Required Outcome / Constraint | System Admin may reassign Complaint Handler and Complaint Supervisor roles mid-cycle. |
| Exceptions / Exclusions | None specified |
| Source / Rationale | Frozen PS 3.11 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-018 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-037 — Active Role Cardinality
| Field | Content |
| Rule ID / Name | BR-CMS-037 — Active Role Cardinality |
| Rule Type | Constraint |
| Rule Statement | CMS enforces exactly one active Complaint Handler role-holder and exactly one active Complaint Supervisor role-holder at a time within CMS. |
| Applies To | Role management |
| Condition / Trigger | When the referenced role management behavior/condition applies. |
| Required Outcome / Constraint | CMS enforces exactly one active Complaint Handler role-holder and exactly one active Complaint Supervisor role-holder at a time within CMS. |
| Exceptions / Exclusions | Assignment that violates cardinality is not completed. |
| Source / Rationale | Frozen PS 3.11 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-018 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-038 — CMS Role Scope Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-038 — CMS Role Scope Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | CMS role assignment is limited to CMS-specific operational and supervisory roles and excludes HR master-data management, payroll, employment records, and platform-wide user-account administration. |
| Applies To | Role management |
| Condition / Trigger | When the referenced role management behavior/condition applies. |
| Required Outcome / Constraint | CMS role assignment is limited to CMS-specific operational and supervisory roles and excludes HR master-data management, payroll, employment records, and platform-wide user-account administration. |
| Exceptions / Exclusions | No HR or platform-account functionality is introduced. |
| Source / Rationale | Frozen PS 3.11 |
| Related CFRs / AFRs |  |
| Related UCs | UC-CMS-018 |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-039 — Excluded Cross-Module Functions
| Field | Content |
| Rule ID / Name | BR-CMS-039 — Excluded Cross-Module Functions |
| Rule Type | Scope Boundary |
| Rule Statement | CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration. |
| Applies To | Scope boundary |
| Condition / Trigger | When the referenced scope boundary behavior/condition applies. |
| Required Outcome / Constraint | CMS shall not perform payment, accounting, payroll, procurement, inventory, physical maintenance execution, or platform-level security administration. |
| Exceptions / Exclusions | These functions may be referenced only as complaint content/progress if applicable. |
| Source / Rationale | Frozen PS 3.12 |
| Related CFRs / AFRs |  |
| Related UCs | All artifacts |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-040 — External Service/Department Complaint Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-040 — External Service/Department Complaint Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | CMS limits complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information. |
| Applies To | Scope boundary |
| Condition / Trigger | When the referenced scope boundary behavior/condition applies. |
| Required Outcome / Constraint | CMS limits complaints involving external services or departments to recording, assigning, tracking, escalating, resolving or rejecting, closing, reopening, notifying, reporting, and reviewing complaint-handling information. |
| Exceptions / Exclusions | Execution of remedial work remains outside CMS. |
| Source / Rationale | Frozen PS 3.12 |
| Related CFRs / AFRs |  |
| Related UCs | Complaint lifecycle artifacts |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-041 — External Policy Boundary
| Field | Content |
| Rule ID / Name | BR-CMS-041 — External Policy Boundary |
| Rule Type | Scope Boundary |
| Rule Statement | External institutional policies, manuals, guidelines, and departmental processes are outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them. |
| Applies To | Scope boundary |
| Condition / Trigger | When the referenced scope boundary behavior/condition applies. |
| Required Outcome / Constraint | External institutional policies, manuals, guidelines, and departmental processes are outside CMS scope unless CMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them. |
| Exceptions / Exclusions | No hidden policies are invented. |
| Source / Rationale | Frozen PS 3.12 |
| Related CFRs / AFRs |  |
| Related UCs | All artifacts |
| Related WFs | N/A — rule does not itself require a workflow transition |
| Status / Notes / TODO | Active |
BR-CMS-042 — System Not Primary Actor Rule
| Field | Content |
| Rule ID / Name | BR-CMS-042 — System Not Primary Actor Rule |
| Rule Type | Retired / Modeling Convention |
| Rule Statement | Retired as a Business Rule. Modeling convention retained: the system under specification is not its own UC actor; meaningful automatic services may be event-triggered UCs with Primary Actor = N.A. — Event-triggered, and System may appear in a workflow STT Actor column only for autonomous state-changing transitions. |
| Applies To | UC/WF specification method |
| Condition / Trigger | When the referenced uc/wf specification method behavior/condition applies. |
| Required Outcome / Constraint | Retired as a Business Rule. Modeling convention retained: the system under specification is not its own UC actor; meaningful automatic services may be event-triggered UCs with Primary Actor = N.A. — Event-triggered, and System may appear in a workflow STT Actor column only for autonomous state-changing transitions. |
| Exceptions / Exclusions | N/A |
| Source / Rationale | Frozen PS 3.12 |
| Related CFRs / AFRs |  |
| Related UCs | UC modeling notes; UC-CMS-021; UC-CMS-022 |
| Related WFs | WF modeling notes; BW-CMS-08; CW-CMS-03 |
| Status / Notes / TODO | Retired — modeling convention maintained outside business-rule baseline; wording synchronized to DIRECT_FINAL_v2. |

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
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Submit a complaint with required details and optional supporting attachments. |
| Trigger | User / Complainant chooses to submit a complaint. |
| Preconditions | User / Complainant is an authorized CMS user; mandatory fields and attachment constraints are available to CMS. |
| Main Success Scenario | 1. User / Complainant opens the complaint submission function. | 2. Enters complaint category/type, complaint description, and other mandatory complaint information. | 3. Attaches supporting evidence if applicable. | 4. CMS validates mandatory complaint fields. | 5. CMS validates accepted attachment constraints. | 6. CMS accepts the submission, records submission date/time, and generates a unique complaint identifier. | 7. CMS provides submission confirmation and triggers the complaint-submission email notification event. |
| Alternative Flows | - If mandatory fields are incomplete, CMS does not accept the submission and asks the User / Complainant to correct the submission. | - If an attachment violates accepted constraints, CMS does not accept the attachment until corrected or removed. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint is registered with identifier, category/type, description, submission date/time, and submission confirmation/notification event recorded. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-001; BR-CMS-002; BR-CMS-003; BR-CMS-004; BR-CMS-005; BR-CMS-006; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r1; BW-CMS-01/02/03/04 r1 |
| Notes / TODO |  |
UC-CMS-002 — Track Submitted Complaint Status and History
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | View the status and history of the User / Complainant's submitted complaints. |
| Trigger | User / Complainant chooses to check complaint status or history. |
| Preconditions | At least one complaint submitted by the User / Complainant exists in CMS. |
| Main Success Scenario | 1. User / Complainant opens complaint tracking. | 2. CMS lists the User / Complainant's submitted complaints. | 3. User / Complainant selects a complaint. | 4. CMS displays current complaint status and complaint history for the selected complaint. |
| Alternative Flows | - If no submitted complaint exists, CMS shows that there is no complaint history for the User / Complainant. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | User / Complainant has viewed status/history information; no lifecycle state is changed. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-011 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-003 — Review Assigned Complaints
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Review complaints assigned for handling. |
| Trigger | Complaint Handler accesses assigned complaint worklist. |
| Preconditions | Complaint Handler role is active and assigned complaints exist or may exist. |
| Main Success Scenario | 1. Complaint Handler opens assigned complaints list. | 2. CMS displays complaints assigned for handling. | 3. Complaint Handler reviews complaint details, status, history, assignment, priority, and available attachments where present. |
| Alternative Flows | - If no assigned complaints exist, CMS shows an empty assigned-complaint list. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint Handler has reviewed assigned complaint information; no state change is required by this use case. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | N/A |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-004 — Assign, Categorize, and Prioritize Complaint
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Manually assign submitted complaints for operational handling, categorize them, and assign priority. |
| Trigger | Complaint Handler selects a submitted complaint for operational handling setup. |
| Preconditions | A submitted complaint exists and the Complaint Handler role is active. |
| Main Success Scenario | 1. Complaint Handler selects a submitted complaint. | 2. Complaint Handler manually assigns the complaint for operational handling. | 3. Complaint Handler categorizes the complaint by complaint category/type. | 4. Complaint Handler assigns priority as Low, Medium, or High. | 5. CMS records assignment and priority information for downstream handling, reminders, and escalation. |
| Alternative Flows | - If required assignment, category/type, or priority information is not supplied, CMS keeps the complaint from completing this operation until corrected. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint has assignment, category/type, and priority information recorded for handling, reminders, and escalation. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-007; BR-CMS-008; BR-CMS-009; BR-CMS-010 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r2; BW-CMS-01/02/03/04 r2 |
| Notes / TODO |  |
UC-CMS-005 — Update Complaint Progress
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Record progress updates while a complaint is being processed. |
| Trigger | Complaint Handler needs to update complaint progress. |
| Preconditions | Complaint is assigned for handling and is within the complaint lifecycle. |
| Main Success Scenario | 1. Complaint Handler opens the complaint. | 2. Complaint Handler enters a progress update. | 3. CMS records the progress update and maintains progress history. | 4. CMS triggers a status-update notification only where an independently supported status update event applies. |
| Alternative Flows | - If the progress update is incomplete or invalid for the current state, CMS does not record the update until corrected. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint progress history is updated. No generic lifecycle-state change is inferred from a progress entry. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-011; BR-CMS-015; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r3; BW-CMS-01/02/03/04 r3 (zero or one traversal) |
| Notes / TODO | ISS-CMS-007: the baseline recognizes In Progress but does not define the transition that enters it. Exact status-transition semantics are not invented. |
UC-CMS-006 — Resolve or Reject Complaint
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Record resolution or rejection details and update complaint outcome. |
| Trigger | Complaint Handler completes handling decision for a complaint. |
| Preconditions | Complaint is assigned for handling and is not already closed. |
| Main Success Scenario | 1. Complaint Handler opens the complaint. | 2. Selects Resolution or Rejection. | 3. For Resolution, records resolution details. | 4. For Rejection, records rejection details/reason. | 5. CMS updates status to Resolved or Rejected according to the supported outcome. | 6. CMS records the outcome/status update and triggers the corresponding resolution or rejection email notification event. |
| Alternative Flows | - If resolution details are missing for a resolved complaint, CMS does not mark the complaint Resolved. | - If rejection details or reason information are missing for a rejected complaint, CMS does not mark the complaint Rejected. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint outcome and status are recorded; User / Complainant is notified. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-012; BR-CMS-013; BR-CMS-014; BR-CMS-015; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r4-r5; BW-CMS-01/02/03/04 outcome row |
| Notes / TODO |  |
UC-CMS-007 — Verify Resolved Complaint for Closure (User / Complainant)
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Verify a resolved complaint when the applicable closure process requires User / Complainant verification, enabling CMS to record closure. |
| Trigger | A complaint is Resolved and the applicable closure process requires User / Complainant verification. |
| Preconditions | Complaint is Resolved; applicable closure process identifies User / Complainant verification. |
| Main Success Scenario | 1. User / Complainant opens the resolved complaint. | 2. Reviews resolution details. | 3. Records successful verification. | 4. CMS records closure and updates status to Closed. |
| Alternative Flows | If verification is not recorded/successful, CMS does not close the complaint under this verification-required path. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Resolved complaint is Closed after successful required User / Complainant verification. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-016; BR-CMS-017 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r6; BW-CMS-02 r5 |
| Notes / TODO | ISS-CMS-010: behavior when verification is not required remains unspecified. |
UC-CMS-008 — Request Complaint Reopening
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Request reopening of a closed complaint where dissatisfaction remains after closure. |
| Trigger | User / Complainant remains dissatisfied after complaint closure. |
| Preconditions | Complaint is Closed and belongs to the User / Complainant. |
| Main Success Scenario | 1. User / Complainant opens the closed complaint. | 2. Submits a reopening request. | 3. CMS records the reopening request and makes it available for Complaint Supervisor review. |
| Alternative Flows | If the complaint is not Closed, CMS does not process the action as a reopening request. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | A reopening request is recorded while the complaint remains Closed pending review. |
| Failure / Minimal Guarantee | Complaint remains Closed; no reopening outcome is recorded if a valid request is not accepted. |
| Related Business Rules | BR-CMS-018 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-02 r1; BW-CMS-05/06 r1 |
| Notes / TODO | Supervisor decision is a separate actor goal in UC-CMS-020. |
UC-CMS-009 — Submit Feedback
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Submit feedback after complaint resolution or closure. |
| Trigger | User / Complainant chooses to submit feedback. |
| Preconditions | Complaint is resolved or closed. |
| Main Success Scenario | 1. User / Complainant opens feedback submission. | 2. Enters feedback. | 3. CMS records feedback for authorized review. | 4. CMS triggers a feedback-related email notification event where applicable. |
| Alternative Flows | - If the complaint is neither resolved nor closed, CMS does not treat the feedback as post-resolution/closure feedback. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Feedback is stored and available to authorized reviewers. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-022; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-010 — Review Submitted Feedback
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler or Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Review feedback submitted by Users / Complainants. |
| Trigger | Complaint Handler or Complaint Supervisor opens submitted feedback. |
| Preconditions | Submitted feedback exists. |
| Main Success Scenario | 1. Actor opens feedback review function. | 2. CMS displays submitted feedback. | 3. Actor reviews feedback content. |
| Alternative Flows | - If no feedback exists, CMS shows an empty feedback list. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Feedback is reviewed; no complaint lifecycle transition is implied. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-023 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Either listed authorized role may independently initiate the same goal; no process succession between those roles is implied. |
UC-CMS-011 — Manually Escalate Unresolved Complaint
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Escalate an unresolved complaint manually when needed. |
| Trigger | Complaint Handler determines that an unresolved complaint requires escalation. |
| Preconditions | Complaint remains unresolved and is within active handling. |
| Main Success Scenario | 1. Complaint Handler opens an unresolved complaint. | 2. Initiates manual escalation. | 3. CMS records escalation status. | 4. CMS triggers the complaint-escalation email notification event. |
| Alternative Flows | - If the complaint is already resolved, rejected, or closed, CMS does not treat it as an unresolved complaint for manual escalation. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint escalation status is recorded. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-024; BR-CMS-025; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-03 r1; BW-CMS-07 r1 |
| Notes / TODO |  |
UC-CMS-012 — Monitor Escalated Complaints
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Monitor complaints that have been escalated and view their recorded escalation status. |
| Trigger | Complaint Supervisor opens the escalated-complaint monitoring view. |
| Preconditions | One or more complaints may have recorded escalation status; Complaint Supervisor role is active. |
| Main Success Scenario | 1. Complaint Supervisor opens escalated-complaint monitoring. | 2. CMS displays escalated complaints and their recorded escalation status. | 3. Complaint Supervisor reviews the displayed escalation information. |
| Alternative Flows | - If no escalated complaints exist, CMS shows no escalated complaint entries. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint Supervisor has reviewed escalated complaint information; no complaint lifecycle or escalation state is changed by this use case. |
| Failure / Minimal Guarantee | Previously recorded complaint and escalation data remain unchanged. |
| Related Business Rules | N/A |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | SLA reminder and automatic SLA escalation are separated into event-triggered UC-CMS-021 and UC-CMS-022 under DIRECT_FINAL_v2. |
UC-CMS-013 — Publish Complaint-Related Announcement
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler or Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Publish a complaint-related announcement. |
| Trigger | Authorized actor chooses to publish a complaint-related announcement. |
| Preconditions | Actor is an active Complaint Handler or Complaint Supervisor. |
| Main Success Scenario | 1. Authorized Complaint Handler or Complaint Supervisor opens announcement publishing. | 2. Enters complaint-related announcement content. | 3. CMS publishes the announcement. | 4. CMS triggers the announcement-related email notification event where CMS is configured to notify Users / Complainants. |
| Alternative Flows | - If actor is not Complaint Handler or Complaint Supervisor, CMS does not allow announcement publication. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Announcement is published and notification may be triggered according to CMS configuration. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-030; BR-CMS-031; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO | Either listed authorized role may independently initiate the same goal; no process succession between those roles is implied. |
UC-CMS-014 — View Complaint-Related Announcements
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | User / Complainant |
| Supporting Actors / Systems | N.A. |
| Goal / Description | View complaint-related announcements. |
| Trigger | User / Complainant opens announcements. |
| Preconditions | User / Complainant has access to CMS. |
| Main Success Scenario | 1. User / Complainant opens announcement view. | 2. CMS displays complaint-related announcements. |
| Alternative Flows | - If no announcement exists, CMS shows no announcement entries. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | User / Complainant has viewed announcements. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | N/A |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-015 — Generate Operational Complaint Reports
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Handler |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Generate operational complaint reports. |
| Trigger | Complaint Handler requests an operational complaint report. |
| Preconditions | Complaint Handler role is active. |
| Main Success Scenario | 1. Complaint Handler opens reporting function. | 2. Complaint Handler selects operational report parameters available within CMS. | 3. CMS generates the operational complaint report. |
| Alternative Flows | - If no data matches selected parameters, CMS generates an empty/no-data result. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Operational complaint report is available to Complaint Handler. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-032 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-016 — View Complaint and Escalation Summaries
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | View complaint summaries and escalation summaries. |
| Trigger | Complaint Supervisor opens summary/report view. |
| Preconditions | Complaint Supervisor role is active. |
| Main Success Scenario | 1. Complaint Supervisor opens complaint summary view. | 2. CMS displays complaint summaries. | 3. Complaint Supervisor opens escalation summary view. | 4. CMS displays escalation summaries. |
| Alternative Flows | - If no data exists, CMS displays empty/no-data summary. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint Supervisor has viewed available summaries. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-032 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-017 — View CMS Reports and Analytics
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | System Admin |
| Supporting Actors / Systems | N.A. |
| Goal / Description | View complaint reports and analytics available within CMS without performing routine complaint operations. |
| Trigger | System Admin opens CMS reports or analytics view. |
| Preconditions | System Admin role is active. |
| Main Success Scenario | 1. System Admin opens CMS reporting/analytics view. | 2. CMS displays complaint reports available within CMS. | 3. CMS displays analytics available within CMS. |
| Alternative Flows | - If analytics/report data is unavailable, CMS displays empty/no-data result. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | System Admin has viewed reports/analytics available within CMS; no routine complaint operation is performed. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-032; BR-CMS-033 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A |
| Notes / TODO |  |
UC-CMS-018 — Manage CMS Roles
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | System Admin |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Assign or reassign Complaint Handler and Complaint Supervisor roles for specified duration. |
| Trigger | System Admin needs to assign or reassign CMS-specific roles. |
| Preconditions | Target institutional users exist outside CMS; CMS role-management function is available. |
| Main Success Scenario | 1. System Admin selects an existing institutional user for Complaint Handler role assignment and specified duration. | 2. System Admin selects an existing institutional user for Complaint Supervisor role assignment and specified duration. | 3. System Admin performs mid-cycle reassignment when required. | 4. CMS enforces exactly one active Complaint Handler and exactly one active Complaint Supervisor role-holder at a time within CMS. |
| Alternative Flows | - If assignment would violate active-role cardinality, CMS does not complete the role assignment until corrected. |
| Exception Flows | See Alternative Flows; no additional exception behavior is supported by the baseline. |
| Success Postcondition | CMS-specific Complaint Handler and Complaint Supervisor role assignments are recorded for specified duration. |
| Failure / Minimal Guarantee | No unsupported state transition is committed; previously recorded complaint data/history remain available. |
| Related Business Rules | BR-CMS-035; BR-CMS-036; BR-CMS-037; BR-CMS-038 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A — state-changing but single-actor administrative support; no cross-actor workflow progression is established. |
| Notes / TODO |  |
UC-CMS-019 — Verify Resolved Complaint for Closure (Complaint Supervisor)
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Verify a resolved complaint when the applicable closure process requires Complaint Supervisor verification, enabling CMS to record closure. |
| Trigger | A complaint is Resolved and the applicable closure process requires Complaint Supervisor verification. |
| Preconditions | Complaint is Resolved; applicable closure process identifies Complaint Supervisor verification. |
| Main Success Scenario | 1. Complaint Supervisor opens the resolved complaint. | 2. Reviews resolution details. | 3. Records successful verification. | 4. CMS records closure and updates status to Closed. |
| Alternative Flows | If verification is not recorded/successful, CMS does not close the complaint under this verification-required path. |
| Exception Flows | No additional exception behavior is supported by the baseline. |
| Success Postcondition | Resolved complaint is Closed after successful required Complaint Supervisor verification. |
| Failure / Minimal Guarantee | Complaint remains Resolved and recorded history is preserved. |
| Related Business Rules | BR-CMS-016; BR-CMS-017 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-01 r7; BW-CMS-03 r5 |
| Notes / TODO | ISS-CMS-010: behavior when verification is not required remains unspecified. |
UC-CMS-020 — Review Complaint Reopening Request
| Field | Content |
| UC Type | Actor-triggered |
| Primary Actor | Complaint Supervisor |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Review a recorded complaint reopening request and record an approval/denial outcome. |
| Trigger | A reopening request exists for a Closed complaint. |
| Preconditions | Complaint is Closed; a valid reopening request is recorded. |
| Main Success Scenario | 1. Complaint Supervisor opens the reopening request. | 2. Reviews the request. | 3. Records approval or denial. | 4. CMS records the reopening outcome. | 5. If approved, CMS reopens the complaint and updates status accordingly. | 6. CMS triggers the reopening-outcome email notification event where applicable. |
| Alternative Flows | If denied, the complaint remains Closed and the denial outcome is recorded. |
| Exception Flows | If the underlying complaint is no longer Closed, the request is not processed as a standard reopening decision without further policy. |
| Success Postcondition | Outcome is recorded; denied complaints remain Closed; approved complaints are reopened with status updated according to policy. |
| Failure / Minimal Guarantee | Complaint remains Closed and existing history is preserved if no valid decision is committed. |
| Related Business Rules | BR-CMS-019; BR-CMS-020; BR-CMS-021; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | CW-CMS-02 r2-r3; BW-CMS-05/06 r2 |
| Notes / TODO | ISS-CMS-008: exact lifecycle state after approved reopening is not defined by the baseline. |
UC-CMS-021 — Trigger Pre-Breach SLA Reminder
| Field | Content |
| UC Type | Event-triggered |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Trigger the configured reminder notification when an unresolved complaint approaches its applicable SLA breach condition. |
| Trigger | Time/SLA event: an unresolved complaint approaches the applicable externally configured SLA breach condition. |
| Preconditions | Complaint remains unresolved; complaint priority is associated with an applicable SLA timeline; applicable SLA values are available to CMS but are not specified in this baseline. |
| Main Success Scenario | 1. The configured time/SLA condition is reached for an unresolved complaint. | 2. CMS evaluates the complaint against its applicable priority-SLA association. | 3. CMS triggers the pre-breach reminder notification event. |
| Alternative Flows | - If the complaint is already resolved, no pre-breach reminder is triggered for that resolved complaint. |
| Exception Flows | No additional exception behavior is supported by the baseline. |
| Success Postcondition | The reminder notification trigger has been issued; complaint lifecycle and escalation status are unchanged by this use case. |
| Failure / Minimal Guarantee | No escalation or lifecycle state change is committed by the reminder service. |
| Related Business Rules | BR-CMS-026; BR-CMS-027; BR-CMS-028; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | N/A — reminder is non-state-changing. |
| Notes / TODO | Time/SLA condition is the trigger, not an actor. Exact SLA durations remain externally configured and unspecified in the module baseline. |
UC-CMS-022 — Automatically Escalate Complaint on SLA Breach
| Field | Content |
| UC Type | Event-triggered |
| Primary Actor | N.A. — Event-triggered |
| Supporting Actors / Systems | N.A. |
| Goal / Description | Automatically escalate an unresolved complaint when its applicable SLA timeline is breached. |
| Trigger | Time/SLA event: the applicable SLA timeline is breached while the complaint remains unresolved. |
| Preconditions | Complaint remains unresolved; complaint priority is associated with an applicable SLA timeline; complaint has not already been escalated for the same active condition. |
| Main Success Scenario | 1. The applicable SLA breach condition occurs while the complaint remains unresolved. | 2. CMS evaluates the complaint against the applicable SLA condition. | 3. CMS records automatic escalation and updates escalation status. | 4. CMS triggers the complaint-escalation email notification event. |
| Alternative Flows | - If the complaint has been resolved before the breach condition is processed, automatic escalation is not performed. |
| Exception Flows | No additional exception behavior is supported by the baseline. |
| Success Postcondition | Complaint escalation status records automatic escalation; the escalated complaint is available for Complaint Supervisor monitoring. |
| Failure / Minimal Guarantee | No unsupported escalation or complaint lifecycle state is committed. |
| Related Business Rules | BR-CMS-025; BR-CMS-026; BR-CMS-027; BR-CMS-029; BR-CMS-034 |
| Related CFRs / AFRs |  |
| Related Workflow(s) | BW-CMS-08 r1; CW-CMS-03 r2 |
| Notes / TODO | System is not a UC actor. This event-triggered UC is initiated by the SLA breach event; the authoritative workflow transition records Actor = System for the autonomous state change. |

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
