# Institute Works Department (IWD) — Module Blueprint

**Module Code**: `iwd`  
**Docs Folder**: `docs/09-iwd/`  
**Environment**: `module-only`  
**Author / Builder (Student 1)**: Meet Patel (24BCS186)  
**Reviewer / Approver (Student 2)**: Ashmi (24BCS282)  
**Date Approved**: 2026-11-20 by Ashmi (Student 2, written sign-off)

---

## 1. Traceability Table

| Id | What it requires | Layer | Enforcement point | Notes |
|---|---|---|---|---|
| CFR-IWD-01 | Create work request in draft status | API / Model | `WorkRequestViewSet.perform_create` | Validates title, location, category |
| CFR-IWD-02 | Submit work request for review | API / Domain | `WorkRequestViewSet.submit`, `rules.validate_transition` | Transitions `draft` -> `submitted` |
| CFR-IWD-03 | Take request under review | API / Domain | `WorkRequestViewSet.review`, `rules.validate_transition` | Transitions `submitted` -> `under_review` |
| CFR-IWD-04 | Approve work request & assign engineer | API / Domain | `WorkRequestViewSet.approve`, `rules.validate_transition` | Populates `assigned_to`, transitions to `approved` |
| CFR-IWD-05 | Reject work request with mandatory note | API / Domain | `WorkRequestViewSet.reject`, `rules.validate_transition` | Terminal state `rejected`, records audit note |
| CFR-IWD-06 | Start approved work | API / Domain | `WorkRequestViewSet.start`, `rules.validate_transition` | Transitions `approved` -> `in_progress` |
| CFR-IWD-07 | Complete in-progress work | API / Domain | `WorkRequestViewSet.complete`, `rules.validate_transition` | Records `actual_cost`, transitions to `completed` |
| CFR-IWD-08 | Close completed work request | API / Domain | `WorkRequestViewSet.close`, `rules.validate_transition` | Terminal state `closed` |
| CFR-IWD-09 | Put request on hold / resume | API / Domain | `WorkRequestViewSet.hold`, `start` | Transitions to/from `on_hold` |
| CFR-IWD-10 | Contractor directory management | Model / API | `ContractorViewSet` | CRUD for registered contractors |
| CFR-IWD-11 | Inventory stock management | Model / API | `InventoryItemViewSet` | Tracks available quantity and low-stock flag |
| CFR-IWD-12 | Comprehensive audit trail | Model / API | `WorkRequestLog`, `requests/{id}/logs/` | Immutable event log for every state transition |
| BR-IWD-001 | Active-role requester authentication | API | `WorkRequestViewSet.perform_create` | Captures authenticated user or `X-User` header |
| BR-IWD-002 | Automatic engineer assignment | Domain / API | `WorkRequestViewSet.approve` | Updates `assigned_to` on approval |
| BR-IWD-003 | Cost-band routing (> Rs. 1,00,000) | Domain | `rules.requires_director_approval` | Requires Director escalation |
| BR-IWD-007 | High-cost capital budget (> Rs. 5,00,000) | Domain | `rules.requires_budget_allocation` | Capital budget allocation required |
| BR-IWD-010 | Low-stock trigger rule | Model / Domain | `InventoryItem.is_low_stock` | Flagged when `quantity_available <= minimum_stock` |
| BR-IWD-012 | Urgency priority scoring | Domain | `rules.compute_priority_score` | Accelerated priority score based on deadline |
| BR-IWD-013 | Audit logging of all decisions | Domain / ORM | `WorkRequestLog.objects.create` | Every action recorded with actor and timestamp |
| BR-IWD-014 | State machine legality validation | Domain | `rules.validate_transition` | Strict state transitions; terminal closed state |

---

## 2. Domain Model

### Entities & Invariants

1. **`WorkRequest`** (`iwd_work_request`):
   - `id`: Auto-incrementing primary key.
   - `title`: CharField(max_length=200). Minimum 5 chars.
   - `description`: TextField(). Minimum 10 chars.
   - `location`: CharField(max_length=200). Non-empty location.
   - `category`: CharField with choices from `WorkCategory` (`civil`, `electrical`, `plumbing`, `carpentry`, `housekeeping`, `repair`, `new_construction`, `other`).
   - `priority`: CharField with choices from `Priority` (`low`, `medium`, `high`, `urgent`).
   - `status`: CharField with choices from `RequestStatus` (`draft`, `submitted`, `under_review`, `approved`, `rejected`, `in_progress`, `on_hold`, `completed`, `closed`). Default `draft`.
   - `requester_username`: CharField(max_length=100).
   - `assigned_to`: CharField(max_length=100, blank=True).
   - `estimated_cost`: DecimalField(max_digits=12, decimal_places=2, default=0.00). Must be non-negative.
   - `actual_cost`: DecimalField(max_digits=12, decimal_places=2, null=True, blank=True).
   - `remarks`: TextField(blank=True).
   - `created_at`, `updated_at`, `submitted_at`, `completed_at`: Timestamps.

2. **`Contractor`** (`iwd_contractor`):
   - `id`: Primary key.
   - `name`: CharField(max_length=200).
   - `contact_person`: CharField(max_length=100).
   - `phone`: CharField(max_length=20).
   - `email`: EmailField(blank=True).
   - `specialization`: CharField(max_length=100).
   - `is_active`: BooleanField(default=True).

3. **`InventoryItem`** (`iwd_inventory_item`):
   - `id`: Primary key.
   - `name`: CharField(max_length=200).
   - `unit`: CharField(max_length=50).
   - `quantity_available`: IntegerField(default=0).
   - `minimum_stock`: IntegerField(default=10).
   - Property `is_low_stock`: Returns `quantity_available <= minimum_stock`.

4. **`WorkRequestLog`** (`iwd_work_request_log`):
   - `id`: Primary key.
   - `work_request`: ForeignKey to `WorkRequest` (CASCADE).
   - `from_status`: CharField(max_length=30).
   - `to_status`: CharField(max_length=30).
   - `actor_username`: CharField(max_length=100).
   - `note`: TextField(blank=True).
   - `changed_at`: DateTimeField(auto_now_add=True).

---

## 3. Declarative State Machine

Allowed transition graph defined in `modules/iwd/domain/rules.py`:

```python
ALLOWED_TRANSITIONS = {
    RequestStatus.DRAFT: [RequestStatus.SUBMITTED],
    RequestStatus.SUBMITTED: [RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED],
    RequestStatus.UNDER_REVIEW: [RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.ON_HOLD],
    RequestStatus.APPROVED: [RequestStatus.IN_PROGRESS, RequestStatus.ON_HOLD],
    RequestStatus.IN_PROGRESS: [RequestStatus.COMPLETED, RequestStatus.ON_HOLD],
    RequestStatus.ON_HOLD: [RequestStatus.IN_PROGRESS, RequestStatus.REJECTED],
    RequestStatus.COMPLETED: [RequestStatus.CLOSED],
    RequestStatus.REJECTED: [],
    RequestStatus.CLOSED: [],
}
```

Rules:
- Illegal transitions raise `IWDDomainError` and map to HTTP 400 Bad Request.
- `REJECTED` and `CLOSED` states have empty transition lists (terminal states).

---

## 4. Permissions & Access Control

Registered in `modules/iwd/registry.py`:

```python
MODULE = {
    "code": "iwd",
    "name": "Institute Works Department",
    "description": "Maintenance, civil, electrical, plumbing, and construction work request management.",
    "app_label": "iwd",
}

PERMISSIONS = [
    {"code": "iwd.work_request.view", "name": "View IWD work requests"},
    {"code": "iwd.work_request.create", "name": "Create IWD work requests"},
    {"code": "iwd.work_request.approve", "name": "Approve IWD work requests"},
    {"code": "iwd.work_request.assign", "name": "Assign engineers to work requests"},
    {"code": "iwd.work_request.close", "name": "Close completed work requests"},
    {"code": "iwd.contractor.manage", "name": "Manage contractors"},
    {"code": "iwd.inventory.manage", "name": "Manage maintenance inventory"},
    {"code": "iwd.budget.view", "name": "View IWD budgets"},
    {"code": "iwd.budget.manage", "name": "Manage IWD capital budgets"},
    {"code": "iwd.report.view", "name": "View IWD management reports"},
]

ROLE_GRANTS = {
    "iwd_requester": ["iwd.work_request.view", "iwd.work_request.create"],
    "iwd_engineer": ["iwd.work_request.view", "iwd.inventory.manage"],
    "iwd_supervisor": ["iwd.work_request.view", "iwd.work_request.approve", "iwd.work_request.assign", "iwd.work_request.close", "iwd.contractor.manage", "iwd.inventory.manage"],
    "iwd_director": ["iwd.work_request.view", "iwd.work_request.approve", "iwd.budget.view", "iwd.budget.manage", "iwd.report.view"],
}
```

---

## 5. Approvals Sign-off

- **Blueprint approved**: Yes, by Student 2 (Ashmi) on 2026-11-20.
- **Shared configuration changes approved**:
  - `config/settings/base.py`: Registered `modules.iwd` in `INSTALLED_APPS` (Approved by Ashmi).
  - `config/urls.py`: Included `modules.iwd.api.urls` router at `api/v1/iwd/` (Approved by Ashmi).
- **New external dependencies**: None (uses core Django, DRF, and pytest-django).
