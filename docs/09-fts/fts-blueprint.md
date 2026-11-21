# File Tracking System (FTS) Module Blueprint

| Field | Value |
| :--- | :--- |
| **Module Name** | File Tracking System (FTS) |
| **Module Code** | `fts` |
| **Document Version** | 1.0 (Phase 2 Blueprint) |
| **Specification Source** | `C:\Fusion\FTS_Specifications_Bundle_v1.3_FINAL` |
| **Status** | APPROVED BY STUDENT 2 (T Aravind Kumar, 24BCS251) |
| **Author** | Harish Reddy (Student 1 - Builder, 24BCS201) |

---

## §1 — Phase 1: Pre-Code Architecture Answers

### Step 2.1 — Bounded Context
FTS is a single bounded context managing institutional file records, tracking histories, movement between holders, mandatory comments, and attachments. It provides a collaborative digital workflow for Institute Employees (faculty/staff). External domain logic (e.g. leave decisions, placement policy) remains in external consuming modules.

### Step 2.2 — Cross-Module Dependencies
FTS depends on:
1. `fusion_auth` (IAM): Token verification, principal claims (`user_id`, active role/designation, permissions).
2. `modules/directory`: Local projection for looking up employee details (display names, designations) for receiver autocomplete without directly querying `fusionlab` tables.
FTS exposes workflow tracking APIs via `contracts.py` to other Fusion modules.

### Step 2.3 — Identity Model
No foreign keys to `auth_user` or `Employee`. All actor representations store plain integer `user_id` values conforming to `core/db/mixins.py::UserScopedModel`:
- `creator_id`: Integer user ID of the employee who created the file/draft.
- `current_holder_id`: Integer user ID of the employee currently holding the file.
- `sender_id` & `receiver_id`: Integer user IDs on movement transitions.
- `uploader_id`: Integer user ID on file attachments.
- `author_id`: Integer user ID on file comments.

### Step 2.4 — Actors and Role Grants
Per Problem Statement §2, CFR-FTS-002, and BR-FTS-001:
- **Institute Employee (`faculty`, `staff`)**: The only operational actors permitted to create, forward, return, comment on, and archive files.
- **System Admin (`admin`, `system_admin`)**: Pure governance actor (RBAC and system audit). Strictly prohibited by `BR-FTS-001` and `AFR-FTS-009` from initiating or participating in operational file movements.
- **Role Context**: All file operations record the persistent `user_id` and acting designation context without mutating historical ownership upon role switching (`BR-FTS-002`).

### Step 2.5 — Read Scoping
Queries are scoped at the selector layer (`selectors/scoping.py`):
- `Inbox`: Active circulating files where `current_holder_id == request.user_id`.
- `Outbox`: Files where user has initiated movement to another recipient.
- `Drafts`: Files where `creator_id == request.user_id` and `status == 'draft'`.
- `File Detail / History`: Access is granted if and only if the requesting user is associated with the file (creator, holder, or participant in movement history) per `BR-FTS-009`. Out-of-scope requests yield **404 Not Found** (never 403, preventing resource enumeration).

### Step 2.6 — Time & Scheduling
FTS workflows are actor-driven. File movement transitions occur synchronously upon submission/forwarding/return/archival. No auto-expiring workflows or date advances exist in the core spec. Periodic housekeeping (e.g. purging discarded draft orphan attachments or generating audit summaries) can be registered as Celery tasks in `schedule.py`.

### Step 2.7 — Quota / Balance
Not applicable. FTS contains no ledger or financial balance computations.

### Step 2.8 — Policy
Lifecycle policies (draft boundary, archival by owner only, append-only history after circulation) are hard-coded invariants enforced in the domain and database layer.

---

## §2 — Step 3.1 (a) Traceability Table

| Id | What it requires | Layer it belongs in | Enforcement point (planned) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **CFR-FTS-001** / AFR-001..004 | Persistent composite file lifecycle, comments, attachments, owner archival | Domain & Models | `domain/state_machine.py`, `models/file.py` | Append-only after circulation |
| **CFR-FTS-002** / AFR-005..010 | Employee operational access vs Admin governance restriction | Domain & API | `services/file_service.py`, `api/permissions.py` | System Admin rejected from file actions |
| **CFR-FTS-003** / AFR-011..013 | File creation with mandatory initial comment and optional attachment | Services & Models | `services/file_service.py::create_file` | Transactional creation |
| **CFR-FTS-004** / AFR-014..019 | Draft save, edit, discard; transition to circulating | Domain & Services | `domain/state_machine.py`, `services/draft_service.py` | Discard only allowed in draft state |
| **CFR-FTS-005** / AFR-020..028 | File forward and return with mandatory comment and movement logging | Domain & Services | `domain/state_machine.py`, `services/movement_service.py` | Validates receiver eligibility and updates current holder |
| **CFR-FTS-006** / AFR-029..034 | Inbox/Outbox listing and authorized file inspection | Selectors & Views | `selectors/scoping.py`, `api/views.py` | 404 for unassociated files |
| **CFR-FTS-007** / AFR-035..041 | Chronological file movement tracking history | Selectors & Models | `models/movement.py`, `selectors/history.py` | Ordered by movement sequence / timestamp |
| **CFR-FTS-008** / AFR-042..047 | Owner-only archival of completed circulated files | Domain & Services | `domain/state_machine.py`, `services/file_service.py::archive_file` | Terminal state; non-forwardable |
| **CFR-FTS-009** / AFR-048..053 | RBAC enforcement & role switching preservation | IAM / Middleware & Selectors | `api/permissions.py`, `selectors/scoping.py` | Preserves identity across active role change |
| **CFR-FTS-010** / AFR-054..060 | Audit logs and versioning of actions | Services & Models | `services/audit_service.py`, `models/audit.py` | Append-only audit records |
| **CFR-FTS-011** / AFR-061..066 | Notification dispatch on file events | Services / Tasks | `services/notification_service.py` | Emits outbox events for notification delivery |
| **CFR-FTS-012** / AFR-067..072 | External module API integration for approval workflows | Contracts & API | `contracts.py`, `api/views_internal.py` | Standard plural contracts |
| **BR-FTS-001** | Only Institute Employees may perform operational file actions | Domain & Permissions | `api/permissions.py::IsInstituteEmployee`, `domain/rules.py` | Blocks Admin & non-employee roles |
| **BR-FTS-002** | Role switching preserves ownership and history | Models & Selectors | `models/file.py`, `models/movement.py` | Bound to `user_id` |
| **BR-FTS-003** | Persistent composite file: no deletion of comments/attachments post-circulation | Models & Services | `models/comment.py`, `models/attachment.py` | Enforced via immutability checks |
| **BR-FTS-004** | Initial comment required on creation | Domain / Validation | `domain/rules.py::validate_initial_comment` | Non-empty comment check |
| **BR-FTS-005** | Draft boundary: drafts cannot be forwarded; can be edited/discarded | Domain & State Machine | `domain/state_machine.py` | State check |
| **BR-FTS-006** | Movement comment required on every forward/return | Domain / Validation | `domain/rules.py::validate_movement_comment` | Non-empty check on action |
| **BR-FTS-007** | Receiver eligibility and return-to-sender validation | Domain / Validation | `domain/rules.py::validate_receiver` | Cannot forward to self; return targets previous holder |
| **BR-FTS-008** | Chronological movement recording | Models | `models/movement.py` | Auto-increment sequence & timestamp |
| **BR-FTS-009** | Associated file access (creator, past holder, current holder) | Selectors | `selectors/scoping.py::get_visible_file_detail` | Returns 404 for unauthorized access |
| **BR-FTS-010** | Role-based access and sensitive action restrictions | Domain & Permissions | `api/permissions.py`, `services/file_service.py` | Strict checks on state mutations |
| **BR-FTS-011** | Audit log and chronological versioning | Models & Services | `models/audit.py`, `services/audit_service.py` | Immutable audit log table |
| **BR-FTS-012** | Archival restricted to file owner on circulating files | Domain & Services | `domain/state_machine.py`, `services/file_service.py` | Checks `owner_id == actor_id` and `status == 'circulating'` |
| **BR-FTS-013** | Notification trigger boundary | Services | `services/notification_service.py` | Decoupled notification dispatch |
| **BR-FTS-014** | FTS integration boundary | Contracts & API | `contracts.py` | Plural interfaces only |
| **FTS-UC-001** | Create New File | Services | `services/file_service.py::create_file` | Handles draft or direct circulation |
| **FTS-UC-002** | Edit or Discard Draft File | Services | `services/draft_service.py` | Modifies or deletes draft before circulation |
| **FTS-UC-003** | Send / Forward File to Employee | Services | `services/movement_service.py::forward_file` | Updates holder, creates movement record |
| **FTS-UC-004** | Return Received File | Services | `services/movement_service.py::return_file` | Reverts holder to previous sender |
| **FTS-UC-005** | View Inbox, Outbox, and Open Files | Selectors / API | `selectors/scoping.py`, `api/views.py` | Scoped list endpoints |
| **FTS-UC-006** | View File Tracking History | Selectors / API | `selectors/history.py`, `api/views.py` | Detail view includes complete trail |
| **FTS-UC-007** | Archive Completed File | Services / API | `services/file_service.py::archive_file` | Owner archival |
| **FTS-UC-008** | Select Assigned Role Context for FTS | Client / Session | `client/src/modules/fts/` | Reads active role from auth context |
| **FTS-UC-009** | Administer FTS User Access Context | IAM | External (IAM / System Admin) | FTS verifies incoming role grants |
| **FTS-UC-010** | Use FTS Workflow-Support APIs | Contracts | `contracts.py` | Inter-module programmatic operations |
| **BW-FTS-01..08** | Basis Workflows (Forwarding, Return, Archival, Draft Lifecycle) | Domain | `domain/state_machine.py` | Transitions: `DRAFT`, `CIRCULATING`, `ARCHIVED`, `DISCARDED` |
| **CW-FTS-01..02** | Composite Workflows (Full File Lifecycle) | Domain & Services | `domain/state_machine.py` | Verified across end-to-end execution |

---

## §3 — Step 3.2 (b) Domain Model & Database Constraints

### 1. `FTSFile` (`fts_file`)
Core aggregate representing an institutional file:
- `id`: AutoField / BigAutoField (PK).
- `file_id`: CharField(max_length=64, unique=True, db_index=True) (e.g. `FTS-2026-00001`).
- `subject`: CharField(max_length=255).
- `description`: TextField(blank=True).
- `status`: CharField(max_length=32, choices=['draft', 'circulating', 'archived', 'discarded'], default='draft', db_index=True).
- `creator_id`: IntegerField(db_index=True) (User ID of creator).
- `owner_id`: IntegerField(db_index=True) (User ID of owner; defaults to creator).
- `current_holder_id`: IntegerField(null=True, blank=True, db_index=True).
- `created_at`: DateTimeField(auto_now_add=True).
- `updated_at`: DateTimeField(auto_now=True).

**Database Constraints:**
- `CheckConstraint(check=Q(status__in=['draft', 'circulating', 'archived', 'discarded']), name="fts_file_valid_status")`
- `CheckConstraint(check=~Q(status='circulating') | Q(current_holder_id__isnull=False), name="fts_circulating_requires_holder")`

### 2. `FileMovement` (`fts_movement`)
Chronological append-only movement log:
- `id`: AutoField (PK).
- `file`: ForeignKey(`FTSFile`, on_delete=CASCADE, related_name='movements').
- `sequence_number`: PositiveIntegerField().
- `sender_id`: IntegerField(db_index=True).
- `sender_designation`: CharField(max_length=128).
- `receiver_id`: IntegerField(db_index=True).
- `receiver_designation`: CharField(max_length=128).
- `action`: CharField(max_length=32, choices=['created', 'forwarded', 'returned', 'archived']).
- `remarks`: TextField(blank=True).
- `timestamp`: DateTimeField(auto_now_add=True, db_index=True).

**Database Constraints:**
- `UniqueConstraint(fields=['file', 'sequence_number'], name="fts_movement_unique_seq")`
- `CheckConstraint(check=Q(action__in=['created', 'forwarded', 'returned', 'archived']), name="fts_movement_valid_action")`

### 3. `FileComment` (`fts_comment`)
Append-only comment stream:
- `id`: AutoField (PK).
- `file`: ForeignKey(`FTSFile`, on_delete=CASCADE, related_name='comments').
- `author_id`: IntegerField(db_index=True).
- `author_designation`: CharField(max_length=128).
- `comment_text`: TextField().
- `movement`: ForeignKey(`FileMovement`, null=True, blank=True, on_delete=SET_NULL, related_name='associated_comments').
- `created_at`: DateTimeField(auto_now_add=True).

**Database Invariants:**
- Comments once saved to circulating files are immutable (enforced via service & model `save()` guard).

### 4. `FileAttachment` (`fts_attachment`)
Attached artifacts/files:
- `id`: AutoField (PK).
- `file`: ForeignKey(`FTSFile`, on_delete=CASCADE, related_name='attachments').
- `uploader_id`: IntegerField(db_index=True).
- `file_name`: CharField(max_length=255).
- `file_path`: CharField(max_length=512) or FileField.
- `file_size`: PositiveIntegerField().
- `mime_type`: CharField(max_length=128).
- `movement`: ForeignKey(`FileMovement`, null=True, blank=True, on_delete=SET_NULL).
- `created_at`: DateTimeField(auto_now_add=True).

**Database Constraints:**
- Attachments on circulating files cannot be deleted.

### 5. `FTSAuditLog` (`fts_audit_log`)
Immutable security and audit log:
- `id`: AutoField (PK).
- `file`: ForeignKey(`FTSFile`, null=True, blank=True, on_delete=SET_NULL).
- `actor_id`: IntegerField(db_index=True).
- `actor_role`: CharField(max_length=128).
- `action_type`: CharField(max_length=64, db_index=True).
- `details`: JSONField(default=dict).
- `timestamp`: DateTimeField(auto_now_add=True, db_index=True).

---

## §4 — Step 3.3 (c) State Machine

Declarative Transition Table: `(Current State, Event / Action, Actor Constraint) -> Next State`

| Current State | Event / Action | Permitted Actor | Target State | Invariant / Precondition |
| :--- | :--- | :--- | :--- | :--- |
| `[None]` | `SAVE_DRAFT` | Institute Employee | `DRAFT` | Mandatory initial comment |
| `[None]` | `SUBMIT_CREATE` | Institute Employee | `CIRCULATING` | Initial comment; recipient specified; sender != recipient |
| `DRAFT` | `EDIT_DRAFT` | File Creator only | `DRAFT` | Modifies subject, description, comments, attachments |
| `DRAFT` | `DISCARD` | File Creator only | `DISCARDED` | Removes draft / marks discarded |
| `DRAFT` | `SEND_FIRST` | File Creator only | `CIRCULATING` | Initial movement record created, current holder set to receiver |
| `CIRCULATING` | `FORWARD` | Current Holder only | `CIRCULATING` | Mandatory comment; recipient is active institute employee; sender != receiver |
| `CIRCULATING` | `RETURN` | Current Holder only | `CIRCULATING` | Mandatory comment; receiver MUST be previous sender in movement history |
| `CIRCULATING` | `ARCHIVE` | File Owner only | `ARCHIVED` | Owner must be current holder or file workflow concluded |
| `ARCHIVED` | `*` | Any | `[REJECT]` | Terminal state: immutable, non-forwardable |
| `DISCARDED` | `*` | Any | `[REJECT]` | Terminal state: no further action |

Any unlisted transition raises `InvalidFileStateTransitionError` in the domain layer.

---

## §5 — Step 3.4 (d) Permission List (`modules/fts/registry.py`)

Using strictly the closed verb vocabulary from `docs/02-iam/rbac-model.md` (`view`, `create`, `update`, `delete`, `manage`):

```python
"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "fts",
    "label": "File Tracking",
    "icon": "FolderSimple",
    "base_path": "/fts",
    "nav_section": "Workflow",
    "sort_order": 25,
    "status": "active",
}

PERMISSIONS = [
    ("fts.file.view", "View accessible files, inbox, outbox and tracking history"),
    ("fts.file.create", "Create new files and save drafts"),
    ("fts.file.update", "Forward, return, edit drafts, and add notes to files"),
    ("fts.file.delete", "Discard uncirculated draft files"),
    ("fts.file.manage", "Archive completed files and manage file configurations"),
    ("fts.audit.view", "View FTS system usage and security audit logs"),
]

SYSTEM_PERMISSIONS = [
    "fts.file.create",
    "fts.file.update",
]

SCOPE_PERMISSIONS = []

# Operational file access granted to all faculty and staff:
_EMPLOYEE_PERMISSIONS = [
    "fts.file.view",
    "fts.file.create",
    "fts.file.update",
    "fts.file.delete",
    "fts.file.manage",
]

_ADMIN_PERMISSIONS = [
    "fts.audit.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE_PERMISSIONS,
    "staff": _EMPLOYEE_PERMISSIONS,
    "admin": _ADMIN_PERMISSIONS,
    "system_admin": _ADMIN_PERMISSIONS,
}
```

---

## §6 — Step 3.5 (e) Endpoint List & UI Navigation

### API Endpoints (`/api/v1/fts/`)

| Method | Path | Required Permissions | Enforced Rule IDs | Returns / Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/fts/inbox/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.view')` | CFR-FTS-006, BR-001, BR-009 | List of circulating files where `current_holder_id == me` |
| `GET` | `/api/v1/fts/outbox/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.view')` | CFR-FTS-006, BR-001, BR-009 | List of files forwarded/sent by `me` |
| `GET` | `/api/v1/fts/drafts/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.view')` | CFR-FTS-004, BR-005 | List of uncirculated drafts created by `me` |
| `POST` | `/api/v1/fts/files/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.create')` | CFR-FTS-003, BR-001, BR-004 | Creates new file (draft or immediate circulate) |
| `GET` | `/api/v1/fts/files/<file_id>/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.view')` | CFR-FTS-006, BR-009 | Detail view + tracking history; returns 404 if not associated |
| `PATCH`| `/api/v1/fts/files/<file_id>/draft/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.update')` | CFR-FTS-004, BR-005 | Edits draft fields (only while status=draft & creator=me) |
| `DELETE`| `/api/v1/fts/files/<file_id>/draft/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.delete')` | CFR-FTS-004, BR-005 | Discards draft (deletes or sets status=discarded) |
| `POST` | `/api/v1/fts/files/<file_id>/forward/`| `HasModuleGrant('fts')`, `HasPermission('fts.file.update')` | CFR-FTS-005, BR-006, BR-007 | Forwards file to next receiver; updates holder |
| `POST` | `/api/v1/fts/files/<file_id>/return/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.update')` | CFR-FTS-005, BR-006, BR-007 | Returns file to previous sender in history |
| `POST` | `/api/v1/fts/files/<file_id>/archive/`| `HasModuleGrant('fts')`, `HasPermission('fts.file.manage')` | CFR-FTS-008, BR-012 | Sets status to archived (owner only) |
| `GET` | `/api/v1/fts/users/search/` | `HasModuleGrant('fts')`, `HasPermission('fts.file.view')` | CFR-FTS-005, BR-007 | Autocomplete for recipient employee lookup |

### Client Routes & Guarding

| Route | View Component | Guard / `RequirePermission` | Nav Item |
| :--- | :--- | :--- | :--- |
| `/fts` | Redirect to `/fts/inbox` | `fts.file.view` | — |
| `/fts/inbox` | `InboxPage` | `fts.file.view` | `Inbox` (Icon: Tray) |
| `/fts/outbox` | `OutboxPage` | `fts.file.view` | `Outbox` (Icon: PaperPlaneTilt) |
| `/fts/drafts` | `DraftsPage` | `fts.file.view` | `Drafts` (Icon: FileDotted) |
| `/fts/create` | `CreateFilePage` | `fts.file.create` | `Create File` (Icon: PlusCircle) |

*Note: Per architecture conventions, File Details and Movement History open in an inline Drawer/Modal component on list pages rather than on separate un-navigated URLs.*

### Hand-Maintained Sidebar Entry for `INTEGRATED_MODULES` (in `Fusion-client`):
```javascript
{
  id: "fts",
  label: "File Tracking",
  icon: "FolderSimple",
  to: "/fts",
  section: "Workflow",
}
```

---

## §7 — Step 3.6 (f) Contracts

`modules/fts/contracts.py` exposes plural, batch-oriented read/write functions for external Fusion modules:

```python
from typing import Sequence, Dict, Any, Optional

def get_file_summaries(file_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Return status, current holder, and movement count for the given file IDs."""
    ...

def create_module_files(file_requests: Sequence[Dict[str, Any]]) -> Sequence[Dict[str, Any]]:
    """Create and dispatch tracking files on behalf of external modules."""
    ...
```

**External Dependencies:**
- `fusion_auth` (IAM): Authentication & authorization token verification.
- `modules/directory`: Looking up employee names and designations.

---

## §8 — Step 3.7 (g) Scheduled Work

- `fts.tasks.cleanup_discarded_drafts`: Daily cleanup of orphaned file attachment objects from discarded drafts.
- Cadence: Daily at 03:00 UTC (`crontab(hour=3, minute=0)`).

---

## §9 — Step 3.8 (h) Open Questions / Known Gaps

1. **System Admin Operational Boundary**: Confirmed that `admin` / `system_admin` cannot view individual operational files unless explicitly made a recipient. System Admin only accesses audit logs.
2. **Designation Coverage**: All faculty and staff roles are granted operational permissions by default, fulfilling BR-FTS-001.

---

### Approval Request
Student 1 submits this blueprint for **Student 2's formal written review and approval**. Application code implementation (Phase 3) will proceed immediately upon sign-off.
