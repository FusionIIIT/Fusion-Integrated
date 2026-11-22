# Fusion ERP – File Tracking System (FTS)
## Problem Statement — Synchronized Baseline v1.2

| Field | Value |
| --- | --- |
| Project | Fusion ERP |
| Module Code | FTS |
| Module | File Tracking System (FTS) |
| Artifact | Problem Statement |
| Version | v1.2 |
| Date | 2026-08-22 |
| Basis | Frozen PS v1.2 + legacy package + synchronization capsule |
| Status | SYNCHRONIZED |
| Semantic Change | No substantive scope change; specification-boundary clarification only |

### Synchronization Note
The legacy PS v1.2 is substantively sound and remains the source/context baseline. The synchronization does not add new domain behavior. The final sentence concerning “System as primary actor” is treated as a specification-modeling convention rather than as FTS runtime functionality; secure-backup implementation remains outside FTS functional scope exactly as stated in §3.7.

### 1. Overview
Fusion is an ERP platform deployed at IIITDM Jabalpur to support administrative, academic, student, and allied institutional services through multiple integrated modules. Fusion provides role-based access, a unified dashboard, notification mechanisms, and inter-module integration capabilities. Platform-wide authentication, user-directory administration, and notification infrastructure are outside the File Tracking System scope unless explicitly represented as FTS role, access, notification, or audit events.

The File Tracking System (FTS) is a Fusion module designed to digitize and streamline academic and administrative file movement involving institute employees, namely faculty and staff. The module enables collaborative processing of institutional files by supporting file creation, draft handling, forwarding, return, commenting, attachment addition, tracking, audit logging, and archival in a secure and transparent manner.

FTS serves two explicit purposes: first, as a Fusion module through which authorized faculty, staff, and administrative role-holders collaboratively create, forward, comment on, and track files; and second, as a workflow-support service that exposes file-tracking APIs to other Fusion modules for module-specific approval and tracking workflows.

A file in FTS is a persistent composite data object consisting of mandatory user comments added at file creation and at each file-movement stage, and optional attachments that may be added where required. After a file is submitted and circulated, its existing comments, attachments, and movement records are append-only and are not deleted. A circulated file may only be archived by its owner after completion of its intended collaborative objective.

FTS improves institutional efficiency, accountability, and traceability by enforcing role-based access within the module, maintaining audit logs, supporting chronological version history of file actions and contents, and triggering file-related notifications.

### 2. Actors
FTS is used by the following actors: Institute Employee (Faculty / Staff) and System Admin. A basic Faculty or Staff user may be assigned additional institutional roles by authorized institutional authorities. Such roles may be exercised through the Fusion dashboard by switching role context. Role switching does not alter file ownership or previously recorded audit history.

#### 2.1 Institute Employee (Faculty / Staff)
An Institute Employee is a faculty or staff member who creates, receives, forwards, returns, tracks, and archives files according to assigned role permissions and file association. Responsibilities include:
• Creating new files under an assigned role.
• Saving draft files and editing them before submission.
• Discarding draft files before submission.
• Sending files to other institute employees.
• Viewing files received in the Inbox and files sent in the Outbox.
• Opening files associated with the user.
• Adding mandatory comments during file movement.
• Adding optional attachments during file creation or movement.
• Forwarding files to the next user in the workflow.
• Returning files to the sender.
• Tracking file movement history.
• Archiving completed files when the user is the file owner.

#### 2.2 System Admin
The System Admin is responsible for FTS-related system governance, user-role administration, access control, and audit/security oversight. Responsibilities include:
• Creating basic user accounts where this responsibility is represented within Fusion administration.
• Assigning and reassigning user roles used for FTS access.
• Managing role-based access control for FTS functions.
• Monitoring FTS system usage.
• Maintaining or viewing FTS security and audit logs.

The System Admin has no operational involvement in file workflows and does not create, forward, return, comment on, or archive operational files as part of routine file processing.

### 3. Functional Scope

#### 3.1 File Creation and Draft Management
- Any authorized institute employee may create a new file under an assigned role.
- A new file must include an initial mandatory comment.
- Attachments may optionally be added during file creation.
- A file may be saved as a draft before submission.
- A draft file may be edited later before submission.
- A draft file may be discarded before submission.
- Once submitted and circulated, a file is not deleted from FTS and may only be archived according to the archival rule.

#### 3.2 File Forwarding and Workflow Handling
- An authorized user may send a file to another institute employee within FTS.
- Each forwarding action requires the acting user to add a mandatory comment.
- Optional attachments may be added at each file-movement stage.
- A receiving user may forward the file to another user where permitted.
- A receiving user may return the file to the sender where permitted.
- All forwarding and return actions are recorded chronologically.

#### 3.3 Inbox and Outbox Management
- Files received by a user appear in the user's Inbox.
- Files sent by a user appear in the user's Outbox.
- Users may view and open files associated with them through the Inbox or Outbox.
- Users may act on files only according to assigned role permissions and file state.
- Files remain accessible to authorized associated users until archived by the file owner.

#### 3.4 File Tracking and History
- Every file maintains complete movement history from creation onward.
- The movement history includes sender details, receiver details, timestamps, comments added, and attachments added.
- Any authorized user associated with the file may view its tracking history.

#### 3.5 File Archival
- A file may be archived only by its owner.
- Archival indicates completion of the intended collaborative file workflow.
- Archived files remain permanently stored and readable to authorized users.
- Archived files cannot be modified or forwarded further.

#### 3.6 Access Control and Security
- FTS enforces role-based access control for file-related functions.
- Users can access only files they are authorized to view or act upon.
- Role switching does not affect file ownership or previously recorded audit history.
- Sensitive actions are restricted based on assigned roles and file association.

#### 3.7 Audit Logs and Versioning
- FTS maintains audit logs for file creation.
- FTS maintains audit logs for comments and attachments added to files.
- FTS maintains audit logs for forwarding and return actions.
- FTS maintains audit logs for archival actions.
- FTS maintains chronological version history through recorded file updates, including comments, attachments, and movement actions.
- Secure backups may be maintained through Fusion or institutional infrastructure to safeguard institutional records; backup implementation details are outside FTS functional scope unless represented as FTS records or controls.

#### 3.8 Notifications
- FTS triggers notifications when a file is received.
- FTS triggers notifications when a file is forwarded.
- FTS triggers notifications when a file is returned.
- FTS triggers notifications when a file is archived.
- FTS triggers notifications when a relevant role assignment or reassignment occurs.
- Notifications are delivered through Fusion integrated notification mechanisms. The central notification infrastructure is outside FTS scope.

#### 3.9 Integration with Fusion Modules
- FTS exposes APIs to other Fusion modules to support module-specific file workflows.
- FTS APIs may support approval chains defined by consuming Fusion modules.
- FTS APIs may support file-based request tracking for consuming Fusion modules.
- All FTS integrations comply with FTS role-based access and audit requirements.
- Consuming Fusion modules remain responsible for their own domain-specific actors, forms, approval policies, validation rules, and workflow semantics.

#### 3.10 Scope Boundaries
- FTS does not define the domain-specific approval policies of consuming Fusion modules.
- FTS does not perform HR, payroll, payment, procurement, inventory, academic decision-making, or central complaint-management functions.
- FTS relies on Fusion-level identity, role, dashboard, notification, backup, and security infrastructure where applicable.
- External institutional policies are outside FTS scope unless FTS explicitly validates, restricts, routes, records, notifies, audits, or reports based on them.

### Specification Modeling Convention
The System is not treated as a regular primary actor in use cases derived from this problem statement. System behavior appears as internal validation, access enforcement, state update, notification, audit logging, maintained data, or postcondition behavior. This sentence governs representation of the specification and is not an active FTS functional requirement.
