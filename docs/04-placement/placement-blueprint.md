# Module Blueprint: Placement Cell Management System (PCMS)
**Module Code:** `placement` | **Docs Folder:** `docs/04-placement/` | **Environment:** `module-only`  
**Author (Student 1):** Rohan (`24BCS060`) | **Approver (Student 2):** Partner (`24BCS135`)  
**Approval Date:** 2026-11-16 | **Status:** APPROVED BY STUDENT 2

---

## 1. Specification Mapping & Traceability (Step 3.1)

PCMS implements the 6 specification documents located in `C:\Users\rohan\Downloads\PCMS_SPECS`:
- `01_PC_Problem_Statement_v1.2_SYNCHRONIZED.docx`
- `02_PC_Requirement_Registry_CFR_AFR_v1.3_FINAL.docx` (64 Active Functional Requirements: `PC-AFR-001` to `PC-AFR-064`)
- `03_PC_Use_Case_Specifications_v1.3_FINAL.docx` (22 Active Use Cases: `PC-UC-001` to `PC-UC-022`)
- `04_PC_Business_Rule_Specifications_v1.3_FINAL.docx` (26 Active Business Rules: `PC-BR-001` to `PC-BR-026`)
- `05_PC_Workflow_Specifications_v1.3_FINAL.docx` (12 Workflows: `BW-PC-01` to `BW-PC-08`, `CW-PC-01` to `CW-PC-04`)
- `06_PC_Traceability_Matrix_v1.3_FINAL.xlsx`

### Core Traceability Highlights

| Spec Category | IDs Covered | Implementation Files | Primary API Endpoints |
| :--- | :--- | :--- | :--- |
| **Registration & Profile** | `PC-AFR-001..008`, `PC-UC-001..004`, `PC-BR-001..002` | `models/students.py`, `services/registration.py` | `/api/placement/registration/`, `/api/placement/profile/` |
| **Company & Verification** | `PC-AFR-009..015`, `PC-UC-005`, `PC-BR-004..006` | `models/companies.py`, `services/companies.py` | `/api/placement/companies/`, `/api/placement/companies/register/` |
| **Job Postings & Rules** | `PC-AFR-016..025`, `PC-UC-006..008`, `PC-BR-003, 007` | `models/postings.py`, `services/postings.py` | `/api/placement/postings/`, `/api/placement/postings/{id}/publish/` |
| **Applications & Clearance**| `PC-AFR-026..036`, `PC-UC-009..012`, `PC-BR-008..012` | `models/applications.py`, `services/applications.py` | `/api/placement/applications/`, `/api/placement/applications/{id}/submit/` |
| **Interviews & Shortlisting**| `PC-AFR-037..043`, `PC-UC-013..015`, `PC-BR-013..015` | `models/interviews.py`, `services/interviews.py` | `/api/placement/interviews/`, `/api/placement/shortlists/` |
| **Offers & Tier Policy** | `PC-AFR-044..053`, `PC-UC-016..018`, `PC-BR-016..020` | `models/offers.py`, `services/offers.py` | `/api/placement/offers/`, `/api/placement/offers/{id}/accept/` |
| **Conduct & Debarment** | `PC-AFR-054..058`, `PC-UC-019..020`, `PC-BR-021..023` | `models/students.py`, `services/conduct.py` | `/api/placement/conduct/incidents/`, `/api/placement/debarment/` |
| **Stats, Audits & Exports**| `PC-AFR-059..064`, `PC-UC-021..022`, `PC-BR-024..026` | `services/stats.py`, `api/exports.py` | `/api/placement/statistics/`, `/api/placement/exports/` |

---

## 2. Domain Model & Database Schema (Step 3.2)

### Architectural Rules
- **No Cross-Module Foreign Keys:** Identity references (`user_id`, `student_id`) use UUIDs / string identifiers without Django FKs to external apps, strictly adhering to ADR 0013.
- **Transactional State Transitions:** All state transitions (Application states, Offer statuses, Job Posting statuses) execute within `transaction.atomic()` with strict row locks (`select_for_update()`).
- **Database Constraints:** Check constraints enforce domain invariants (e.g., `posting_published_has_required_content`, `posting_published_has_locked_rule`, `deadline_cannot_shorten`).

### Core Entities
1. `PlacementRegistration`: Tracks student registration status (`pending`, `registered`, `debarred`, `opted_out`).
2. `StudentPlacementProfile`: Encapsulates resume drive links, academic verification status, and contact details.
3. `Company`: Verified employer profile with domain-verified recruiters.
4. `JobPosting`: Drives job postings (`draft`, `pending_approval`, `published`, `closed`). Enforces immutable rules upon publication.
5. `JobApplication`: Application lifecycle (`applied`, `shortlisted`, `interview_scheduled`, `offered`, `rejected`, `withdrawn`).
6. `JobOffer`: Tracks offers, compensation CTC, dream/core/open tier classification, acceptance/rejection, and institute single-offer / upgrade policies.

---

## 3. Permission Matrix & Role Grants (Step 3.3)

Defined in `modules/placement/registry.py`:

```python
PERMISSIONS = [
    ("placement_cell.job_posting.view", "View job postings"),
    ("placement_cell.job_posting.manage", "Create, edit, and publish job postings"),
    ("placement_cell.application.create", "Submit job application"),
    ("placement_cell.application.view_self", "View own applications"),
    ("placement_cell.application.review", "Review and shortlist applications"),
    ("placement_cell.offer.manage", "Issue and update job offers"),
    ("placement_cell.offer.respond", "Accept or reject received job offer"),
    ("placement_cell.statistics.view", "View placement statistics and reports"),
    ("placement_cell.statistics.student.view", "View student placement overview"),
    ("placement_cell.announcement.view", "View placement announcements"),
    ("placement_cell.announcement.manage", "Create and publish announcements"),
    ("placement_cell.conduct.manage", "Log conduct incidents and debarment"),
    ("placement_cell.company.manage", "Verify and manage recruiting companies"),
]

ROLE_GRANTS = {
    "student": [
        "placement_cell.job_posting.view",
        "placement_cell.application.create",
        "placement_cell.application.view_self",
        "placement_cell.offer.respond",
        "placement_cell.statistics.student.view",
        "placement_cell.announcement.view",
    ],
    "placement_coordinator": [
        "placement_cell.job_posting.view",
        "placement_cell.job_posting.manage",
        "placement_cell.application.review",
        "placement_cell.announcement.view",
        "placement_cell.announcement.manage",
        "placement_cell.statistics.view",
    ],
    "placement_officer": [
        "placement_cell.job_posting.view",
        "placement_cell.job_posting.manage",
        "placement_cell.application.review",
        "placement_cell.offer.manage",
        "placement_cell.conduct.manage",
        "placement_cell.company.manage",
        "placement_cell.announcement.manage",
        "placement_cell.statistics.view",
    ],
}
```

---

## 4. API Contracts & Endpoints (Step 3.4)

All endpoints live under `/api/placement/` and follow DRF conventions:
- `POST /api/placement/postings/` (201 Created / 400 Validation Error)
- `POST /api/placement/postings/{id}/publish/` (200 OK / 400 Bad Request on missing locked rules)
- `POST /api/placement/postings/{id}/apply/` (201 Created / 403 Forbidden / 400 Bad Request)
- `GET /api/placement/applications/my/` (200 OK)
- `POST /api/placement/offers/{id}/respond/` (200 OK / 400 Bad Request)
- `GET /api/placement/statistics/summary/` (200 OK, excludes debarred/opted-out from placed counts)
- `GET /api/placement/openapi/` & OpenAPI schema synchronization.

---

## 5. Frontend Navigation & Route Guards (Step 3.5)

Client routes in `client/src/modules/placement/routes.tsx`:
- `/placement`: Student Dashboard (Guarded by `placement_cell.application.view_self`)
- `/placement/postings`: Browse Job Postings (Guarded by `placement_cell.job_posting.view`)
- `/placement/applications`: Application Status (Guarded by `placement_cell.application.view_self`)
- `/placement/manage/postings`: Coordinator Postings Desk (Guarded by `placement_cell.job_posting.manage`)
- `/placement/manage/applications`: Application Review & Shortlisting (Guarded by `placement_cell.application.review`)
- `/placement/manage/offers`: Officer Offer Desk (Guarded by `placement_cell.offer.manage`)
- `/placement/manage/statistics`: Placement Reports (Guarded by `placement_cell.statistics.view`)

Every route wrapped in `<RequirePermission>` with dedicated Loading, Empty, and Error states.

---

## 6. Background Scheduling & Celery Tasks (Step 3.6)

Registered in `modules/placement/schedule.py` and `config/celery.py`:
- `placement.expire_stale_postings`: Hourly task moving past-deadline postings from `published` to `closed`.
- `placement.process_offer_deadlines`: Daily task expiring unanswered offers past the 48-hour acceptance window.
- `placement.dispatch_outbox_events`: Processes pending outbox events with exponential backoff.

---

## 7. Testing Strategy & Quality Gates (Step 3.7)

1. **Unit & Domain Tests:** Verify isolated state machines, eligibility rule evaluator, offer policy checks.
2. **Integration Tests:** Exercise viewsets, permissions, database checks, and serializer validations.
3. **Adversarial Security Tests:** Attempt privilege escalation, cross-tenant leaks, bypassing locked rules.
4. **Client Route Guard Tests:** Verify frontend permission enforcements fail gracefully when permissions lack.
5. **Coverage Target:** >85% line coverage on `modules.placement`.

---

## 8. Approvals, Known Gaps & Decisions (Step 3.8)

- **Approval Record:**
  > "Approved by Student 2 (Partner <24bcs135@iiitdmj.ac.in>) on 2026-11-16. Blueprint satisfies all 64 AFRs, 22 UCs, 26 BRs, and 12 Workflows without introducing unsupported platform dependencies."
- **Known Gaps:** None. All live specification obligations are mapped to active implementation files.
- **External Dependencies:** Only standard Fusion-Integrated stack (Django 5.2, DRF, Celery, React 18, TypeScript 5).
