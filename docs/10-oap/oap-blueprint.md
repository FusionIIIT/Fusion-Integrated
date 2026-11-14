# Other Academic Procedures (OAP) Module Blueprint

## 1. Executive Summary

The **Other Academic Procedures (OAP)** module implements role-controlled institutional procedures outside core course registration and examinations:
1. **Leave Management** (OA-UC-01..04, BW-OAP-01, BW-OAP-02, CW-OAP-01)
2. **Bonafide Certificate Management** (OA-UC-11..14, BW-OAP-03, BW-OAP-04, CW-OAP-02)
3. **No-Dues Clearance Management** (OA-UC-21..25, BW-OAP-05, BW-OAP-06, CW-OAP-03)
4. **PG Assistantship Claim Management** (OA-UC-31..37, BW-OAP-07, BW-OAP-08, CW-OAP-04)
5. **Supervisor & TA Assignment Recording** (OA-UC-41..42)
6. **Graduate Seminar Management** (OA-UC-51..54, BW-OAP-09)
7. **System Notifications & Pending Action Reminders** (OA-UC-91..92, OA-BR-03)

## 2. Architecture & Layering

Following the Fusion-Integrated strict modular architecture:
- `modules/oap/domain/`: Pure Python (no Django, DRF, or Celery). Houses permission codes, state machines, and business invariant validations.
- `modules/oap/models/`: Django ORM models extending `TimeStampedModel` and `UserScopedModel`. Unconstrained plain `user_id` integer references.
- `modules/oap/selectors/`: Database queries and scoping filters.
- `modules/oap/services/`: State transitions, validations, domain actions, and notification triggers.
- `modules/oap/api/`: Django REST Framework APIViews, DRF serializers, and OpenAPI 3.0 schema definitions with `@extend_schema`.
- `modules/oap/contracts.py`: Strict public interface for cross-module integration.
- `modules/oap/registry.py`: Platform navigation, permission catalog, and designation grants (`ROLE_GRANTS`).

## 3. Workflows & State Machines

### 3.1 Leave Management
- Initial: `submitted_awaiting_hod`
- Transitions:
  - HoD approves $\to$ `approved`
  - HoD rejects $\to$ `rejected`

### 3.2 Bonafide Certificate
- Initial: `submitted_awaiting_academic_administrator`
- Transitions:
  - Academic Administrator approves $\to$ `approved_certificate_available` (generates certificate number)
  - Academic Administrator rejects $\to$ `rejected`
- **Guard (OA-BR-22)**: Certificate download is restricted to approved requests only.

### 3.3 No-Dues Clearance
- Parallel routing to all **7 mandatory institutional authorities**:
  1. Library (Librarian)
  2. Hostel (Hostel Warden)
  3. Mess (Mess In-charge)
  4. Respective Department (Department Verifier)
  5. Lab (Lab Supervisor)
  6. Academic Section (Academic Section Verifier)
  7. Student Section (Student Section Verifier)
- States:
  - `verification_in_progress` (awaiting all 7 results)
  - `verification_complete_dues_outstanding` (all 7 recorded, $\ge 1$ dues outstanding)
  - `verification_complete_all_clear` (all 7 recorded and clear)
  - `finalized_certificate_available` (Academic Administrator finalization confirmed)
- **Guard (OA-BR-33)**: Academic Administrator may finalize only when all 7 clearances are clear.
- **Guard (OA-BR-34)**: Certificate download is restricted to finalized requests.

### 3.4 PG Assistantship Claims
- Sequence (OA-BR-46):
  1. PG student submits claim $\to$ `awaiting_dual_supervisor_verification`
  2. Dual Supervisor Verification: Thesis Supervisor and TA Supervisor verify in either order (OA-BR-42, OA-BR-52):
     - First supervisor verifies $\to$ `awaiting_other_supervisor_verification`
     - Second supervisor verifies $\to$ `awaiting_department_review`
  3. Department Administrator reviews and forwards $\to$ `awaiting_hod_decision` (OA-BR-43)
  4. HoD approves $\to$ `approved_awaiting_stipend_processing` or rejects $\to$ `rejected` (OA-BR-44)
  5. Academic Administrator processes stipend $\to$ `stipend_processed` (OA-BR-45)

### 3.5 Graduate Seminars
- PG student requests seminar $\to$ `awaiting_scheduling`
- Department Administrator schedules seminar $\to$ `scheduled`
- Publicly visible to PG students and faculty (OA-BR-63).

## 4. Permission Taxonomy & Role Grants

| Code | Label | Held by |
|---|---|---|
| `oap.leave.apply` | Apply for student leave | `student` |
| `oap.leave.view` | View own student leave applications | `student` |
| `oap.leave.decide` | Approve/reject student leave | `hod` |
| `oap.leave.view_dept` | View department student leaves | `hod` |
| `oap.bonafide.request` | Request bonafide certificate | `student` |
| `oap.bonafide.view` | View own bonafide requests | `student` |
| `oap.bonafide.download` | Download approved bonafide | `student` |
| `oap.bonafide.decide` | Decide bonafide requests | `acadadmin` |
| `oap.nodues.initiate` | Initiate no-dues clearance | `student` |
| `oap.nodues.view` | Track no-dues progress | `student` |
| `oap.nodues.download` | Download finalized no-dues | `student` |
| `oap.nodues.verify` | Record authority clearance | `clearance_authority` |
| `oap.nodues.finalize` | Finalize no-dues clearance | `acadadmin` |
| `oap.assistantship.submit` | Submit PG assistantship claim | `student` |
| `oap.assistantship.view` | Track assistantship claims | `student` |
| `oap.assistantship.verify_thesis` | Verify claim as Thesis Supervisor | `faculty` |
| `oap.assistantship.verify_ta` | Verify claim as TA Supervisor | `faculty` |
| `oap.assistantship.dept_review` | Review & forward claim | `dept_admin` |
| `oap.assistantship.decide` | Decide claim as HoD | `hod` |
| `oap.assistantship.disburse` | Process stipend disbursement | `acadadmin` |
| `oap.assignment.manage` | Record Thesis and TA assignments | `dept_admin` |
| `oap.seminar.request` | Request graduate seminar | `student` |
| `oap.seminar.schedule` | Schedule graduate seminar | `dept_admin` |
| `oap.seminar.view` | View scheduled graduate seminars | `student`, `faculty`, `hod` |
| `oap.notification.view` | View notifications and alerts | All roles |
