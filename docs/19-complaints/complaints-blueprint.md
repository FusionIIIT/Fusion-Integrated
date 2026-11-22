# Complaint Management System (CMS) — Architecture Blueprint

| Field | Value |
| :--- | :--- |
| **Module** | Complaint Management System (`modules/complaints`) |
| **Module Code** | `complaints` |
| **Docs Folder** | `docs/19-complaints` |
| **Author** | Student 1 (`24BCS134`, kushagra-005) |
| **Approver** | Student 2 (`24BCS038`, Ashish Kumar Meena) |
| **Status** | APPROVED (2026-11-22) |
| **Specification Baseline** | CMS Specifications v1.4 FINAL (CFR/AFR Registry, Use Cases, Business Rules, Workflows) |

---

## 1. Executive Summary & Bounded Context

The Complaint Management System (CMS) provides automated grievance intake, routing, resolution, verified closure, and escalation workflows for students, faculty, staff, and administrators within the Fusion ERP ecosystem at IIITDM Jabalpur.

CMS operates as a single bounded domain context governing:
1. **Intake & Categorization**: Student, faculty, and staff grievance logging against active categories with automatic SLA deadline computation.
2. **Assignment & Handling**: Assignment by handlers/supervisors to designated handlers and transition to `in_progress`.
3. **Resolution & Verification**: Resolution logging with mandatory resolution comments; closure gated by user verification or supervisor review where required.
4. **Reopening Lifecycle**: Explicit complainant reopening requests within policy limits, reviewed and approved/denied by supervisors.
5. **Escalation Management**: Single-tier manual escalation to supervisors, and background SLA breach automatic escalation.
6. **Post-Closure Feedback**: Single feedback submission per complaint with 1-5 rating bounds.
7. **Cross-Module Isolation**: Zero direct cross-module database foreign keys; identity and RBAC resolved strictly via Fusion IAM tokens.

---

## Step 3.1 (a) — Traceability Table

| Requirement ID | Description | Enforcement Point |
| :--- | :--- | :--- |
| `CFR-001` / `AFR-001..010` | Complaint Intake & Category Mapping | `modules/complaints/services/complaints.py:submit_complaint` |
| `CFR-002` / `AFR-011..018` | Handler Assignment & Delegation | `modules/complaints/services/complaints.py:assign_complaint` |
| `CFR-003` / `AFR-019..024` | In-Progress Lifecycle Updates | `modules/complaints/services/complaints.py:progress_complaint` |
| `CFR-004` / `AFR-025..032` | Resolution & Verification Routing | `modules/complaints/services/complaints.py:resolve_complaint` |
| `CFR-005` / `AFR-033..038` | Rejection with Mandatory Reason | `modules/complaints/services/complaints.py:reject_complaint` |
| `CFR-006` / `AFR-039..045` | User & Supervisor Verified Closure | `modules/complaints/services/complaints.py:verify_closure` |
| `CFR-007` / `AFR-046..052` | Reopening Request Submission | `modules/complaints/services/complaints.py:request_reopen` |
| `CFR-008` / `AFR-053..058` | Supervisor Reopen Review | `modules/complaints/services/complaints.py:review_reopen` |
| `CFR-009` / `AFR-059..063` | Manual Escalation Guard | `modules/complaints/services/complaints.py:escalate_complaint` |
| `CFR-010` / `AFR-064..067` | Background SLA Breach Escalation | `modules/complaints/services/complaints.py:check_and_escalate_sla_breaches` |
| `CFR-011` / `AFR-068..071` | Post-Closure Feedback Logging | `modules/complaints/services/complaints.py:submit_feedback` |
| `CFR-012` / `AFR-072..073` | 75% SLA Reminder Flag | `modules/complaints/services/complaints.py:check_and_send_sla_reminders` |

---

## Step 3.2 (b) — Domain Model

- **Complaint**: `id`, `title`, `description`, `category` (FK), `status` (Enum), `priority` (Enum), `complainant_user_id`, `handler_user_id`, `supervisor_user_id`, `sla_deadline`, `sla_reminder_sent`, `created_at`, `updated_at`, `resolved_at`, `closed_at`.
- **ComplaintCategory**: `id`, `name`, `code`, `is_active`, `max_sla_hours`, `requires_supervisor_review`, `requires_user_verification`.
- **ComplaintComment**: `id`, `complaint` (FK), `author_user_id`, `comment`, `created_at`.
- **ComplaintEscalation**: `id`, `complaint` (FK), `escalation_type`, `from_user_id`, `to_user_id`, `reason`, `created_at`.
- **ComplaintFeedback**: `id`, `complaint` (OneToOne), `rating` (1-5), `comments`, `created_at`.

---

## Step 3.3 (c) — State Machine

Formal state transitions enforced in `modules/complaints/domain/state_machine.py`:
- `submitted` -> `assigned` (via assign)
- `submitted` -> `rejected` (via reject)
- `assigned` -> `in_progress` (via progress)
- `assigned` -> `rejected` (via reject)
- `in_progress` -> `resolved` (via resolve)
- `in_progress` -> `rejected` (via reject)
- `resolved` -> `closed` (via verify_close)
- `resolved` -> `reopen_requested` (via reopen_request)
- `reopen_requested` -> `in_progress` (via approve reopen)
- `reopen_requested` -> `closed` (via deny reopen)

---

## Step 3.4 (d) — Permission List & RBAC

Registered in `modules/complaints/registry.py`:
- `complaints.complaint.submit`
- `complaints.complaint.assign`
- `complaints.complaint.progress`
- `complaints.complaint.resolve`
- `complaints.complaint.verify_close`
- `complaints.complaint.reopen_request`
- `complaints.complaint.review_reopen`
- `complaints.complaint.escalate`
- `complaints.complaint.feedback`
- `complaints.complaint.sla_check`

---

## Step 3.5 (e) — Endpoint List

- `POST /api/v1/complaints/` — Submit complaint
- `GET /api/v1/complaints/` — List complaints with role filters
- `GET /api/v1/complaints/<id>/` — Retrieve complaint detail
- `POST /api/v1/complaints/<id>/assign/` — Assign handler
- `POST /api/v1/complaints/<id>/progress/` — Update progress
- `POST /api/v1/complaints/<id>/resolve/` — Mark resolved
- `POST /api/v1/complaints/<id>/reject/` — Reject complaint
- `POST /api/v1/complaints/<id>/verify-close/` — Verified closure
- `POST /api/v1/complaints/<id>/reopen-request/` — Request reopening
- `POST /api/v1/complaints/<id>/reopen-review/` — Approve/deny reopening
- `POST /api/v1/complaints/<id>/escalate/` — Manual escalation
- `POST /api/v1/complaints/<id>/feedback/` — Submit feedback
- `POST /api/v1/complaints/sla-check/` — Run background SLA audit

---

## Step 3.6 (f) — Plural Contracts

Declared in `modules/complaints/contracts.py`:
- `get_complaints_by_complainant_ids(user_ids: list[int]) -> list[dict]`
- `get_complaints_by_ids(complaint_ids: list[int]) -> list[dict]`

---

## Step 3.7 (g) — Scheduled Work

1. **SLA Breach Check**: Celery beat schedule runs every 15 minutes checking overdue active complaints past `sla_deadline`, automatically creating `automatic_sla` escalation records and reassigning to category supervisors.
2. **75% SLA Reminder**: Flags complaints exceeding 75% elapsed SLA window with `sla_reminder_sent = True`.

---

## Step 3.8 (h) — Open Questions & Approver Sign-off

- Approver: Student 2 (`24BCS038`, Ashish Kumar Meena)
- Approval Date: 2026-11-22
- Decision: Approved without waivers. All 12 CFRs and 73 AFRs represented in domain logic and contracts.
