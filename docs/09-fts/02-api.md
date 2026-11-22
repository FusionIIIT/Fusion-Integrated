# FTS API Specification & Contract Reference

**Module**: File Tracking System (`fts`)  
**Base URL**: `/api/v1/fts/`  
**OpenAPI Tag**: `fts`

---

## 1. Authentication & Permissions

All endpoints require authentication via the platform session cookie or Bearer token.
Access is governed by RBAC permissions registered in `modules/fts/registry.py`:

| Permission Code | Description | Authorized Roles |
|---|---|---|
| `fts.file.create` | Create files and manage drafts | Faculty, Staff, Officers, Administrators |
| `fts.file.forward` | Forward files to colleagues | Faculty, Staff, Officers, Administrators |
| `fts.file.return` | Return received files to sender | Faculty, Staff, Officers, Administrators |
| `fts.file.archive` | Archive circulated files (Owner only) | Faculty, Staff, Officers, Administrators |
| `fts.file.view` | View inbox, outbox, and file history | Faculty, Staff, Officers, Administrators |
| `fts.governance.view` | View audit trail and usage statistics | System Administrator, Admin |
| `fts.integration.access` | Inter-module workflow file creation | System Services, Integration Clients |
| `fts.notification.dispatch` | Dispatch asynchronous notifications | Background Celery Workers |

---

## 2. API Endpoints

### 2.1 File Operations

#### `POST /api/v1/fts/files/`
Create a new file or draft.
- **Permission**: `fts.file.create`, `IsInstituteEmployee`
- **Request Body**:
  ```json
  {
    "subject": "Project Proposal - Phase 2",
    "description": "Funding and staff requirements for research grant.",
    "comment": "Submitted for approval and processing.",
    "is_draft": false,
    "recipient_user_id": 201,
    "recipient_username": "dean_rnd",
    "recipient_role": "Dean R&D",
    "attachments": [
      {
        "file_name": "proposal_v1.pdf",
        "file_url": "https://storage.fusion.ac.in/fts/prop.pdf",
        "file_size": 204800,
        "mime_type": "application/pdf"
      }
    ]
  }
  ```
- **Response** (`201 Created`): `FileDetail`

#### `GET /api/v1/fts/inbox/`
List files currently in the authenticated user's active possession (`CIRCULATED` status).
- **Permission**: `fts.file.view`, `IsInstituteEmployee`
- **Response** (`200 OK`): `FileListSerializer[]`

#### `GET /api/v1/fts/outbox/`
List files created or forwarded by the authenticated user.
- **Permission**: `fts.file.view`, `IsInstituteEmployee`
- **Response** (`200 OK`): `FileListSerializer[]`

#### `GET /api/v1/fts/drafts/`
List pre-circulation drafts created by the authenticated user.
- **Permission**: `fts.file.create`, `IsInstituteEmployee`
- **Response** (`200 OK`): `FileListSerializer[]`

#### `GET /api/v1/fts/files/{id}/`
Retrieve detailed metadata, attachments, and current holder information.
- **Permission**: `fts.file.view` (scoped to stakeholders or governance viewers)
- **Response** (`200 OK`): `FileDetailSerializer`

#### `PUT /api/v1/fts/files/{id}/`
Update an uncirculated draft file (`DRAFT` status only).
- **Permission**: `fts.file.create`, `IsInstituteEmployee`
- **Response** (`200 OK`): `FileDetailSerializer`

#### `POST /api/v1/fts/files/{id}/forward/`
Forward an active file to another employee.
- **Permission**: `fts.file.forward`, `IsInstituteEmployee`
- **Guard**: User must be `current_holder`. File must be in `CIRCULATED` status.
- **Request Body**:
  ```json
  {
    "to_user_id": 305,
    "to_username": "finance_officer",
    "to_role": "Finance Officer",
    "comment": "Forwarding for budget verification.",
    "attachments": []
  }
  ```
- **Response** (`200 OK`): `FileMovementSerializer`

#### `POST /api/v1/fts/files/{id}/return/`
Return received file to the preceding sender or creator.
- **Permission**: `fts.file.return`, `IsInstituteEmployee`
- **Guard**: User must be `current_holder`. File must be in `CIRCULATED` status.
- **Request Body**:
  ```json
  {
    "comment": "Please clarify item 3 in budget table.",
    "attachments": []
  }
  ```
- **Response** (`200 OK`): `FileMovementSerializer`

#### `POST /api/v1/fts/files/{id}/archive/`
Archive a completed file.
- **Permission**: `fts.file.archive`, `IsInstituteEmployee`
- **Guard**: User must be the `owner` (creator). File must be in `CIRCULATED` status.
- **Response** (`200 OK`): `FileDetailSerializer`

#### `POST /api/v1/fts/files/{id}/discard/`
Permanently abandon an uncirculated draft file.
- **Permission**: `fts.file.create`, `IsInstituteEmployee`
- **Guard**: User must be the creator. File must be in `DRAFT` status.
- **Response** (`200 OK`): `FileDetailSerializer` (status updated to `DISCARDED`)

#### `GET /api/v1/fts/files/{id}/history/`
Retrieve chronological movement history and comments trail.
- **Permission**: `fts.file.view`
- **Response** (`200 OK`): `FileMovementSerializer[]`

---

### 2.2 Governance & Administration

#### `GET /api/v1/fts/governance/usage/`
Summary counts of total files, drafts, circulated files, archived files, and movements.
- **Permission**: `fts.governance.view`
- **Response** (`200 OK`): `UsageMetricsSerializer`

#### `GET /api/v1/fts/governance/audit-logs/`
Full chronological audit trail with optional filtering by `file_id`.
- **Permission**: `fts.governance.view`
- **Query Parameters**: `file_id` (optional integer)
- **Response** (`200 OK`): `FileAuditLogSerializer[]`

---

## 3. Public Integration Contracts (`modules/fts/contracts.py`)

External modules integrate with FTS using plural functions:
```python
def get_file_statuses(file_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
  """Return status, holder, and reference number for given file IDs."""


def get_files_for_users(
    user_ids: Sequence[int],
) -> dict[int, list[dict[str, Any]]]:
  """Return all currently held files for the provided user IDs."""


def create_module_tracked_file(
    calling_module: str,
    subject: str,
    creator_user_id: int,
    creator_username: str,
    creator_role: str,
    initial_comment: str,
    recipient_user_id: int,
    recipient_username: str,
    recipient_role: str,
    description: str = "",
) -> dict[str, Any]:
  """Public contract for other Fusion modules to initiate a tracked file."""
```
