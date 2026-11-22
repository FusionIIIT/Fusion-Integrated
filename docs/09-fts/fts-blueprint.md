# File Tracking System (FTS) — Module Blueprint
**Document Version:** 1.1  
**Status:** Approved by Student 2 (with minor polish refinements incorporated)  
**Authors:** Student 1 (Builder: `@VarunJalagam`)  
**Approver:** Student 2 (Reviewer: `@navasamith9`)  
**Approval Date:** 2026-11-21  

---

## 1. §1.5 Specification Inventory

### 1.1 Coherent / Consolidated Requirements (CFRs) & Atomic Requirements (AFRs)
- **CFR-FTS-001**: Persistent Collaborative Record & Lifecycle Archival
  - **AFR-FTS-001**: File treated as persistent composite object (mandatory comments + optional attachments).
  - **AFR-FTS-002**: Preserve circulated files and accumulated contents without deletion.
  - **AFR-FTS-003**: File owner may archive completed file instead of deleting it.
  - **AFR-FTS-004**: Maintain full traceability of creation, movement, comments, attachments, archival.
- **CFR-FTS-002**: Operational Users & Admin Governance Boundary
  - **AFR-FTS-005**: Support Institute Employees (Faculty/Staff) as operational file workflow users.
  - **AFR-FTS-006**: Support System Admin administration of FTS-relevant roles and access context.
  - **AFR-FTS-007**: Support System Admin monitoring of FTS system usage within governance scope.
  - **AFR-FTS-008**: Support System Admin security and audit log oversight.
  - **AFR-FTS-009**: Prohibit System Admin from performing operational file actions on behalf of employees.
  - **AFR-FTS-010**: Support Institute Employees operating under selected assigned role contexts via Fusion dashboard.
- **CFR-FTS-003**: Authorized File Creation
  - **AFR-FTS-011**: Allow any Institute Employee to create a new file under an assigned role.
  - **AFR-FTS-012**: Require mandatory initial comment upon file creation.
  - **AFR-FTS-013**: Allow optional attachments during file creation.
- **CFR-FTS-004**: Pre-Circulation Draft Handling & Circulation Boundary
  - **AFR-FTS-014**: Allow Institute Employee to save newly created file as draft.
  - **AFR-FTS-015**: Allow Institute Employee to edit saved draft before submission.
  - **AFR-FTS-016**: Allow Institute Employee to discard draft before submission.
  - **AFR-FTS-017**: Prevent deletion of file once submitted and circulated.
  - **AFR-FTS-018**: Transition file from draft to circulated workflow state upon submission.
  - **AFR-FTS-019**: Preserve accumulated comments and attachments after submission.
- **CFR-FTS-005**: Authorized Forwarding and Return
  - **AFR-FTS-020**: Allow Institute Employee to send file to another Institute Employee.
  - **AFR-FTS-021**: Allow file to be sent to any Institute Employee regardless of receiver role.
  - **AFR-FTS-022**: Require mandatory comment for every movement action (forward and return).
  - **AFR-FTS-023**: Allow optional attachments at each movement stage.
  - **AFR-FTS-024**: Allow recipient user to forward received file onward.
  - **AFR-FTS-025**: Allow recipient user to return received file to sender.
  - **AFR-FTS-026**: Chronologically record each forwarding action.
  - **AFR-FTS-027**: Chronologically record each return action.
  - **AFR-FTS-028**: Update current file holder / pending recipient after forward or return.
- **CFR-FTS-006**: Inbox and Outbox Management
  - **AFR-FTS-029**: Show received files in user's Inbox.
  - **AFR-FTS-030**: Show sent files in user's Outbox.
  - **AFR-FTS-031**: Allow users to view and open files from Inbox.
  - **AFR-FTS-032**: Allow users to view and open files from Outbox.
  - **AFR-FTS-033**: Allow user to act on actionable files from Inbox/Outbox according to file state and role.
  - **AFR-FTS-034**: Keep files accessible to associated users until owner archives.
- **CFR-FTS-007**: Complete Chronological Tracking History
  - **AFR-FTS-035**: Maintain complete movement history from creation onward.
  - **AFR-FTS-036**: Record sender details for each movement event.
  - **AFR-FTS-037**: Record receiver details for each movement event.
  - **AFR-FTS-038**: Record timestamps for each movement event.
  - **AFR-FTS-039**: Record comments added at each movement event.
  - **AFR-FTS-040**: Record attachments added at each movement event.
  - **AFR-FTS-041**: Allow any associated user to view file tracking history.
- **CFR-FTS-008**: Lifecycle Closure & Archival
  - **AFR-FTS-042**: Allow file owner to archive file.
  - **AFR-FTS-043**: Prevent users other than owner from archiving file.
  - **AFR-FTS-044**: Treat archival as completion of collaborative file workflow.
  - **AFR-FTS-045**: Keep archived files permanently stored and readable.
  - **AFR-FTS-046**: Prevent modification of archived files.
  - **AFR-FTS-047**: Prevent forwarding of archived files.
- **CFR-FTS-009**: Role-Based Authorization & Role Context Switching
  - **AFR-FTS-048**: Enforce role-based access control for file operations.
  - **AFR-FTS-049**: Restrict file access to authorized users only.
  - **AFR-FTS-050**: Restrict file actions to authorized users only.
  - **AFR-FTS-051**: Preserve file ownership when a user switches roles.
  - **AFR-FTS-052**: Preserve audit history when a user switches roles.
  - **AFR-FTS-053**: Restrict sensitive actions according to assigned roles.
- **CFR-FTS-010**: Audit Logs & Versioning Traceability
  - **AFR-FTS-054**: Maintain audit log for file creation.
  - **AFR-FTS-055**: Maintain audit log for comments added.
  - **AFR-FTS-056**: Maintain audit log for attachments added.
  - **AFR-FTS-057**: Maintain audit log for forwarding actions.
  - **AFR-FTS-058**: Maintain audit log for return actions.
  - **AFR-FTS-059**: Maintain audit log for archival actions.
  - **AFR-FTS-060**: Maintain file versioning implicitly through chronological file updates.
- **CFR-FTS-011**: Event Notification Generation
  - **AFR-FTS-061**: Generate notification when file is received.
  - **AFR-FTS-062**: Generate notification when file is forwarded.
  - **AFR-FTS-063**: Generate notification when file is returned.
  - **AFR-FTS-064**: Generate notification when file is archived.
  - **AFR-FTS-065**: Generate notification when role is assigned/reassigned.
  - **AFR-FTS-066**: Deliver notifications through Fusion integrated mechanisms.
- **CFR-FTS-012**: Inter-Module Workflow Support & RBAC Integration
  - **AFR-FTS-067**: Expose APIs to other Fusion modules for module-specific workflows.
  - **AFR-FTS-068**: Expose APIs to other Fusion modules for approval chains.
  - **AFR-FTS-069**: Expose APIs to other Fusion modules for file-based request tracking.
  - **AFR-FTS-070**: Apply RBAC requirements to module integrations.
  - **AFR-FTS-071**: Apply audit requirements to module integrations.
  - **AFR-FTS-072**: Do not define domain-specific approval rules of consuming modules.

### 1.2 Use Cases (UCs)
- **FTS-UC-001**: Create New File (Actor: Institute Employee)
- **FTS-UC-002**: Edit or Discard Draft File (Actor: Institute Employee)
- **FTS-UC-003**: Send / Forward File to Employee (Actor: Institute Employee - Sender / Current Holder)
- **FTS-UC-004**: Return Received File (Actor: Institute Employee - Recipient / Current Holder)
- **FTS-UC-005**: View Inbox, Outbox, and Open Files (Actor: Institute Employee)
- **FTS-UC-006**: View File Tracking History (Actor: Institute Employee)
- **FTS-UC-007**: Archive Completed File (Actor: Institute Employee / File Owner)
- **FTS-UC-008**: Select Assigned Role Context for FTS (Actor: Institute Employee)
- **FTS-UC-009**: Administer FTS User Access Context (Actor: System Admin)
- **FTS-UC-010**: Use FTS Workflow-Support APIs (Actor: Authorized Consuming Fusion Module)
*(FTS-UC-011 retired; notification triggers represented as events/cross-cutting concerns).*

### 1.3 Business Rules (BRs)
- **BR-FTS-001**: Institute Employee Operational Access Rule
- **BR-FTS-002**: Role Switching Preservation Rule
- **BR-FTS-003**: Persistent Composite File Rule
- **BR-FTS-004**: Initial Comment Requirement
- **BR-FTS-005**: Draft Boundary Rule
- **BR-FTS-006**: File-Movement Comment Requirement
- **BR-FTS-007**: Receiver and Return Eligibility Rule
- **BR-FTS-008**: Chronological Movement Record Rule
- **BR-FTS-009**: Associated File Access Rule
- **BR-FTS-010**: Role-Based Access and Sensitive Action Rule
- **BR-FTS-011**: Audit Log and Chronological Versioning Rule
- **BR-FTS-012**: Archival Rule
- **BR-FTS-013**: Notification Trigger and Delivery Boundary Rule
- **BR-FTS-014**: FTS Integration Boundary Rule
*(BR-FTS-015 reclassified as modeling convention).*

### 1.4 Workflows (WFs)
- **BW-FTS-01**: Forward File to Recipient — Zero Onward Traversal (Basis)
- **BW-FTS-02**: Onward Forwarding — One Loop Traversal (Basis)
- **BW-FTS-03**: Return File to Previous Sender (Basis)
- **BW-FTS-04**: Archive Completed Circulated File (Basis)
- **BW-FTS-05**: Prepare and Circulate New File — Zero Draft-Edit Traversal (Basis)
- **BW-FTS-06**: Prepare and Circulate New File — One Draft-Edit Traversal (Basis)
- **BW-FTS-07**: Create and Discard Draft — Zero Draft-Edit Traversal (Basis)
- **BW-FTS-08**: Edit Once and Discard Draft — One Draft-Edit Traversal (Basis)
- **CW-FTS-01**: Collaborative File Circulation and Completion (Composite)
- **CW-FTS-02**: New File Preparation and Initial Outcome (Composite)

---

## 2. Phase 1 Questions & Answers (§2.1–§2.8)

### §2.1 — Is this one bounded context?
Yes. FTS is a single cohesive bounded context responsible for the lifecycle, tracking, movement, commenting, attachment management, and audit logging of institutional files within Fusion. It does not perform domain-specific administrative logic (HR, payroll, academics).

### §2.2 — What does it need from other modules?
1. **IAM (`fusion_auth` / `Fusion_System_Administrator`)**:
   - Authentication & Role verification: User authentication via session, role context (`faculty`, `staff`, or administrative role context).
   - Recipient directory resolution: resolving valid recipient Institute Employees.
2. **Notification delivery**:
   - Handing off notification events to Fusion's notification mechanisms.
3. Consuming modules consume FTS via `modules.fts.contracts` for module-specific request tracking and approval chains.

### §2.3 — Identity
- File records are identified by internal integer primary key ID and a human-readable file reference number (e.g. `FTS-YYYYMMDD-XXXX`).
- Users are identified by their Fusion IAM `user_id` (integer) and `username`.
- Role context: the active designation/role under which the user created or acted on the file is stored alongside `user_id` to preserve historical audit context across role switches.

### §2.4 — Who decides, and who may see
- **Institute Employee (Faculty / Staff)**:
  - May create files, save/edit/discard drafts.
  - May view received files in Inbox and sent files in Outbox.
  - Current file holder may forward or return an active file.
  - Associated users (creator, senders, recipients in movement chain) may view file tracking history and details.
  - Only File Owner (creator) may archive a completed file.
- **System Admin**:
  - May monitor usage, view security and audit logs, and administer role contexts.
  - Prohibited from operational file processing (creating, forwarding, returning, commenting, or archiving operational files).
- **Consuming Modules**:
  - Authorized service calls via `contracts.py` or API endpoints with appropriate service token/permissions.

### §2.5 — Scope
- **Tenancy**: Institute-wide single deployment.
- **Association**: A user is associated with a file if they are the file owner/creator, or have participated in its movement chain (as sender or receiver), or are the current holder.
- **Access scoping**: Only associated authorized employees may view file details, comments, and history. Other users receive 403 Forbidden.

### §2.6 — Time
- All movements, comments, audit logs, and status changes are timestamped with UTC timestamps (`created_at`).
- Chronological ordering is strictly preserved and append-only.

### §2.7 — Money / Quota / Balance
- FTS does not handle financial transactions, quotas, or balances.
- **File attachment storage validation**: Exact limits (e.g. 10MB per attachment, specific allowed MIME types like PDF, JPEG, PNG, DOCX) to be finalized in Fusion platform-wide `core.files` configuration, but FTS will enforce the platform's validation hooks directly on upload/creation.

### §2.8 — Policy
- Draft files can be edited or discarded.
- Circulated files can never be deleted or discarded.
- Every forward and return movement requires a non-empty comment.
- Archival is strictly restricted to the file owner when active; archived files become permanently read-only and cannot be forwarded or modified.

---

## 3. Phase 2 Blueprint (§3.1–§3.8)

### 3.1 (a) Traceability Table
| CFR / AFR | Business Rule | Use Case | Workflow | Model / Component | Endpoint |
|---|---|---|---|---|---|
| CFR-FTS-001 (AFR-001..004) | BR-FTS-003, BR-FTS-011, BR-FTS-012 | FTS-UC-001, 003, 007 | BW-FTS-01..08, CW-FTS-01, 02 | `File`, `FileComment`, `FileAttachment` | `/api/fts/files/` |
| CFR-FTS-002 (AFR-005..010) | BR-FTS-001, BR-FTS-002, BR-FTS-010 | FTS-UC-008, 009 | N/A | `FileAuditLog`, `registry.py` | `/api/fts/governance/` |
| CFR-FTS-003 (AFR-011..013) | BR-FTS-001, BR-FTS-004 | FTS-UC-001 | BW-FTS-05..08, CW-FTS-02 | `File`, `FileComment`, `FileAttachment` | `POST /api/fts/files/` |
| CFR-FTS-004 (AFR-014..019) | BR-FTS-003, BR-FTS-005 | FTS-UC-001, 002 | BW-FTS-05..08, CW-FTS-02 | `File`, `domain/state_machine.py` | `POST /api/fts/files/{id}/discard/`, `PUT /api/fts/files/{id}/` |
| CFR-FTS-005 (AFR-020..028) | BR-FTS-006, BR-FTS-007, BR-FTS-008 | FTS-UC-003, 004 | BW-FTS-01..03, CW-FTS-01 | `FileMovement`, `FileComment`, `FileAttachment` | `POST /api/fts/files/{id}/forward/`, `POST /api/fts/files/{id}/return/` |
| CFR-FTS-006 (AFR-029..034) | BR-FTS-009, BR-FTS-010 | FTS-UC-005 | CW-FTS-01 | `selectors/files.py` | `GET /api/fts/inbox/`, `GET /api/fts/outbox/`, `GET /api/fts/files/{id}/` |
| CFR-FTS-007 (AFR-035..041) | BR-FTS-008, BR-FTS-009, BR-FTS-011 | FTS-UC-006 | CW-FTS-01 | `FileMovement`, `selectors/history.py` | `GET /api/fts/files/{id}/history/` |
| CFR-FTS-008 (AFR-042..047) | BR-FTS-010, BR-FTS-012 | FTS-UC-007 | BW-FTS-04, CW-FTS-01 | `File`, `domain/state_machine.py` | `POST /api/fts/files/{id}/archive/` |
| CFR-FTS-009 (AFR-048..053) | BR-FTS-001, BR-FTS-002, BR-FTS-010 | FTS-UC-008 | N/A | `api/permissions.py`, `registry.py` | Across all endpoints |
| CFR-FTS-010 (AFR-054..060) | BR-FTS-011 | FTS-UC-001..007, 010 | All workflows | `FileAuditLog` | `GET /api/fts/governance/audit-logs/` |
| CFR-FTS-011 (AFR-061..066) | BR-FTS-013 | FTS-UC-003, 004, 007, 009 | BW-FTS-01..06 | `NotificationEvent`, `tasks.py` | Internal / Celery |
| CFR-FTS-012 (AFR-067..072) | BR-FTS-014 | FTS-UC-010 | N/A | `contracts.py`, `api/integration.py` | `/api/fts/integrations/` |

### 3.2 (b) Domain Model
- **`File`**:
  - `id`: BigAutoField (PK)
  - `reference_number`: CharField(max_length=64, unique=True, indexed)
  - `subject`: CharField(max_length=255)
  - `description`: TextField(blank=True)
  - `status`: CharField (choices: `DRAFT`, `CIRCULATED`, `ARCHIVED`, `DISCARDED`)
  - `owner_user_id`: IntegerField(indexed)
  - `owner_username`: CharField(max_length=150)
  - `owner_role`: CharField(max_length=100)
  - `current_holder_user_id`: IntegerField(indexed)
  - `current_holder_username`: CharField(max_length=150)
  - `current_holder_role`: CharField(max_length=100)
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)
  - `archived_at`: DateTimeField(null=True, blank=True)
- **`FileMovement`**:
  - `id`: BigAutoField (PK)
  - `file`: ForeignKey to `File` (related_name="movements")
  - `sequence`: PositiveIntegerField()
  - `movement_type`: CharField (choices: `CREATION`, `FORWARD`, `RETURN`, `ARCHIVE`)
  - `from_user_id`: IntegerField()
  - `from_username`: CharField(max_length=150)
  - `from_role`: CharField(max_length=100)
  - `to_user_id`: IntegerField()
  - `to_username`: CharField(max_length=150)
  - `to_role`: CharField(max_length=100)
  - `created_at`: DateTimeField(auto_now_add=True)
- **`FileComment`**:
  - `id`: BigAutoField (PK)
  - `file`: ForeignKey to `File` (related_name="comments")
  - `movement`: ForeignKey to `FileMovement` (null=True, blank=True, related_name="comments")
  - `author_user_id`: IntegerField()
  - `author_username`: CharField(max_length=150)
  - `author_role`: CharField(max_length=100)
  - `comment_text`: TextField()
  - `created_at`: DateTimeField(auto_now_add=True)
  - *Atomic Constraint (BR-FTS-006)*: The creation of a `FileMovement` and its primary `FileComment` must occur in a single atomic database transaction (`transaction.atomic`). A movement record cannot exist without its mandatory comment, preventing orphaned movements at the database level.
- **`FileAttachment`**:
  - `id`: BigAutoField (PK)
  - `file`: ForeignKey to `File` (related_name="attachments")
  - `movement`: ForeignKey to `FileMovement` (null=True, blank=True, related_name="attachments")
  - `uploader_user_id`: IntegerField()
  - `uploader_username`: CharField(max_length=150)
  - `file_name`: CharField(max_length=255)
  - `file_url`: CharField(max_length=1024)
  - `file_size`: PositiveIntegerField()
  - `mime_type`: CharField(max_length=100)
  - `created_at`: DateTimeField(auto_now_add=True)
- **`FileAuditLog`**:
  - `id`: BigAutoField (PK)
  - `file_id`: IntegerField(indexed)
  - `action`: CharField(max_length=50) (e.g., `FILE_CREATED`, `FILE_UPDATED`, `DRAFT_DISCARDED`, `FILE_FORWARDED`, `FILE_RETURNED`, `FILE_ARCHIVED`, `INTEGRATION_INVOKED`)
  - `actor_user_id`: IntegerField()
  - `actor_username`: CharField(max_length=150)
  - `actor_role`: CharField(max_length=100)
  - `details`: JSONField(default=dict)
  - `timestamp`: DateTimeField(auto_now_add=True)
- **`NotificationEvent`**:
  - `id`: BigAutoField (PK)
  - `event_type`: CharField(max_length=50)
  - `recipient_user_id`: IntegerField()
  - `payload`: JSONField(default=dict)
  - `delivered`: BooleanField(default=False)
  - `created_at`: DateTimeField(auto_now_add=True)

### 3.3 (c) State Machine (`domain/state_machine.py`)
- **States**:
  - `DRAFT`: Pre-circulation state. Can be edited, discarded, or submitted (circulated).
  - `CIRCULATED`: Active collaborative workflow state. Forward, return, and comment allowed. Cannot be discarded or deleted.
  - `ARCHIVED`: Final closed state. Owner only. Read-only; cannot be forwarded or modified.
  - `DISCARDED`: Terminal pre-circulation state. Functions as a soft-delete/terminal state for auditability (satisfying AFR-FTS-054), but these records are strictly excluded from all standard Inbox/Outbox/Draft queries (enforced by `selectors/files.py`).
- **Allowed Transitions**:
  - `DRAFT` -> `DRAFT` (Edit action)
  - `DRAFT` -> `DISCARDED` (Discard action)
  - `DRAFT` -> `CIRCULATED` (First Send/Forward action with recipient: Transitions `DRAFT` $\to$ `CIRCULATED` on initial circulation)
  - `CIRCULATED` -> `CIRCULATED` (Forward to recipient or Return to sender: Remains `CIRCULATED` on onward forwarding)
  - `CIRCULATED` -> `ARCHIVED` (Owner Archival action)
- **Invalid Transitions (raise `InvalidStateTransitionError`)**:
  - `CIRCULATED` -> `DISCARDED` (Prohibited by BR-FTS-003, BR-FTS-005)
  - `ARCHIVED` -> any state (Archived files are permanent and immutable, BR-FTS-012)
  - `DISCARDED` -> any state (Terminal)

### 3.4 (d) Permission List & Role Grants (`registry.py`)
- Permissions:
  - `fts.file.create`: Create files and save/edit/discard drafts.
  - `fts.file.forward`: Forward active files.
  - `fts.file.return`: Return received active files.
  - `fts.file.archive`: Archive completed files (restricted to file owner).
  - `fts.file.view`: View associated files in Inbox/Outbox and tracking history.
  - `fts.governance.view`: View system usage, security, and audit logs.
  - `fts.governance.manage`: Administer FTS role-access context.
  - `fts.integration.access`: Invoke FTS workflow-support APIs.
- System Permissions:
  - `fts.notification.dispatch`: Background task delivery of notifications.
- Role Grants:
  - **`faculty`**: `["fts.file.create", "fts.file.forward", "fts.file.return", "fts.file.archive", "fts.file.view"]`
  - **`staff`**: `["fts.file.create", "fts.file.forward", "fts.file.return", "fts.file.archive", "fts.file.view"]`
  - **`admin` / `System Admin`**: `["fts.governance.view", "fts.governance.manage"]` *(Explicitly excluded from operational file processing permissions, satisfying BR-FTS-001 and AFR-FTS-009)*.

### 3.5 (e) Endpoint List
All endpoints reside under `/api/fts/`.
1. **`POST /api/fts/files/`**:
   - Permission: `fts.file.create` (Employee only)
   - Body: `{"subject": str, "description": str, "comment": str (mandatory), "attachments": list (optional), "is_draft": bool}`
   - Action: Creates file in `DRAFT` or immediate `CIRCULATED` state if recipient provided.
2. **`GET /api/fts/inbox/`**:
   - Permission: `fts.file.view`
   - Returns: List of active circulated files where `current_holder_user_id == request.principal.user_id`. (Excludes `DISCARDED` and `DRAFT`).
3. **`GET /api/fts/outbox/`**:
   - Permission: `fts.file.view`
   - Returns: List of circulated files sent by `request.principal.user_id`. (Excludes `DISCARDED` and `DRAFT`).
4. **`GET /api/fts/drafts/`**:
   - Permission: `fts.file.create`
   - Returns: List of active draft files (`status == 'DRAFT'`) owned by `request.principal.user_id`.
5. **`GET /api/fts/files/{id}/`**:
   - Permission: `fts.file.view`
   - Guard: User must be associated with the file (owner, sender, recipient, or current holder) or admin for governance.
   - Returns: File composite object, including current status, holder, comments, and attachments.
6. **`PUT /api/fts/files/{id}/`**:
   - Permission: `fts.file.create`
   - Guard: File must be in `DRAFT` state and owned by user.
   - Body: `{"subject": str, "description": str, "comment": str, "attachments": list}`
7. **`POST /api/fts/files/{id}/discard/`**:
   - Permission: `fts.file.create`
   - Guard: File must be in `DRAFT` state and owned by user.
   - Action: Transitions draft to `DISCARDED` and records audit entry.
8. **`POST /api/fts/files/{id}/forward/`**:
   - Permission: `fts.file.forward`
   - Guard: File in `DRAFT` (initial circulation) or `CIRCULATED` (onward forwarding). User must be current holder.
   - Transition Outcome: Transitions `DRAFT` $\to$ `CIRCULATED` on initial circulation; remains `CIRCULATED` on onward forwarding.
   - Body: `{"to_user_id": int, "to_role": str, "comment": str (mandatory), "attachments": list (optional)}`
   - Atomic Transaction: Movement, Comment, Holder Update, and Audit Log execute atomically.
9. **`POST /api/fts/files/{id}/return/`**:
   - Permission: `fts.file.return`
   - Guard: File in `CIRCULATED` state. User must be current recipient. Target is the sender of the latest movement.
   - Transition Outcome: Remains `CIRCULATED`, holder updated to previous sender.
   - Body: `{"comment": str (mandatory), "attachments": list (optional)}`
   - Atomic Transaction: Movement, Comment, Holder Update, and Audit Log execute atomically.
10. **`POST /api/fts/files/{id}/archive/`**:
    - Permission: `fts.file.archive`
    - Guard: User must be the `owner_user_id`. File must be in `CIRCULATED` state.
    - Action: Transitions file to `ARCHIVED`. Immutable henceforth.
11. **`GET /api/fts/files/{id}/history/`**:
    - Permission: `fts.file.view`
    - Guard: Associated user only.
    - Returns: Chronological list of movements, comments, attachments, and timestamps.
12. **`GET /api/fts/governance/audit-logs/`**:
    - Permission: `fts.governance.view` (System Admin only)
    - Returns: System-wide audit log entries.
13. **`GET /api/fts/governance/usage/`**:
    - Permission: `fts.governance.view` (System Admin only)
    - Returns: Aggregate usage statistics (total files, active files, archived files).
14. **`POST /api/fts/integrations/requests/`**:
    - Permission: `fts.integration.access`
    - Service endpoint for consuming modules to initiate file tracking.

### 3.6 (f) Contracts (`contracts.py`)
Functions exposed to other modules:
- `create_tracked_file(*, subject: str, description: str, creator_user_id: int, creator_username: str, creator_role: str, initial_comment: str, recipient_user_id: int, recipient_username: str, recipient_role: str) -> dict`: Creates and circulates a file on behalf of another module.
- `get_file_status(*, file_id: int) -> dict`: Returns status, current holder, and timestamps.
- `get_files_for_user(*, user_id: int) -> list[dict]`: Returns summary of files associated with user.

### 3.7 (g) Scheduled Work (`schedule.py` & `tasks.py`)
- `dispatch_pending_notifications`: Periodic task to process undelivered `NotificationEvent` rows and dispatch to Fusion notification mechanism.
- `verify_audit_integrity`: Periodic integrity check ensuring movement sequence numbers and timestamps are monotonically strictly increasing.

### 3.8 (h) Open Questions & Known Gaps
- **Objective Completion Criterion**: Governed by the file owner's decision to invoke `FTS-UC-007` (Archive). No automated closure condition is mandated or assumed.
- **Attachment Storage**: Managed via platform validation hooks (`core.files`), stored as URL references with size, mime-type, and checksums.
- **No known gaps**: The full specification (CFR-FTS-001..012, AFR-FTS-001..072, BR-FTS-001..014, FTS-UC-001..010, BW-FTS-01..08, CW-FTS-01..02) is covered completely without stubs or placeholders.

---
*(End of Blueprint v1.1)*
