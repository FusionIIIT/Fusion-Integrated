# SPACS Blueprint — Module 4: Awards and Scholarships

> **Module Name**: Awards and Scholarships (`spacs`)  
> **Environment**: `module-only`  
> **Author**: Manvendra Singh (`24BCS145`)  
> **Reviewer & Approver**: Kasu Karunya Reddy (`24BCS116`)  
> **Date of Approval**: 2026-11-16  

---

## 3.1 Traceability Matrix

Every live specification item from `4-Awards and Scholarships` mapped to its architectural layer and enforcing code unit:

| Id | What it requires | Layer it belongs in | Enforcement point | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `BR-SPACS-001` | CPI and family income eligibility criteria must be satisfied | `domain/` | `rules.py:validate_eligibility` | Pure function checked in service submission |
| `BR-SPACS-002` | No duplicate active applications per cycle | `domain/` | `rules.py:check_no_duplicate` | Checked against existing application states |
| `BR-SPACS-003` | Valid supporting document reuse | `domain/` | `rules.py:validate_document_reuse` | Validates document ownership and expiry date |
| `BR-SPACS-004` | Application completeness (mandatory fields & docs) | `domain/` | `rules.py:validate_completeness` | Ensures mandatory fields & documents are present |
| `BR-SPACS-005` | Review access restricted to staff roles | `domain/` | `rules.py:check_application_review_access` | Guards assistant and convener review queues |
| `BR-SPACS-006` | Assistant verification is not final sanction | `domain/` | `rules.py:assert_assistant_action_permitted` | Assistants can only verify, defect, or flag concern |
| `BR-SPACS-007` | Draft preservation across partial saves | `domain/` | `rules.py:preserve_draft_payload` | Merges incoming updates without dropping data |
| `BR-SPACS-008` | Notification on significant status change | `domain/` | `rules.py:should_notify_event` | Triggers notifications for key lifecycle events |
| `BR-SPACS-009` | Withdrawal allowed before final decision | `domain/` | `rules.py:validate_can_withdraw` | Blocks withdrawal after approval or convener lock |
| `BR-SPACS-010` | Owner-only draft modification and withdrawal | `domain/` | `rules.py:assert_ownership` | Prevents students altering other students' records |
| `BR-SPACS-011` | Defect correction and revalidation | `domain/` | `rules.py:validate_can_modify` | Only allows edits in draft or correction_required |
| `BR-SPACS-012` | Export and download access control | `domain/` | `rules.py:validate_download_access` | Owner or staff only |
| `BR-SPACS-013` | SLA review monitoring and escalation | `domain/` | `rules.py:is_sla_breached` | Evaluates elapsed hours against SLA limit (48h) |
| `BR-SPACS-014` | Published catalogue version is authoritative source | `domain/` | `rules.py:validate_catalogue_published_and_open` | Requires published status and open window |
| `BR-SPACS-015` | Catalogue publication requires approved policy | `domain/` | `rules.py:validate_catalogue_publication_prerequisites` | Policy approval ref and effective dates mandatory |
| `BR-SPACS-016` | Document authenticity verification recorded | `domain/` | `rules.py:validate_document_verification_recording` | Notes and authenticity check required |
| `BR-SPACS-017` | Renewal uses scheme rules & fresh verification | `domain/` | `rules.py:validate_renewal_conditions` | Requires prior approval; never auto-approves |
| `BR-SPACS-018` | Scholarship sanction authority reserved to Convener | `domain/` | `rules.py:assert_decision_authority` | Only spacs_convener / admin can approve/reject |
| `BR-SPACS-019` | Award evaluation & approval follows award policy | `domain/` | `rules.py:validate_award_publication_allowed` | Ready state & approval evidence required |
| `BR-SPACS-020` | Award criteria versioning | `domain/` | `rules.py:validate_award_criteria_version` | Increments version on criteria amendment |
| `BR-SPACS-021` | Audit records protected and restricted | `domain/` | `models:SpacsAuditLog.save/delete` | Immutable audit log table, raises error on mutation |
| `BR-SPACS-022` | Role reassignment preserves task creation history | `domain/` | `rules.py:filter_reassignable_tasks` | Reassigns only pending tasks; preserves creator |
| `BR-SPACS-023` | Award candidate sourcing method is scheme-specific | `domain/` | `rules.py:filter_eligible_candidates` | Filters candidates by system pool or application |
| `AFR-SPACS-001` | Scheme catalogue browsing | `selectors/` | `visible_catalogue` | Returns active published schemes |
| `AFR-SPACS-003` | Draft catalogue entry creation | `services/` | `catalogue.py:create_catalogue_entry` | Draft entry with criteria |
| `AFR-SPACS-004` | Update catalogue criteria & increment version | `services/` | `catalogue.py:update_draft_catalogue_entry` | Criteria amendment logic |
| `AFR-SPACS-005` | Publish catalogue version with provenance | `services/` | `catalogue.py:publish_catalogue_version` | Validates policy ref, marks published |
| `AFR-SPACS-006` | Retire catalogue entry prospectively | `services/` | `catalogue.py:retire_catalogue_entry` | Marks entry retired |
| `AFR-SPACS-007` | Catalogue version history preservation | `models/` | `SpacsCatalogueVersion` | Immutable version records |
| `AFR-SPACS-008` | Initiate scholarship application draft | `services/` | `applications.py:create_draft_application` | Creates draft application record |
| `AFR-SPACS-009` | Submit completed application | `services/` | `applications.py:submit_application` | Validates eligibility & transitions state |
| `AFR-SPACS-012` | Upload supporting documents | `services/` | `applications.py:upload_document` | Stores document link and validity date |
| `AFR-SPACS-013` | Reuse valid supporting documents | `services/` | `applications.py:reuse_prior_document` | Validates ownership & expiry |
| `AFR-SPACS-016` | Application ID generation | `services/` | `applications.py:create_draft_application` | Uses format `SPACS-APP-<UUID>` |
| `AFR-SPACS-017` | Route verification task to assistant | `services/` | `applications.py:submit_application` | Creates `SpacsTask(task_type='verification')` |
| `AFR-SPACS-018` | Submission notifications | `services/` | `applications.py:submit_application` | Dispatches notifications to student & assistant |
| `AFR-SPACS-019` | Assistant opens application for verification | `services/` | `verification.py:open_verification_task` | Transitions to `under_verification` |
| `AFR-SPACS-020` | Record verification checklist & findings | `services/` | `verification.py:record_verification_findings` | Updates verification notes |
| `AFR-SPACS-021` | Request correction for defect | `services/` | `verification.py:request_correction` | Transitions to `correction_required` |
| `AFR-SPACS-022` | Modify flagged fields during correction | `services/` | `applications.py:modify_application_in_correction` | Updates only editable fields |
| `AFR-SPACS-023` | Resubmit corrected application | `services/` | `applications.py:resubmit_application` | Transitions to `resubmitted` |
| `AFR-SPACS-024` | Mark application verified | `services/` | `verification.py:mark_verified` | Transitions to `verified` & creates Convener task |
| `AFR-SPACS-025` | Record verification concern | `services/` | `verification.py:record_verification_concern` | Transitions to `verification_concern` |
| `AFR-SPACS-026` | SLA monitoring and escalation | `services/` | `tasks.py:check_and_escalate_sla_tasks` | Queries aged tasks and notifies staff |
| `AFR-SPACS-027` | Open application for Convener decision | `services/` | `decisions.py:open_convener_decision` | Transitions to `under_convener_decision` |
| `AFR-SPACS-028` | Approve scholarship application | `services/` | `decisions.py:approve_application` | Transitions to `approved` |
| `AFR-SPACS-029` | Reject scholarship application | `services/` | `decisions.py:reject_application` | Transitions to `rejected` with mandatory reason |
| `AFR-SPACS-033` | Withdraw application | `services/` | `applications.py:withdraw_application` | Transitions to `withdrawn` |
| `AFR-SPACS-036` | Export application summary | `services/` | `applications.py:export_application` | Exports application metadata |
| `AFR-SPACS-037` | Initiate scholarship renewal | `services/` | `renewals.py:initiate_renewal` | Prefills prior application data |
| `AFR-SPACS-039` | Submit scholarship renewal | `services/` | `renewals.py:submit_renewal` | Validates criteria and creates assistant task |
| `AFR-SPACS-041` | Renewal window notification reminders | `services/` | `renewals.py:send_renewal_reminders` | Dispatches reminders to prior beneficiaries |
| `AFR-SPACS-042` | Open convocation award cycle | `services/` | `awards.py:open_award_cycle` | Creates `SpacsAwardCycle` in state `open` |
| `AFR-SPACS-043` | Prepare candidate pool | `services/` | `awards.py:prepare_candidate_pool` | Filters eligible students into candidate pool |
| `AFR-SPACS-044` | Record committee evaluation results | `services/` | `awards.py:record_committee_results` | Updates candidate scores & recommendations |
| `AFR-SPACS-045` | Record institutional approval reference | `services/` | `awards.py:record_final_award_outcome` | Transitions to `ready_for_publication` |
| `AFR-SPACS-046` | Publish award outcomes | `services/` | `awards.py:publish_award_results` | Marks cycle `published` and dispatches notifications |
| `AFR-SPACS-050` | Audit trail inspection restricted | `selectors/` | `get_audit_trail_for_auditor` | Access restricted to Convener/Admin |
| `AFR-SPACS-052` | Assistant task reassignment | `services/` | `tasks.py:reassign_role_tasks` | Reallocates pending tasks |

---

## 3.2 Domain Model

All business tables are managed in PostgreSQL under the `fusion_integrated` database. No authentication or authorization tables are stored in the module; all identity and role claims are verified via the IAM session token.

### Entities and Invariants

1. **`SpacsCatalogueEntry`** (`spacs_catalogue_entry`)
   - `scheme_code`: `CharField(max_length=64, unique=True)`
   - `name`: `CharField(max_length=255)`
   - `scheme_type`: `CharField(choices=['scholarship', 'award', 'financial_aid'])`
   - `status`: `CharField(choices=['draft', 'published', 'retired'], default='draft')`
   - `version`: `PositiveIntegerField(default=1)`
   - `min_cpi`: `DecimalField(max_digits=4, decimal_places=2, default=0.0)`
   - `max_family_income`: `DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)`
   - `application_window_start`: `DateTimeField(null=True, blank=True)`
   - `application_window_end`: `DateTimeField(null=True, blank=True)`
   - `renewal_allowed`: `BooleanField(default=False)`
   - `renewal_window_start`: `DateTimeField(null=True, blank=True)`
   - `renewal_window_end`: `DateTimeField(null=True, blank=True)`
   - *Database Invariant*: Unique `scheme_code`.

2. **`SpacsCatalogueVersion`** (`spacs_catalogue_version`)
   - `catalogue_entry`: `ForeignKey(SpacsCatalogueEntry, on_delete=CASCADE, related_name='versions')`
   - `version`: `PositiveIntegerField()`
   - `policy_approval_ref`: `CharField(max_length=128)`
   - `effective_from`: `DateField()`
   - `effective_to`: `DateField(null=True, blank=True)`
   - *Database Invariant*: `unique_together = ('catalogue_entry', 'version')`.

3. **`SpacsApplication`** (`spacs_application`)
   - `application_id`: `CharField(max_length=64, unique=True)`
   - `catalogue_entry`: `ForeignKey(SpacsCatalogueEntry, on_delete=PROTECT)`
   - `catalogue_version`: `PositiveIntegerField(default=1)`
   - `applicant_user_id`: `IntegerField(db_index=True)`
   - `academic_cycle`: `CharField(max_length=32)`
   - `state`: `CharField(max_length=32, default='draft')`
   - `is_renewal`: `BooleanField(default=False)`
   - `parent_application`: `ForeignKey('self', null=True, blank=True, on_delete=SET_NULL)`
   - `cpi`: `DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)`
   - `family_income`: `DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)`
   - `application_data`: `JSONField(default=dict)`
   - *Concurrency Guard*: Optimistic row locking via version/timestamps; state transitions guarded by state machine.

4. **`SpacsDocument`** (`spacs_document`)
   - `application`: `ForeignKey(SpacsApplication, on_delete=CASCADE, related_name='documents')`
   - `user_id`: `IntegerField(db_index=True)`
   - `document_type`: `CharField(max_length=64)`
   - `file_path`: `CharField(max_length=512)`
   - `valid_until`: `DateField(null=True, blank=True)`
   - `is_verified`: `BooleanField(default=False)`

5. **`SpacsAwardCycle`** (`spacs_award_cycle`)
   - `scheme_code`: `CharField(max_length=64)`
   - `academic_cycle`: `CharField(max_length=32)`
   - `state`: `CharField(max_length=32, default='open')`
   - `convener_user_id`: `IntegerField()`
   - `approval_evidence`: `CharField(max_length=255, blank=True, default='')`
   - *Database Invariant*: `unique_together = ('scheme_code', 'academic_cycle')`.

6. **`SpacsAwardCandidate`** (`spacs_award_candidate`)
   - `award_cycle`: `ForeignKey(SpacsAwardCycle, on_delete=CASCADE, related_name='candidates')`
   - `student_user_id`: `IntegerField(db_index=True)`
   - `cpi`: `DecimalField(max_digits=4, decimal_places=2, default=0.0)`
   - `academic_standing`: `CharField(max_length=64, default='good')`
   - `shortlisted`: `BooleanField(default=False)`
   - `evaluation_score`: `DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)`
   - *Database Invariant*: `unique_together = ('award_cycle', 'student_user_id')`.

7. **`SpacsTask`** (`spacs_task`)
   - `task_type`: `CharField(max_length=64)`
   - `entity_type`: `CharField(max_length=64)`
   - `entity_id`: `CharField(max_length=64, db_index=True)`
   - `assigned_role`: `CharField(max_length=64)`
   - `assigned_user_id`: `IntegerField(null=True, blank=True, db_index=True)`
   - `status`: `CharField(choices=['pending', 'in_progress', 'completed', 'cancelled'])`

8. **`SpacsNotification`** (`spacs_notification`)
   - `recipient_user_id`: `IntegerField(db_index=True)`
   - `event_type`: `CharField(max_length=64)`
   - `title`: `CharField(max_length=255)`
   - `message`: `TextField()`
   - `is_read`: `BooleanField(default=False)`

9. **`SpacsAuditLog`** (`spacs_audit_log`)
   - `event_type`: `CharField(max_length=64)`
   - `entity_type`: `CharField(max_length=64)`
   - `entity_id`: `CharField(max_length=64)`
   - `actor_user_id`: `IntegerField()`
   - `details`: `JSONField(default=dict)`
   - `timestamp`: `DateTimeField(default=timezone.now)`
   - *Database Protection*: Overridden `save()` and `delete()` methods prevent modification or deletion (BR-SPACS-021).

---

## 3.3 State Machine

Declarative state transitions implemented in `modules/spacs/domain/state_machine.py`. Illegal transitions cannot be triggered.

### Application Lifecycle

```
[DRAFT]
   │  submit (student)
   ▼
[SUBMITTED]
   │  open_verification (spacs_assistant)
   ▼
[UNDER_VERIFICATION]
   ├── request_correction (spacs_assistant) ──▶ [CORRECTION_REQUIRED]
   │                                                    │ resubmit (student)
   │                                                    ▼
   │                                             [RESUBMITTED]
   │                                                    │ open_verification
   │                                                    ▼
   │                                             [UNDER_VERIFICATION]
   ├── record_concern (spacs_assistant) ────────▶ [VERIFICATION_CONCERN]
   │                                                    │ open_decision (convener)
   │                                                    ▼
   │                                             [UNDER_CONVENER_DECISION]
   └── mark_verified (spacs_assistant) ─────────▶ [VERIFIED]
                                                        │ open_decision (convener)
                                                        ▼
                                                 [UNDER_CONVENER_DECISION]
                                                        ├── approve (convener) ──▶ [APPROVED]
                                                        ├── reject (convener)  ──▶ [REJECTED]
                                                        └── defect (convener)  ──▶ [CORRECTION_REQUIRED]
```

*Withdrawal*: At any point in `draft`, `submitted`, `under_verification`, `resubmitted`, or `correction_required`, the student owner may execute `withdraw` → `[WITHDRAWN]`.

### Convocation Award Cycle

```
[OPEN] ──▶ pool_prepare (convener) ──▶ [POOL_PREPARED] ──▶ evaluate (committee) ──▶ [UNDER_COMMITTEE_EVALUATION]
                                                                                               │
                                                                                        record_results
                                                                                               ▼
[PUBLISHED] ◀── publish (convener) ◀── [READY_FOR_PUBLICATION] ◀── approve ◀── [COMMITTEE_RESULT_RECORDED]
                                                                        (immediate or pending)
```

---

## 3.4 Permissions & Access Control

Defined in `modules/spacs/registry.py` and synced to `registry/permissions.json`:

```python
MODULE = "spacs"

PERMISSIONS = (
    "spacs.scheme.view",
    "spacs.scheme.create",
    "spacs.scheme.update",
    "spacs.scheme.retire",
    "spacs.application.create",
    "spacs.application.view",
    "spacs.application.update",
    "spacs.application.review",
    "spacs.decision.record",
    "spacs.award.create",
    "spacs.award.view",
    "spacs.award.publish",
    "spacs.award.export",
    "spacs.cycle.publish",
    "spacs.task.reassign",
    "spacs.audit.view",
)

ROLE_GRANTS = {
    "student": (
        "spacs.scheme.view",
        "spacs.application.create",
        "spacs.application.view",
        "spacs.application.update",
        "spacs.award.view",
    ),
    "faculty": (
        "spacs.scheme.view",
        "spacs.award.view",
    ),
    "spacs_assistant": (
        "spacs.scheme.view",
        "spacs.application.view",
        "spacs.application.review",
        "spacs.award.view",
    ),
    "spacs_convener": (
        "spacs.scheme.view",
        "spacs.scheme.create",
        "spacs.scheme.update",
        "spacs.scheme.retire",
        "spacs.application.view",
        "spacs.decision.record",
        "spacs.award.create",
        "spacs.award.view",
        "spacs.award.publish",
        "spacs.award.export",
        "spacs.cycle.publish",
        "spacs.task.reassign",
        "spacs.audit.view",
    ),
    "spacs_committee_member": (
        "spacs.scheme.view",
        "spacs.award.view",
        "spacs.award.create",
    ),
    "admin": PERMISSIONS,
}
```

---

## 3.5 API Endpoints & Client Routes

### REST Endpoints

| Path | Method | Permission | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/spacs/schemes` | GET | `spacs.scheme.view` | List published schemes |
| `/api/v1/spacs/schemes` | POST | `spacs.scheme.create` | Create new scheme draft |
| `/api/v1/spacs/schemes/<pk>` | GET | `spacs.scheme.view` | Scheme detail |
| `/api/v1/spacs/schemes/<pk>` | PATCH | `spacs.scheme.update` | Update scheme criteria |
| `/api/v1/spacs/cycles` | GET | `spacs.scheme.view` | List award cycles |
| `/api/v1/spacs/cycles/<pk>/publish` | POST | `spacs.cycle.publish` | Publish award cycle results |
| `/api/v1/spacs/applications` | GET | `spacs.application.view` | List user or scoped applications |
| `/api/v1/spacs/applications` | POST | `spacs.application.create` | Create application draft |
| `/api/v1/spacs/applications/<pk>` | GET | `spacs.application.view` | Application detail |
| `/api/v1/spacs/applications/<pk>/withdraw` | POST | `spacs.application.update` | Withdraw active application |
| `/api/v1/spacs/verifications` | GET | `spacs.application.review` | Assistant verification queue |
| `/api/v1/spacs/verifications/<pk>/action` | POST | `spacs.application.review` | Perform verification action |
| `/api/v1/spacs/decisions/action` | POST | `spacs.decision.record` | Record Convener approval/rejection |
| `/api/v1/spacs/renewals` | GET/POST | `spacs.application.create` | List and submit renewals |
| `/api/v1/spacs/awards` | GET/POST | `spacs.award.create` | Manage award candidates |
| `/api/v1/spacs/awards/publish` | POST | `spacs.award.publish` | Announce award outcomes |
| `/api/v1/spacs/awards/export` | GET | `spacs.award.export` | Export awards data |
| `/api/v1/spacs/audit` | GET | `spacs.audit.view` | View audit trail records |

### Frontend Pages

| URL Route | Page Component | Access Guard |
| :--- | :--- | :--- |
| `/spacs/opportunities` | `OpportunitiesPage.tsx` | All authenticated users |
| `/spacs/my-applications` | `MyApplicationsPage.tsx` | `student` role |
| `/spacs/verification-queue` | `VerificationQueuePage.tsx` | `spacs_assistant`, `admin` |
| `/spacs/decisions` | `DecisionsPage.tsx` | `spacs_convener`, `admin` |
| `/spacs/convocation-awards` | `ConvocationAwardsPage.tsx` | `spacs_convener`, `spacs_committee_member` |

---

## 3.6 Contracts & Cross-Module Boundaries

Cross-module communication complies strictly with `.importlinter` layering contracts.

1. **`contracts.py`**
   - Outgoing services provided to other modules:
     - `get_student_scholarships(student_user_id)`: returns active scholarship grants.
     - `get_active_award_recipients(academic_cycle)`: returns published award winners.
   - Incoming queries: None required; directory and user roles resolved through IAM token principal.

---

## 3.7 Scheduled Work & Celery Tasks

1. **`check_sla_tasks`** (`modules.spacs.tasks.check_sla_tasks`)
   - **Schedule**: Every 6 hours (`0 */6 * * *`)
   - **Action**: Queries `SpacsTask` instances pending > 48 hours and dispatches SLA reminder notifications to assigned assistants.
2. **`close_expired_cycles`** (`modules.spacs.tasks.close_expired_cycles`)
   - **Schedule**: Daily at midnight (`0 0 * * *`)
   - **Action**: Checks catalogue application and renewal window deadlines and updates cycle statuses accordingly.

---

## 3.8 Open Questions, Deviations & Written Approval

- **Question 1**: Are non-student users eligible to apply for SPACS scholarships?
  - *Resolution*: No. Per spec AFR-SPACS-008 and BR-SPACS-001, scholarships are exclusively for enrolled students. Staff and faculty may only view opportunities and participate in evaluation/administration.
- **Question 2**: Can an assistant approve or reject an application directly?
  - *Resolution*: No. Per BR-SPACS-006 and BR-SPACS-018, verification is evidence-checking only; final sanction authority is reserved strictly to the Convener.

### Written Approval

> "I, Kasu Karunya Reddy (24BCS116), have reviewed this specification blueprint for Module 4 (Awards and Scholarships) against the problem statement, business rules, use cases, and workflow documents. The architecture, domain model, declarative state machine, permission grants, and API routes accurately implement all requirements. I hereby grant written approval for implementation to proceed."  
> — **Kasu Karunya Reddy (`24BCS116`), Approver & Spec Tester**  
> *Date*: 2026-11-16
