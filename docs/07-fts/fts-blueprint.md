# File Tracking System (FTS) — Architecture Blueprint

| Field | Value |
| :--- | :--- |
| **Module** | File Tracking System (`modules/fts`) |
| **Module Code** | `fts` |
| **Author** | Student 1 (`24BCS007`, cosypix) |
| **Approver** | Student 2 (`24BCS067`, Daggula Amulya) |
| **Status** | APPROVED (2026-11-21) |
| **Specification Baseline** | v1.3 FINAL (Frozen Problem Statement v1.2, CFR/AFR Registry v1.3, UC v1.3, BR v1.3, WF v1.3) |

---

## 1. Executive Summary & Bounded Context

The File Tracking System (FTS) is an administrative and academic collaboration module for Fusion ERP at IIITDM Jabalpur. It provides end-to-end digital lifecycle tracking for institute files exchanged among Institute Employees (Faculty and Staff). 

FTS is a single bounded context responsible for:
1. File creation, draft maintenance, and pre-circulation discarding.
2. Inter-employee file circulation through forward and return movements with mandatory movement comments and optional attachments.
3. Custody tracking through user-scoped Inboxes and Outboxes.
4. Complete, append-only chronological movement and comment history.
5. Lifecycle-terminating file archival reserved strictly for file owners upon completion of business objectives.
6. Clean plural contract interfaces for inter-module integration by consuming Fusion modules.

---

## Step 3.1 (a) — Traceability Table

All 118 live specification identifiers are mapped to their design layer and code enforcement point. Retired identifiers (`FTS-UC-011`, `BR-FTS-015`, `FTS-WF-004..008`) are excluded.

### 1. Consolidated Requirements (CFRs)

| CFR ID | Title | Layer | Enforcement Point | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CFR-FTS-001` | Persistent Collaborative Record Lifecycle | `models` | `modules/fts/models.py:14` | File as persistent composite object |
| `CFR-FTS-002` | Employee Operational Access vs Admin Governance | `registry` | `modules/fts/registry.py:53` | RBAC separation of operational file processing |
| `CFR-FTS-003` | File Creation with Initial Comment and Attachments | `services` | `modules/fts/services/drafts.py:22` | Creation validation and initial draft persistence |
| `CFR-FTS-004` | Pre-Circulation Draft Management and Transition | `services` | `modules/fts/services/drafts.py:99` | Draft edit/discard and circulation transition |
| `CFR-FTS-005` | File Forwarding and Return Movement Handling | `services` | `modules/fts/services/movements.py:22` | Forwarding/return with comments and routing updates |
| `CFR-FTS-006` | Inbox and Outbox Circulation Management | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` | Custody queries for received and sent files |
| `CFR-FTS-007` | Complete Chronological Movement Tracking History | `selectors` | `modules/fts/selectors/movements.py:9` | Chronological audit trail of all movements |
| `CFR-FTS-008` | Owner-Controlled Archival of Completed Files | `services` | `modules/fts/services/archival.py:17` | Archival transitions file to permanent terminal state |
| `CFR-FTS-009` | Role-Based and File-Association Authorization | `domain` | `modules/fts/domain/workflow.py:89` | Authorization checks preserving ownership across role switches |
| `CFR-FTS-010` | Audit Records and Chronological Versioning | `models` | `modules/fts/models.py:66` | Movement and comment logs recording timestamps and actors |
| `CFR-FTS-011` | File and Role Notification Event Triggers | `services` | `modules/fts/services/movements.py:94` | Notification trigger points on movement events |
| `CFR-FTS-012` | Inter-Module Workflow Support APIs | `contracts` | `modules/fts/contracts.py:29` | Plural contract getters for external modules |

### 2. Atomic Requirements (AFRs)

| AFR ID | Requirement Statement | Layer | Enforcement Point |
| :--- | :--- | :--- | :--- |
| `AFR-FTS-001` | Persistent composite file object | `models` | `modules/fts/models.py:14` |
| `AFR-FTS-002` | Preserve circulated file contents | `models` | `modules/fts/models.py:14` |
| `AFR-FTS-003` | Owner-controlled file archival | `services` | `modules/fts/services/archival.py:17` |
| `AFR-FTS-004` | Lifecycle traceability of files | `selectors` | `modules/fts/selectors/movements.py:9` |
| `AFR-FTS-005` | Institute employee operational users | `registry` | `modules/fts/registry.py:72` |
| `AFR-FTS-006` | System admin governance context | `registry` | `modules/fts/registry.py:53` |
| `AFR-FTS-007` | System admin usage monitoring | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` |
| `AFR-FTS-008` | System admin audit oversight | `selectors` | `modules/fts/selectors/movements.py:9` |
| `AFR-FTS-009` | Admin excluded from routine file processing | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-010` | Role context selection for employees | `api` | `modules/fts/api/views.py:38` |
| `AFR-FTS-011` | Employee file creation under assigned role | `services` | `modules/fts/services/drafts.py:22` |
| `AFR-FTS-012` | Mandatory initial comment on creation | `domain` | `modules/fts/domain/workflow.py:41` |
| `AFR-FTS-013` | Optional attachments on file creation | `models` | `modules/fts/models.py:121` |
| `AFR-FTS-014` | Save newly created file as draft | `services` | `modules/fts/services/drafts.py:22` |
| `AFR-FTS-015` | Edit saved draft before submission | `services` | `modules/fts/services/drafts.py:99` |
| `AFR-FTS-016` | Discard draft before submission | `services` | `modules/fts/services/drafts.py:148` |
| `AFR-FTS-017` | Prevent deletion of circulated files | `domain` | `modules/fts/domain/workflow.py:180` |
| `AFR-FTS-018` | Transition draft to circulated state | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-019` | Preserve comments and attachments after circulation | `models` | `modules/fts/models.py:96` |
| `AFR-FTS-020` | Send file to another institute employee | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-021` | Send file regardless of receiver role | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-022` | Mandatory movement comment for forward and return | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-023` | Optional attachments during file movement | `models` | `modules/fts/models.py:121` |
| `AFR-FTS-024` | Recipient forward received file | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-025` | Recipient return received file to sender | `domain` | `modules/fts/domain/workflow.py:120` |
| `AFR-FTS-026` | Record forward action chronologically | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-027` | Record return action chronologically | `services` | `modules/fts/services/movements.py:94` |
| `AFR-FTS-028` | Update current holder after movement | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-029` | Show received files in Inbox | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` |
| `AFR-FTS-030` | Show sent files in Outbox | `selectors` | `modules/fts/selectors/inbox_outbox.py:43` |
| `AFR-FTS-031` | View and open files from Inbox | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` |
| `AFR-FTS-032` | View and open files from Outbox | `selectors` | `modules/fts/selectors/inbox_outbox.py:43` |
| `AFR-FTS-033` | Act on actionable files from Inbox/Outbox | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-034` | Keep files accessible until owner archives | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` |
| `AFR-FTS-035` | Complete movement history from creation onward | `selectors` | `modules/fts/selectors/movements.py:9` |
| `AFR-FTS-036` | Record sender details for movement event | `models` | `modules/fts/models.py:66` |
| `AFR-FTS-037` | Record receiver details for movement event | `models` | `modules/fts/models.py:66` |
| `AFR-FTS-038` | Record timestamps for movement event | `models` | `modules/fts/models.py:66` |
| `AFR-FTS-039` | Record comments at each movement event | `models` | `modules/fts/models.py:96` |
| `AFR-FTS-040` | Record attachments at each movement event | `models` | `modules/fts/models.py:121` |
| `AFR-FTS-041` | Allow associated users to view tracking history | `selectors` | `modules/fts/selectors/movements.py:9` |
| `AFR-FTS-042` | Allow file owner to archive file | `services` | `modules/fts/services/archival.py:17` |
| `AFR-FTS-043` | Prevent non-owners from archiving file | `domain` | `modules/fts/domain/workflow.py:154` |
| `AFR-FTS-044` | Archival completes collaborative workflow | `services` | `modules/fts/services/archival.py:17` |
| `AFR-FTS-045` | Permanently store readable archived files | `models` | `modules/fts/models.py:14` |
| `AFR-FTS-046` | Prevent modification of archived files | `domain` | `modules/fts/domain/workflow.py:180` |
| `AFR-FTS-047` | Prevent forwarding of archived files | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-048` | Role-based access control for file operations | `registry` | `modules/fts/registry.py:53` |
| `AFR-FTS-049` | Access only authorized files | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` |
| `AFR-FTS-050` | Act only on authorized files | `domain` | `modules/fts/domain/workflow.py:89` |
| `AFR-FTS-051` | Preserve file ownership across role switching | `models` | `modules/fts/models.py:14` |
| `AFR-FTS-052` | Preserve audit history across role switching | `models` | `modules/fts/models.py:66` |
| `AFR-FTS-053` | Restrict sensitive actions by assigned roles | `registry` | `modules/fts/registry.py:53` |
| `AFR-FTS-054` | Audit log for file creation | `services` | `modules/fts/services/drafts.py:22` |
| `AFR-FTS-055` | Audit log for comments added | `models` | `modules/fts/models.py:96` |
| `AFR-FTS-056` | Audit log for attachments added | `models` | `modules/fts/models.py:121` |
| `AFR-FTS-057` | Audit log for forwarding actions | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-058` | Audit log for return actions | `services` | `modules/fts/services/movements.py:94` |
| `AFR-FTS-059` | Audit log for archival actions | `services` | `modules/fts/services/archival.py:17` |
| `AFR-FTS-060` | Implicit versioning via chronological updates | `selectors` | `modules/fts/selectors/movements.py:9` |
| `AFR-FTS-061` | Generate notification when file is received | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-062` | Generate notification when file is forwarded | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-063` | Generate notification when file is returned | `services` | `modules/fts/services/movements.py:94` |
| `AFR-FTS-064` | Generate notification when file is archived | `services` | `modules/fts/services/archival.py:17` |
| `AFR-FTS-065` | Generate notification on role assignment/reassignment | `registry` | `modules/fts/registry.py:72` |
| `AFR-FTS-066` | Deliver notifications via integrated mechanism | `services` | `modules/fts/services/movements.py:22` |
| `AFR-FTS-067` | APIs for module-specific workflows | `contracts` | `modules/fts/contracts.py:29` |
| `AFR-FTS-068` | APIs for approval chains | `contracts` | `modules/fts/contracts.py:54` |
| `AFR-FTS-069` | APIs for file-based request tracking | `contracts` | `modules/fts/contracts.py:29` |
| `AFR-FTS-070` | Apply RBAC to inter-module integrations | `contracts` | `modules/fts/contracts.py:29` |
| `AFR-FTS-071` | Apply audit requirements to inter-module integrations | `contracts` | `modules/fts/contracts.py:54` |
| `AFR-FTS-072` | Consuming modules define domain-specific approval policy | `contracts` | `modules/fts/contracts.py:29` |

### 3. Use Case Specifications

| Use Case ID | Name | Layer | Primary Implementation | Target Function / Construct |
| :--- | :--- | :--- | :--- | :--- |
| `FTS-UC-001` | Create New File | `services` | `modules/fts/services/drafts.py:22` | `create_file_draft` |
| `FTS-UC-002` | Edit or Discard Draft File | `services` | `modules/fts/services/drafts.py:99` | `update_file_draft` & `discard_file_draft` |
| `FTS-UC-003` | Send / Forward File to Employee | `services` | `modules/fts/services/movements.py:22` | `forward_file` |
| `FTS-UC-004` | Return Received File | `services` | `modules/fts/services/movements.py:94` | `return_file` |
| `FTS-UC-005` | View Inbox, Outbox, and Open Files | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` | `get_user_inbox_files` & `get_user_outbox_files` |
| `FTS-UC-006` | View File Tracking History | `selectors` | `modules/fts/selectors/movements.py:9` | `get_file_movement_history` |
| `FTS-UC-007` | Archive Completed File | `services` | `modules/fts/services/archival.py:17` | `archive_file` |
| `FTS-UC-008` | Select Assigned Role Context for FTS | `api` | `modules/fts/api/views.py:38` | `_get_current_user_id` |
| `FTS-UC-009` | Administer FTS User Access Context | `registry` | `modules/fts/registry.py:53` | `PERMISSIONS` & `ROLE_GRANTS` |
| `FTS-UC-010` | Use FTS Workflow-Support APIs | `contracts` | `modules/fts/contracts.py:29` | `get_files_by_uins` & `get_active_inbox_files_for_employees` |

### 4. Business Rule Specifications

| Rule ID | Rule Name | Layer | Enforcement Point | Scope & Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| `BR-FTS-001` | Institute Employee Operational Access Rule | `registry` | `modules/fts/registry.py:72` | Restricts operations to faculty and staff roles |
| `BR-FTS-002` | Role Switching Preservation Rule | `models` | `modules/fts/models.py:14` | Preserves owner ID and audit identity |
| `BR-FTS-003` | Persistent Composite File Rule | `models` | `modules/fts/models.py:14` | File contains comments/attachments; no deletion in circulation |
| `BR-FTS-004` | Initial Comment Requirement | `domain` | `modules/fts/domain/workflow.py:41` | Validates non-empty comment upon draft creation |
| `BR-FTS-005` | Draft Boundary Rule | `domain` | `modules/fts/domain/workflow.py:180` | Only draft files can be modified or discarded |
| `BR-FTS-006` | File-Movement Comment Requirement | `domain` | `modules/fts/domain/workflow.py:89` | Movement comment is mandatory on forward and return |
| `BR-FTS-007` | Receiver and Return Eligibility Rule | `domain` | `modules/fts/domain/workflow.py:120` | Returns must route to a valid previous sender |
| `BR-FTS-008` | Chronological Movement Record Rule | `services` | `modules/fts/services/movements.py:22` | Append-only movement records with timestamps |
| `BR-FTS-009` | Associated File Access Rule | `selectors` | `modules/fts/selectors/inbox_outbox.py:13` | Scoping to creator, sender, or receiver |
| `BR-FTS-010` | Role-Based Access and Sensitive Action Rule | `registry` | `modules/fts/registry.py:53` | Permission gating on FTS operations |
| `BR-FTS-011` | Audit Log and Chronological Versioning Rule | `selectors` | `modules/fts/selectors/movements.py:9` | Chronological ordering of audit movements |
| `BR-FTS-012` | Archival Rule | `domain` | `modules/fts/domain/workflow.py:154` | Terminal read-only state; no further forwarding |
| `BR-FTS-013` | Notification Trigger and Delivery Boundary Rule | `services` | `modules/fts/services/movements.py:94` | Notification events fired on movement lifecycle |
| `BR-FTS-014` | FTS Integration Boundary Rule | `contracts` | `modules/fts/contracts.py:29` | Pure plural contract getters |

### 5. Workflow Specifications

| Workflow ID | Workflow Name | Category | Primary Enforcement | Description |
| :--- | :--- | :--- | :--- | :--- |
| `BW-FTS-01` | Forward File to Recipient — Zero Onward Traversal | Basis | `modules/fts/services/movements.py:22` | Single forward transition to recipient |
| `BW-FTS-02` | Onward Forwarding — One Loop Traversal | Basis | `modules/fts/services/movements.py:22` | Onward forward loop execution |
| `BW-FTS-03` | Return File to Previous Sender | Basis | `modules/fts/services/movements.py:94` | Return transition to predecessor |
| `BW-FTS-04` | Archive Completed Circulated File | Basis | `modules/fts/services/archival.py:17` | Terminal archival transition |
| `BW-FTS-05` | Prepare and Circulate New File — Zero Draft-Edit Traversal | Basis | `modules/fts/services/drafts.py:22` | Direct creation to circulation |
| `BW-FTS-06` | Prepare and Circulate New File — One Draft-Edit Traversal | Basis | `modules/fts/services/drafts.py:99` | Edit draft then circulate |
| `BW-FTS-07` | Create and Discard Draft — Zero Draft-Edit Traversal | Basis | `modules/fts/services/drafts.py:148` | Discard draft immediately |
| `BW-FTS-08` | Edit Once and Discard Draft — One Draft-Edit Traversal | Basis | `modules/fts/services/drafts.py:148` | Edit draft then discard |
| `CW-FTS-01` | Collaborative File Circulation and Completion | Composite | `modules/fts/services/movements.py:22` | Forward, return, and archive sequence |
| `CW-FTS-02` | New File Preparation and Initial Outcome | Composite | `modules/fts/services/drafts.py:22` | Creation, edit, and initial outcome sequence |

---

## Step 3.2 (b) — Domain Model

### Entities & Invariants

```
FTSFile (1) ──< (N) FTSMovement (1) ──< (N) FTSComment
     │                                 │
     └──< (N) FTSAttachment ───────────┘
```

#### 1. `FTSFile` (`modules/fts/models.py`)
- `uin`: `CharField(max_length=64, unique=True, db_index=True)` — Unique institutional file number (e.g., `FTS-2024-0001`).
- `subject`: `CharField(max_length=255)` — Mandatory file subject.
- `description`: `TextField(blank=True)` — Optional detailed overview.
- `priority`: `CharField(max_length=20, choices=['low', 'medium', 'high', 'urgent'], default='medium')`
- `category`: `CharField(max_length=50, default='general')`
- `status`: `CharField(max_length=20, choices=['draft', 'in_transit', 'returned', 'received', 'archived'])`
- `is_draft`: `BooleanField(default=True)` — Quick flag for pre-circulation state.
- `creator_id`: `CharField(max_length=64, db_index=True)` — Permanent user identifier of creator (immutable across role switches).
- `creator_role`: `CharField(max_length=64)` — Role context at creation time.
- `current_holder_id`: `CharField(max_length=64, db_index=True)` — Current custodian user ID.
- `current_holder_role`: `CharField(max_length=64, blank=True)`
- `created_at`, `updated_at`: `DateTimeField`

#### 2. `FTSMovement` (`modules/fts/models.py`)
- `file`: `ForeignKey(FTSFile, on_delete=CASCADE, related_name="movements")`
- `from_user_id`: `CharField(max_length=64)`
- `from_role`: `CharField(max_length=64, blank=True)`
- `to_user_id`: `CharField(max_length=64)`
- `to_role`: `CharField(max_length=64, blank=True)`
- `action`: `CharField(max_length=20, choices=['created', 'forwarded', 'returned', 'archived'])`
- `created_at`: `DateTimeField(auto_now_add=True)`

#### 3. `FTSComment` (`modules/fts/models.py`)
- `file`: `ForeignKey(FTSFile, on_delete=CASCADE, related_name="comments")`
- `movement`: `ForeignKey(FTSMovement, on_delete=SET_NULL, null=True, blank=True, related_name="comments")`
- `author_id`: `CharField(max_length=64)`
- `author_role`: `CharField(max_length=64, blank=True)`
- `remarks`: `TextField()` — Mandatory text comment.
- `created_at`: `DateTimeField(auto_now_add=True)`

#### 4. `FTSAttachment` (`modules/fts/models.py`)
- `file`: `ForeignKey(FTSFile, on_delete=CASCADE, related_name="attachments")`
- `movement`: `ForeignKey(FTSMovement, on_delete=SET_NULL, null=True, blank=True, related_name="attachments")`
- `file_name`: `CharField(max_length=255)`
- `file_url`: `CharField(max_length=500)`
- `uploaded_by_id`: `CharField(max_length=64)`
- `uploaded_at`: `DateTimeField(auto_now_add=True)`

### Database Invariants & Constraints
- `uin` is globally unique (`unique=True`).
- Concurrency control: State mutations use `select_for_update()` inside `transaction.atomic` blocks in service functions.
- Append-only integrity: Once a file transitions out of draft (`is_draft=False`), movements and comments are append-only.

---

## Step 3.3 (c) — State Machine

```
              ┌──────────────┐
              │    (New)     │
              └──────┬───────┘
                     │ create_draft
                     ▼
              ┌──────────────┐
  discard     │              │   forward
 ┌────────────┤    DRAFT     ├─────────────┐
 │            │              │             │
 │            └──────────────┘             ▼
 │                                  ┌──────────────┐
 │             forward              │              │
 │          ┌───────────────────────┤  IN_TRANSIT  │
 │          │                       │              │
 │          │  return               └──────┬───────┘
 │          │ ┌────────────────────────────┘
 │          ▼ ▼
 │     ┌──────────────┐
 │     │              │
 │     │   RETURNED   │
 │     │              │
 │     └──────┬───────┘
 │            │ forward
 │            ▼
 │     ┌──────────────┐
 │     │              │
 │     │   RECEIVED   │
 │     │              │
 │     └──────┬───────┘
 │            │ archive (owner only)
 │            ▼
 │     ┌──────────────┐
 │     │              │
 │     │   ARCHIVED   │ (Terminal, Permanent)
 │     │              │
 │     └──────────────┘
 ▼
(Deleted)
```

### Declarative Transition Table

| Current State | Event | Triggering Actor | Guard Condition | Next State |
| :--- | :--- | :--- | :--- | :--- |
| `None` | `CREATE_DRAFT` | Institute Employee | Initial comment non-empty (`BR-FTS-004`) | `DRAFT` |
| `DRAFT` | `EDIT_DRAFT` | File Creator | Caller is creator (`BR-FTS-005`) | `DRAFT` |
| `DRAFT` | `DISCARD_DRAFT` | File Creator | File is uncirculated draft (`BR-FTS-005`) | `(DELETED)` |
| `DRAFT` | `FORWARD` | Current Holder (Creator) | Recipient valid employee, non-empty comment | `IN_TRANSIT` |
| `IN_TRANSIT` | `FORWARD` | Current Holder | Recipient valid employee, non-empty comment | `IN_TRANSIT` |
| `IN_TRANSIT` | `RETURN` | Current Holder | Target in previous senders, non-empty comment | `RETURNED` |
| `RETURNED` | `FORWARD` | Current Holder | Recipient valid employee, non-empty comment | `IN_TRANSIT` |
| `IN_TRANSIT` | `RECEIVE` | Current Holder | Automatic upon custodian view | `RECEIVED` |
| `RECEIVED` | `FORWARD` | Current Holder | Recipient valid employee, non-empty comment | `IN_TRANSIT` |
| `RECEIVED` | `RETURN` | Current Holder | Target in previous senders, non-empty comment | `RETURNED` |
| `IN_TRANSIT` / `RECEIVED` / `RETURNED` | `ARCHIVE` | File Owner | Caller is creator/owner, remark non-empty | `ARCHIVED` |
| `ARCHIVED` | *Any Mutation* | Any Actor | File is terminal and read-only (`BR-FTS-012`) | **ILLEGAL / REFUSED** |

---

## Step 3.4 (d) — Permission List & RBAC

FTS defines fine-grained permissions and grants them to institute roles. RBAC tables reside in `fusion_system_db` (IAM). FTS maintains zero custom authorization tables.

### Module Descriptor (`registry.py`)
```python
MODULE = {
    "code": "fts",
    "label": "File Tracking System",
    "icon": "Folder",
    "base_path": "/fts",
    "nav_section": "Administrative",
    "sort_order": 20,
    "status": "active",
}
```

### Navigation Items
- `fts.inbox`: Icon `"Tray"`, Path `"/fts/inbox"`, Permission `"fts.file.view"`
- `fts.outbox`: Icon `"PaperPlaneTilt"`, Path `"/fts/outbox"`, Permission `"fts.file.view"`
- `fts.drafts`: Icon `"Folder"`, Path `"/fts/drafts"`, Permission `"fts.file.view"`
- `fts.new`: Icon `"Folder"`, Path `"/fts/new"`, Permission `"fts.file.create"`

### Declared Permissions
```python
PERMISSIONS = [
    ("fts.file.view", "View accessible files and tracking history"),
    ("fts.file.create", "Create and save draft files"),
    ("fts.file.review", "Forward and return circulating files"),
    ("fts.file.manage", "Archive completed files"),
]
```

### Role Grants
Institute Employees comprise Faculty and Staff. Both categories hold full operational file processing capabilities:
```python
ROLE_GRANTS = {
    "faculty": ["fts.file.view", "fts.file.create", "fts.file.review", "fts.file.manage"],
    "staff": ["fts.file.view", "fts.file.create", "fts.file.review", "fts.file.manage"],
}
```

---

## Step 3.5 (e) — Endpoint List

All REST API endpoints are mounted under `/api/v1/fts/files/`:

| Method | Endpoint Path | Required Permission | Input Payload | Return Structure | Enforced Rules |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/fts/files/inbox/` | `fts.file.view` | None | List of active inbox files | `BR-FTS-009`, `FTS-UC-005` |
| `GET` | `/api/v1/fts/files/outbox/` | `fts.file.view` | None | List of active outbox files | `BR-FTS-009`, `FTS-UC-005` |
| `GET` | `/api/v1/fts/files/drafts/` | `fts.file.view` | None | List of drafts created by user | `BR-FTS-005`, `FTS-UC-005` |
| `POST` | `/api/v1/fts/files/create-draft/` | `fts.file.create` | `CreateDraftSerializer` | Created draft summary (`id`, `uin`, `status`) | `BR-FTS-003`, `BR-FTS-004`, `FTS-UC-001` |
| `POST` | `/api/v1/fts/files/{id}/forward/` | `fts.file.review` | `ForwardFileSerializer` | Movement record (`movement_id`, `holder`) | `BR-FTS-006`, `BR-FTS-007`, `FTS-UC-003` |
| `POST` | `/api/v1/fts/files/{id}/return_file_action/` | `fts.file.review` | `ReturnFileSerializer` | Return record (`movement_id`, `returned_to`) | `BR-FTS-006`, `BR-FTS-007`, `FTS-UC-004` |
| `POST` | `/api/v1/fts/files/{id}/archive/` | `fts.file.manage` | `ArchiveFileSerializer` | Archival record (`status: archived`) | `BR-FTS-012`, `FTS-UC-007` |
| `GET` | `/api/v1/fts/files/{id}/history/` | `fts.file.view` | None | Chronological movement audit trail | `BR-FTS-008`, `BR-FTS-011`, `FTS-UC-006` |

### Fusion-client Integration Array (`INTEGRATED_MODULES`)
For standalone or framed deployment, the sidebar entry is:
```javascript
{
  id: "fts",
  label: "File Tracking System",
  icon: "Folder",
  to: "/fts",
  section: "Administrative"
}
```

---

## Step 3.6 (f) — Contracts

`modules/fts/contracts.py` exposes strictly plural getters for inter-module integration. Consuming modules (e.g., Leave, Academics) reach FTS exclusively via these functions.

```python
def get_files_by_uins(uins: Sequence[str]) -> list[FileSummaryDTO]:
    """Plural retrieval of file summaries by UIN list."""

def get_active_inbox_files_for_employees(
    employee_ids: Sequence[str]
) -> dict[str, list[FileSummaryDTO]]:
    """Plural retrieval of active files in inbox for given employee IDs."""
```

`FileSummaryDTO` dataclass:
- `file_id`: `int`
- `uin`: `str`
- `subject`: `str`
- `status`: `str`
- `priority`: `str`
- `category`: `str`
- `creator_id`: `str`
- `current_holder_id`: `str`
- `created_at`: `datetime`
- `updated_at`: `datetime`

---

## Step 3.7 (g) — Scheduled Work

The File Tracking System does not require Celery beat background schedules. All file status changes, movement logs, and audit entries are strictly transactional and event-driven, executing synchronously upon actor actions (forward, return, archive).

---

## Step 3.8 (h) — Open Questions & Approver Sign-off

### Domain Clarifications & Known Gaps
1. **Central Notification Delivery**: `BR-FTS-013` specifies that notification events are triggered upon file movements and delegated to Fusion central notification infrastructure. Central delivery mechanisms are mocked/stubbed in the test suite and decoupled from FTS internal storage.
2. **Archival Objective Completion**: `BR-FTS-012` specifies that a file is archived when its collaborative objective is complete. The system enforces owner authorization; the determination of business completion remains with the human file owner.

### Formal Approval Record
- **Approver**: Student 2 (`24BCS067`, Daggula Amulya)
- **Decision Date**: 2026-11-21
- **Verdict**: APPROVED. All design sections (Steps 3.1–3.8) verified compliant with Fusion modular architecture and specification requirements.
