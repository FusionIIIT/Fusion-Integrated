# File Tracking System (FTS-007) — Implementation Blueprint

**Module Name:** File Tracking System (FTS)  
**Module Code:** `filetracking`  
**Documentation Folder:** `docs/09-filetracking/`  
**Specification Source:** `/home/utkarsh_gupta/Documents/Fusion/7`  
**Specification ID Prefix:** `FTS-` (`CFR-FTS-`, `AFR-FTS-`, `BR-FTS-`, `FTS-UC-`, `FTS-WF-`, `BW-FTS-`, `CW-FTS-`)  
**Environment:** `module-only`  
**Reference Domain Module:** `modules/placement/`  
**Author / Builder (Student 1):** Utkarsh Gupta (24BCS256)  
**Reviewer / Tester (Student 2):** Sushanth (24BCS193)  

---

## 1. Phase 1 — Architectural Questions & Decisions (§2)

### Step 2.1 — Is this one bounded context?
**Yes.** The File Tracking System (FTS) is a single, coherent bounded context responsible for the creation, drafting, movement (forwarding/return), commenting, attachment management, tracking history, and lifecycle archival of institutional administrative and academic files across Institute Employees.  
Consuming modules (such as Leave, Purchase, or Academic approvals) may invoke FTS APIs to establish and track file-based approval chains, but all domain-specific workflows, forms, and approval semantics remain strictly within the consuming modules (`BR-FTS-014`).

### Step 2.2 — What does it need from other modules?
FTS strictly adheres to ADR-0013 (no cross-module database foreign keys) and accesses cross-cutting capabilities exclusively through agreed contracts and HTTP IAM services:
1. **IAM & Directory (`modules/directory` / `fusion_auth`):**
   - User resolution: Plural getters `get_users(user_ids: Sequence[int])` and employee directory searches `search_users(query: str, designation: str)` to validate that file recipients are active Institute Employees (`BR-FTS-001`, `BR-FTS-007`).
   - Active Role Context: Reading the caller's active designation from the request session (`request.session["active_role"]`) and token payload (`BR-FTS-002`, `BR-FTS-008`).
2. **Notifications (`core.outbox` / Fusion Notification Service):**
   - Outbox pattern to trigger file movement and lifecycle event notifications (received, forwarded, returned, archived, access context change) without cross-module writes (`BR-FTS-013`).

### Step 2.3 — Identity
All user references within FTS persistence models are plain integers (`user_id: int`) inheriting from `core.db.mixins.TimeStampedModel`. No foreign keys to `auth_user` or legacy `Employee` models exist. Acting designation titles (`acting_designation: str`) are stored as immutable audit metadata at the time of each action (`BR-FTS-002`, `BR-FTS-011`).

### Step 2.4 — Roles and Designations
From the actor inventory across BRs, UCs, and Workflows:
- **Operational File Users (`BR-FTS-001`, `CFR-FTS-002`):**
  - Institute Employees: `faculty`, `staff`.
  - Administrative and Academic designations: `Dean Academic`, `acadadmin`, `placement_officer`, `placement_coordinator`, `placement_chairman`.
  - Operational users hold permissions to create files, save drafts, forward files, return received files, add comments/attachments, view tracking trails of associated files, and archive files they own.
- **Governance Actor (`BR-FTS-001`, `FTS-UC-009`, `CFR-FTS-002`):**
  - `system_admin`, `admin`.
  - System Administrators perform governance oversight, access context inspection, and view system audit records. System Admin is strictly prohibited from participating in operational file movements or reading private operational file contents (`BR-FTS-001`, `BR-FTS-010`).
- **Excluded Actors:**
  - `student`: Students are strictly forbidden from operational file processing in FTS (`BR-FTS-001`).

### Step 2.5 — Scoping & Data Visibility
Read operations are strictly filtered by file association Choke-Points in `selectors/scoping.py` (`BR-FTS-009`):
- A user operating under an assigned employee role may only view and open a file if they are:
  1. The original creator/owner (`created_by_user_id == user_id`), OR
  2. The current holder (`current_holder_user_id == user_id`), OR
  3. A past participant in the file's movement history (`sender_user_id == user_id` or `receiver_user_id == user_id` in `FileMovement`).
- Accessing a file without association yields **HTTP 404 Not Found**, never HTTP 403 Forbidden, to prevent probing or confirming the existence of institutional files.

### Step 2.6 — Time & Scheduled Jobs
FTS files do not expire automatically by time. Periodic Celery beat tasks:
- `filetracking.reconcile_outbox_notifications`: Runs every 5 minutes to sweep and deliver pending outbox events.
- `filetracking.audit_integrity_check`: Runs daily at 02:00 UTC to verify hash integrity and chronological monotonicity of audit records.

### Step 2.7 — Money, Quota & Balances
FTS maintains no monetary balances. File movement and audit trails are modeled as **strictly append-only immutable event ledgers** (`BR-FTS-003`, `BR-FTS-008`, `BR-FTS-011`). Once circulated, movement records, comments, and attachments cannot be modified or deleted.

### Step 2.8 — Policy & Configuration
Institute file processing policies (maximum attachment size: 10MB; permitted MIME types: `application/pdf`, `image/png`, `image/jpeg`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`) are configured via Django settings and validated in domain services.

---

## 2. Phase 2 — Technical Blueprint (§3)

### Step 3.1 (a) — Traceability Matrix

| Specification ID | Requirement / Rule / Use Case Summary | Layer | Enforcement Point (Planned) | Notes / Cross-Reference |
| :--- | :--- | :--- | :--- | :--- |
| **BR-FTS-001** | Only Institute Employees may perform operational file processing; System Admin is governance-only. | Domain / API | `domain/rules.py::check_operational_employee_role`, `api/permissions.py` | CFR-FTS-002, AFR-FTS-001..004 |
| **BR-FTS-002** | Role switching preserves file ownership and historical audit identity. | Domain / Service | `services/files.py`, `models/file.py` (`created_by_user_id` immutable) | CFR-FTS-009, AFR-FTS-042..047 |
| **BR-FTS-003** | Persistent composite file; circulated contents (comments, attachments) are immutable and append-only. | Domain / Persistence | `domain/entities.py`, `models/file.py`, `models/movement.py` | CFR-FTS-001, AFR-FTS-001..004 |
| **BR-FTS-004** | Mandatory initial user comment on file creation. | Domain / API | `domain/rules.py::validate_initial_comment`, `api/serializers.py` | CFR-FTS-003, AFR-FTS-005..010 |
| **BR-FTS-005** | Draft edit/discard permitted only before circulation; circulated files cannot be discarded. | Domain / State Machine | `domain/state_machine.py`, `services/files.py::discard_draft` | CFR-FTS-004, AFR-FTS-011..013 |
| **BR-FTS-006** | Mandatory movement comment for every forward and return action. | Domain / Service | `domain/rules.py::validate_movement_comment`, `services/files.py` | CFR-FTS-005, AFR-FTS-014..019 |
| **BR-FTS-007** | Forward recipient must be a valid active Employee (not self); Return must be to immediate previous sender. | Domain / Service | `domain/rules.py::validate_forward_recipient`, `validate_return_recipient` | CFR-FTS-005, AFR-FTS-014..019 |
| **BR-FTS-008** | Chronological movement recording with sender, receiver, timestamp, comments, attachments. | Service / Persistence | `services/files.py`, `models/movement.py` (auto-now timestamps) | CFR-FTS-005, CFR-FTS-007, AFR-FTS-029..034 |
| **BR-FTS-009** | Associated file access: only creator, current holder, or past movement participants can access a file. | Selectors / Scoping | `selectors/scoping.py::get_associated_file_or_404` | CFR-FTS-006, AFR-FTS-020..028 |
| **BR-FTS-010** | RBAC and sensitive action controls (archive, forward, return, discard). | Domain / API | `api/permissions.py`, `domain/rules.py` | CFR-FTS-009, AFR-FTS-042..047 |
| **BR-FTS-011** | Immutable audit logging and chronological version history for all auditable events. | Service / Audit | `services/audit.py`, `models/audit.py` (append-only ledger) | CFR-FTS-010, AFR-FTS-048..053 |
| **BR-FTS-012** | Only file owner may archive a completed circulated file; archived files are permanently read-only. | Domain / State Machine | `domain/state_machine.py`, `services/files.py::archive_file` | CFR-FTS-008, AFR-FTS-035..041 |
| **BR-FTS-013** | Trigger notifications for received, forwarded, returned, archived, and role-change events. | Service / Outbox | `services/notifications.py`, `core.outbox` | CFR-FTS-011, AFR-FTS-054..060 |
| **BR-FTS-014** | FTS integration boundary: expose workflow-tracking APIs; consuming modules own business logic. | Contracts / API | `contracts.py`, `api/views.py::IntegrationViewSet` | CFR-FTS-012, AFR-FTS-061..072 |
| **BR-FTS-015** | System Actor modeling convention (reclassified as specification modeling convention). | Architecture | System boundaries documented; no artificial system actor logic. | Spec reconciliation |
| **FTS-UC-001** | Create New File (draft or initial circulation). | Service / API | `services/files.py::create_file`, `api/views.py::FileViewSet.create` | BW-FTS-05, BW-FTS-06, CW-FTS-02 |
| **FTS-UC-002** | Edit or Discard Draft File before submission. | Service / API | `services/files.py::update_draft`, `discard_draft` | BW-FTS-07, BW-FTS-08, CW-FTS-02 |
| **FTS-UC-003** | Send / Forward File to Employee (initial send or onward forward). | Service / API | `services/files.py::forward_file`, `api/views.py::FileViewSet.forward` | BW-FTS-01, BW-FTS-02, CW-FTS-01 |
| **FTS-UC-004** | Return Received File to immediate previous sender. | Service / API | `services/files.py::return_file`, `api/views.py::FileViewSet.return_file` | BW-FTS-03, CW-FTS-01 |
| **FTS-UC-005** | View Inbox, Outbox, Drafts, Archived, and Open File details. | Selectors / API | `selectors/files.py`, `api/views.py::FileViewSet.{inbox,outbox,drafts,archived}` | AFR-FTS-020..028 |
| **FTS-UC-006** | View File Tracking History and chronological movement trail. | Selectors / API | `selectors/files.py::get_file_history`, `api/views.py::FileViewSet.history` | AFR-FTS-029..034 |
| **FTS-UC-007** | Archive Completed Circulated File (owner only). | Service / API | `services/files.py::archive_file`, `api/views.py::FileViewSet.archive` | BW-FTS-04, CW-FTS-01 |
| **FTS-UC-008** | Select Assigned Role Context for FTS operations. | IAM / Middleware | Request session `active_role` resolution, `api/permissions.py` | AFR-FTS-042..047 |
| **FTS-UC-009** | Administer FTS User Access Context & Governance Oversight. | Selectors / API | `api/views.py::GovernanceViewSet`, `selectors/audit.py` | AFR-FTS-048..053 |
| **FTS-UC-010** | Use FTS Workflow-Support APIs for inter-module integration. | Contracts / API | `contracts.py`, `api/views.py::IntegrationViewSet` | AFR-FTS-061..072 |
| **FTS-UC-011** | Receive FTS Notifications (Retired as standalone UC; cross-cutting effect). | Outbox Service | `services/notifications.py` | BR-FTS-013, AFR-FTS-054..060 |
| **CFR-FTS-001..012** | Core Functional Requirements (all 12 CFRs mapped). | Core Domain | Comprehensive service and domain models | Covers all 72 AFRs |
| **AFR-FTS-001..072** | Additional Functional Requirements (all 72 AFRs mapped). | Full Module | Validated across domain, services, selectors, and API suites | 100% spec coverage |

---

### Step 3.2 (b) — Domain Model & Database Invariants

#### 1. Entity: `TrackedFile` (`db_table = "filetracking_file"`)
- `id`: Auto-incrementing primary key.
- `file_number`: String (unique institutional identifier format `FTS/<YEAR>/<SEQ>`, e.g. `FTS/2026/00001`).
- `subject`: CharField(max_length=255) — non-empty file subject.
- `description`: TextField — mandatory initial file description/content.
- `status`: CharField(max_length=32, choices=FileStatus.choices, default=FileStatus.DRAFT) — `draft`, `circulating`, `archived`.
- `created_by_user_id`: IntegerField (immutable owner ID).
- `creator_designation`: CharField(max_length=128) — designation of creator when created.
- `current_holder_user_id`: IntegerField (null when draft or archived, set to recipient when circulating).
- `current_holder_designation`: CharField(max_length=128, blank=True).
- `is_archived`: BooleanField(default=False).
- `archived_at`: DateTimeField(null=True, blank=True).
- `created_at`, `updated_at`: DateTimeFields (`TimeStampedModel`).
- **Database Constraints:**
  - `UniqueConstraint(fields=['file_number'], name='uniq_fts_file_number')`
  - `CheckConstraint(check=Q(status__in=['draft', 'circulating', 'archived']), name='check_fts_file_status')`
  - `CheckConstraint(check=Q(status='draft', current_holder_user_id__isnull=True) | Q(status='circulating', current_holder_user_id__isnull=False) | Q(status='archived', is_archived=True), name='check_fts_holder_consistency')`

#### 2. Entity: `FileMovement` (`db_table = "filetracking_movement"`)
- `id`: Auto-incrementing primary key.
- `file`: ForeignKey(`TrackedFile`, on_delete=CASCADE, related_name='movements').
- `sequence_number`: PositiveIntegerField (1, 2, 3... monotonically increasing per file).
- `action`: CharField(max_length=32) — `created`, `forwarded`, `returned`, `archived`.
- `sender_user_id`: IntegerField.
- `sender_designation`: CharField(max_length=128).
- `receiver_user_id`: IntegerField.
- `receiver_designation`: CharField(max_length=128).
- `comment`: TextField (mandatory movement remark per `BR-FTS-006`).
- `created_at`: DateTimeField(auto_now_add=True).
- **Database Constraints:**
  - `UniqueConstraint(fields=['file', 'sequence_number'], name='uniq_fts_movement_seq')`
  - `CheckConstraint(check=~Q(sender_user_id=F('receiver_user_id')), name='check_fts_no_self_movement')`

#### 3. Entity: `FileAttachment` (`db_table = "filetracking_attachment"`)
- `id`: Auto-incrementing primary key.
- `file`: ForeignKey(`TrackedFile`, on_delete=CASCADE, related_name='attachments').
- `movement`: ForeignKey(`FileMovement`, on_delete=CASCADE, null=True, blank=True, related_name='attachments').
- `uploaded_by_user_id`: IntegerField.
- `uploader_designation`: CharField(max_length=128).
- `file_name`: CharField(max_length=255).
- `file_path`: CharField(max_length=512) — storage path.
- `file_size`: PositiveIntegerField.
- `mime_type`: CharField(max_length=128).
- `created_at`: DateTimeField(auto_now_add=True).
- **Database Constraints:**
  - `CheckConstraint(check=Q(file_size__lte=10485760), name='check_fts_attachment_max_10mb')`

#### 4. Entity: `FileAuditLog` (`db_table = "filetracking_audit"`)
- `id`: Auto-incrementing primary key.
- `file_id`: IntegerField(null=True, blank=True, db_index=True).
- `action`: CharField(max_length=64) — `file.create`, `file.update_draft`, `file.discard_draft`, `file.forward`, `file.return`, `file.archive`, `governance.access_change`, `api.integration_call`.
- `actor_user_id`: IntegerField.
- `actor_designation`: CharField(max_length=128).
- `payload`: JSONField(default=dict) — recorded state diff and snapshot.
- `ip_address`: GenericIPAddressField(null=True, blank=True).
- `created_at`: DateTimeField(auto_now_add=True, db_index=True).

---

### Step 3.3 (c) — Declarative State Machine

The FTS lifecycle is governed by a formal transition table in `domain/state_machine.py`. Illegal transitions are inexpressible.

```python
from dataclasses import dataclass
from typing import Dict, Tuple, Set

class FileStatus:
    DRAFT = "draft"
    CIRCULATING = "circulating"
    ARCHIVED = "archived"

class FileEvent:
    CREATE_DRAFT = "create_draft"
    SUBMIT_INITIAL = "submit_initial"
    UPDATE_DRAFT = "update_draft"
    DISCARD_DRAFT = "discard_draft"
    FORWARD = "forward"
    RETURN = "return"
    ARCHIVE = "archive"

# Key: (current_state, event) -> (next_state, allowed_actor_roles)
TRANSITIONS: Dict[Tuple[str, str], Tuple[str, Set[str]]] = {
    # Pre-circulation Draft Flow (CW-FTS-02 / BW-FTS-05..08)
    (FileStatus.DRAFT, FileEvent.UPDATE_DRAFT): (FileStatus.DRAFT, {"OWNER"}),
    (FileStatus.DRAFT, FileEvent.DISCARD_DRAFT): (None, {"OWNER"}), # None indicates deletion of draft
    (FileStatus.DRAFT, FileEvent.SUBMIT_INITIAL): (FileStatus.CIRCULATING, {"OWNER"}),

    # Active Circulation Flow (CW-FTS-01 / BW-FTS-01..03)
    (FileStatus.CIRCULATING, FileEvent.FORWARD): (FileStatus.CIRCULATING, {"CURRENT_HOLDER"}),
    (FileStatus.CIRCULATING, FileEvent.RETURN): (FileStatus.CIRCULATING, {"CURRENT_HOLDER"}),

    # Lifecycle Closing Flow (CW-FTS-01 / BW-FTS-04)
    (FileStatus.CIRCULATING, FileEvent.ARCHIVE): (FileStatus.ARCHIVED, {"OWNER"}),
}
```

**Guard Rules:**
1. `DISCARD_DRAFT`: Fails if `status != FileStatus.DRAFT`. Circulated files can never be discarded (`BR-FTS-005`).
2. `FORWARD`: Current holder cannot forward to themselves (`recipient_id != current_holder_id`). Recipient must be an active Institute Employee (`BR-FTS-007`). Mandatory comment required (`BR-FTS-006`).
3. `RETURN`: Target recipient must strictly be the `sender_user_id` of the immediate previous movement record (`BR-FTS-007`). Mandatory comment required (`BR-FTS-006`).
4. `ARCHIVE`: Caller must be `created_by_user_id` (the File Owner). Any attempted forward, return, or edit on an archived file is rejected (`BR-FTS-012`).

---

### Step 3.4 (d) — RBAC and Permission Registry (`registry.py`)

Exact content for `modules/filetracking/registry.py`:

```python
"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "filetracking",
    "label": "File Tracking",
    "icon": "Folder",
    "base_path": "/filetracking",
    "nav_section": "Office",
    "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "filetracking.inbox",
        "label": "Inbox",
        "icon": "Tray",
        "to": "/filetracking/inbox",
        "required_permission": "filetracking.file.view",
        "sort_order": 10,
    },
    {
        "code": "filetracking.outbox",
        "label": "Outbox",
        "icon": "PaperPlaneTilt",
        "to": "/filetracking/outbox",
        "required_permission": "filetracking.file.view",
        "sort_order": 20,
    },
    {
        "code": "filetracking.create",
        "label": "Create File",
        "icon": "FilePlus",
        "to": "/filetracking/create",
        "required_permission": "filetracking.file.create",
        "sort_order": 30,
    },
    {
        "code": "filetracking.archive",
        "label": "Archive",
        "icon": "Archive",
        "to": "/filetracking/archive",
        "required_permission": "filetracking.file.view",
        "sort_order": 40,
    },
    {
        "code": "filetracking.governance",
        "label": "Audit Logs",
        "icon": "ShieldCheck",
        "to": "/filetracking/governance",
        "required_permission": "filetracking.governance.view",
        "sort_order": 50,
    },
]

PERMISSIONS = [
    ("filetracking.file.create", "Create and draft institutional files"),
    ("filetracking.file.view", "View associated files and tracking history"),
    ("filetracking.file.forward", "Send or forward files to employees"),
    ("filetracking.file.return", "Return received files to previous sender"),
    ("filetracking.file.archive", "Archive completed circulated files"),
    ("filetracking.governance.view", "View FTS governance usage and audit logs"),
    ("filetracking.governance.manage", "Administer FTS access and role context"),
    ("filetracking.api.integrate", "Invoke FTS workflow-support APIs"),
]

SYSTEM_PERMISSIONS = [
    "filetracking.api.integrate",
]

SCOPE_PERMISSIONS = []

_OPERATIONAL_EMPLOYEE = [
    "filetracking.file.create",
    "filetracking.file.view",
    "filetracking.file.forward",
    "filetracking.file.return",
    "filetracking.file.archive",
]

_GOVERNANCE_ADMIN = [
    "filetracking.governance.view",
    "filetracking.governance.manage",
]

ROLE_GRANTS = {
    "faculty": _OPERATIONAL_EMPLOYEE,
    "staff": _OPERATIONAL_EMPLOYEE,
    "Dean Academic": _OPERATIONAL_EMPLOYEE,
    "acadadmin": _OPERATIONAL_EMPLOYEE,
    "placement_officer": _OPERATIONAL_EMPLOYEE,
    "placement_coordinator": _OPERATIONAL_EMPLOYEE,
    "placement_chairman": _OPERATIONAL_EMPLOYEE,
    "admin": _GOVERNANCE_ADMIN,
    "system_admin": _GOVERNANCE_ADMIN,
}
```

---

### Step 3.5 (e) — REST API Endpoints & `Fusion-client` Navigation

Base URL prefix: `/api/v1/filetracking/`

| HTTP Method | Path | Auth & Permission Gate | Description / Return | Enforced Rule IDs |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/filetracking/files/inbox/` | IsAuthenticated, `filetracking.file.view` | Paginated list of files where current user is `current_holder` (`circulating`). | BR-FTS-001, BR-FTS-009, FTS-UC-005 |
| `GET` | `/api/v1/filetracking/files/outbox/` | IsAuthenticated, `filetracking.file.view` | Paginated list of files where current user previously sent/forwarded or created. | BR-FTS-001, BR-FTS-009, FTS-UC-005 |
| `GET` | `/api/v1/filetracking/files/drafts/` | IsAuthenticated, `filetracking.file.create` | List of uncirculated draft files created by current user. | BR-FTS-001, BR-FTS-005, FTS-UC-005 |
| `GET` | `/api/v1/filetracking/files/archived/` | IsAuthenticated, `filetracking.file.view` | List of completed archived files associated with current user. | BR-FTS-001, BR-FTS-009, BR-FTS-012 |
| `POST` | `/api/v1/filetracking/files/` | IsAuthenticated, `filetracking.file.create` | Create new file (draft or initial circulation). | BR-FTS-001, BR-FTS-004, FTS-UC-001 |
| `GET` | `/api/v1/filetracking/files/{id}/` | IsAuthenticated, `filetracking.file.view` | Retrieve file details with association check (404 if unassociated). | BR-FTS-001, BR-FTS-009, FTS-UC-005 |
| `PUT`/`PATCH` | `/api/v1/filetracking/files/{id}/draft/` | IsAuthenticated, `filetracking.file.create` | Update uncirculated draft subject/content/attachments (owner only). | BR-FTS-005, FTS-UC-002 |
| `DELETE` | `/api/v1/filetracking/files/{id}/draft/` | IsAuthenticated, `filetracking.file.create` | Discard uncirculated draft (owner only). Returns 400 if circulated. | BR-FTS-003, BR-FTS-005, FTS-UC-002 |
| `POST` | `/api/v1/filetracking/files/{id}/forward/` | IsAuthenticated, `filetracking.file.forward` | Forward file to recipient employee with mandatory comment. | BR-FTS-006, BR-FTS-007, FTS-UC-003 |
| `POST` | `/api/v1/filetracking/files/{id}/return/` | IsAuthenticated, `filetracking.file.return` | Return file to immediate previous sender with mandatory comment. | BR-FTS-006, BR-FTS-007, FTS-UC-004 |
| `POST` | `/api/v1/filetracking/files/{id}/archive/` | IsAuthenticated, `filetracking.file.archive` | Archive completed circulated file (owner only). | BR-FTS-008, BR-FTS-012, FTS-UC-007 |
| `GET` | `/api/v1/filetracking/files/{id}/history/` | IsAuthenticated, `filetracking.file.view` | Full chronological movement trail with comments, attachments, timestamps. | BR-FTS-008, BR-FTS-011, FTS-UC-006 |
| `POST` | `/api/v1/filetracking/integration/initiate/` | SystemToken, `filetracking.api.integrate` | Consuming module initiates workflow-tracked file. | BR-FTS-014, FTS-UC-010, CFR-FTS-012 |
| `GET` | `/api/v1/filetracking/governance/audit/` | IsAuthenticated, `filetracking.governance.view` | System Admin views governance audit logs. | BR-FTS-001, BR-FTS-010, FTS-UC-009 |

#### Shell Navigation Specification for `Fusion-client` (`INTEGRATED_MODULES`)
```javascript
{
  id: "filetracking",
  label: "File Tracking",
  icon: "Folder",
  to: "/filetracking/inbox",
  section: "Office"
}
```

---

### Step 3.6 (f) — Inter-Module Contracts (`contracts.py`)

`modules/filetracking/contracts.py` exposes plural, bulk-safe query and command interfaces for other Fusion modules:

```python
from typing import Sequence, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class FileStatusDTO:
    file_id: int
    file_number: str
    subject: str
    status: str
    current_holder_user_id: Optional[int]
    is_archived: bool

def get_file_statuses(file_ids: Sequence[int]) -> List[FileStatusDTO]:
    """Plural getter: bulk-fetches statuses for consuming module requests."""
    ...

def get_files_for_holders(holder_user_ids: Sequence[int]) -> List[FileStatusDTO]:
    """Plural getter: bulk-fetches active files held by given users."""
    ...

def initiate_module_tracking_chain(
    initiator_user_id: int,
    initiator_designation: str,
    subject: str,
    initial_comment: str,
    recipient_user_id: int,
    recipient_designation: str,
    external_reference: str,
) -> FileStatusDTO:
    """Inter-module command: creates and circulates an institutional file for external workflow."""
    ...
```

---

### Step 3.7 (g) — Scheduled Work (`schedule.py`)

Celery beat schedule registered in `modules/filetracking/schedule.py`:

```python
from celery.schedules import crontab

SCHEDULE = {
    "filetracking-reconcile-outbox": {
        "task": "modules.filetracking.tasks.reconcile_outbox_notifications",
        "schedule": 300.0, # Every 5 minutes
    },
    "filetracking-audit-integrity-check": {
        "task": "modules.filetracking.tasks.verify_audit_integrity",
        "schedule": crontab(hour=2, minute=0), # Daily at 02:00 UTC
    },
}
```
**Failure Modes:**
- If `reconcile_outbox_notifications` stops running: File movement notifications may be delayed. The outbox table persists events safely until the task resumes.
- If `verify_audit_integrity` stops running: Routine daily tamper-detection is skipped; runtime file operations are unaffected.

---

### Step 3.8 (h) — Open Questions & Verifications for Student 2 Approval

1. **Role Designations:** Confirmed that operational file access is assigned to `faculty`, `staff`, `Dean Academic`, `acadadmin`, and placement designations, while `admin` and `system_admin` are restricted to governance. Confirmed that students are excluded from FTS operational file processing.
2. **Draft Discard vs Circulation:** Confirmed that discarding a file is only permitted while in `draft` state. Once submitted into circulation (`circulating`), draft deletion is permanently blocked, and completed files must be closed via owner `archive`.
3. **Return Movement:** Confirmed that a file return action can only be addressed to the immediate previous sender of the file in the movement chain.
4. **Git Branching:** Awaiting Student 1 / Student 2 execution of `git fetch upstream && git checkout -b module/filetracking upstream/main` as required by the Assignment 9 guide.
