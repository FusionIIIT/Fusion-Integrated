# Patent Management System (PMS) — Domain Model

This document outlines the core domain model, entities, value objects, and business rules governing the Patent Management System (`modules.patents`).

---

## 1. Architectural Principles

1. **Domain Purity**: The domain layer (`modules/patents/domain/`) is strictly pure Python (`.importlinter` enforced). It does not import Django, DRF, Celery, or external dependencies.
2. **Persistence Independence**: Business rules for transitions, deadlines, document constraints, and filing validation are modeled as pure functions and immutable data structures.
3. **Auditability**: Every application transition and ledger expenditure maintains an immutable audit trail (`AuditLogRecord`).

---

## 2. Core Entities & Relationships

### 2.1 PatentApplication
The aggregate root representing an institutional invention disclosure:
* `id`: Unique integer identifier.
* `application_number`: Official or system tracking number (`PMS-YYYY-NNN`).
* `user_id`: Primary inventor / applicant (student, faculty, or staff).
* `title`, `abstract`, `description`, `claims`: Core technical disclosure fields (BR-PMS-017).
* `status`: Current lifecycle state (`PatentApplicationStatus`).
* `domain_category`: Academic or technological domain classification.
* `jurisdiction`: Target patent office jurisdiction (`IN`, `US`, `EP`, `WO`).
* `version`: Monotonically incrementing integer tracking specification revisions (BR-PMS-082..086).
* `filing_date`, `grant_date`, `decision_date`: Milestone dates.

### 2.2 CoInventor
Co-inventors associated with a patent application:
* `application`: ForeignKey to `PatentApplication`.
* `user_id`: Co-inventor user account.
* `role`: Academic/research designation.
* `contribution_percent`: Share of inventive contribution ($\sum = 100\%$, BR-PMS-073..075).
* `consent_status`: Formal consent status (`PENDING`, `GRANTED`, `REFUSED`, BR-PMS-078).

### 2.3 PatentPolicy
Singleton configuration governing institutional patent timelines, thresholds, and withdrawal criteria:
* `director_review_days`: SLA for director evaluation (default: 15 days, BR-PMS-030).
* `revision_resubmission_days`: Revision window before rejection expiry (default: 60 days, BR-PMS-034..038).
* `office_action_response_days`: Default response deadline for examiner actions (BR-PMS-065).
* `cost_escalation_threshold`: Budget limit requiring enhanced approval (BR-PMS-051). Has no default value and is set by the institute through `PatentPolicy` or `pms_seed_policy --threshold`.
* `max_attorney_workload`: Maximum active drafting/prosecution assignments per panel attorney (BR-PMS-043). Has no default value (nullable) and is set by the institute through `PatentPolicy` or `pms_seed_policy --max-workload` (proposed default: 5). When unset, no workload limit is enforced unless configured by policy.
* `withdrawal_eligible_states`: Configurable tuple of states eligible for pre-filing withdrawal (BR-PMS-068).

### 2.4 PatentBudgetLedger
Append-only ledger of financial requests, decisions and reversals (BW-PMS-08..10, R1-08). A row is never updated or deleted. A request is one `REQUEST` row. A decision is a new `APPROVAL` or `ESCALATION` row whose `replaces_entry` points at the request. A correction is a new `REVERSAL` row whose `replaces_entry` points at the approval. Approved spend is derived as approvals minus reversals.
* `application`: ForeignKey to `PatentApplication`.
* `entry_kind`: `REQUEST`, `APPROVAL`, `ESCALATION`, `REVERSAL`, `DISBURSEMENT`.
* `replaces_entry`: nullable self-reference to the request, approval or entry being decided or reversed.
* `entry_type`: Stage category (`FILING`, `PROSECUTION`, `MAINTENANCE`, `LEGAL`).
* `amount`, `currency`: Monetary value.
* `status`: outcome of the row (`PENDING`, `APPROVED`, `REJECTED`, `ESCALATED`, `REVERSED`).
* `authorized_by_user_id`: Authorizing Director ID.

### 2.6 Policy superseding and consent tokens
* `PatentPolicy` is effective-dated. A change ends the current row (`effective_to`, `is_active=False`, `superseded_by` set to the new row) and inserts a new active row. Policy content is never edited in place.
* `CoInventorConsentToken` holds the SHA-256 hash of a one-time consent token for an external co-inventor with no institute account. The applicant requests the token, the system emails it to the co-inventor, and the co-inventor confirms it once within 14 days. The applicant never sees the token.
* Email is sent through Django's configured mail backend. The module does not run its own mail queue.

### 2.5 OfficeActionRecord
Subordinate lifecycle tracking official patent office examination reports (BW-PMS-12..13):
* `application`: ForeignKey to `PatentApplication`.
* `action_code`: Official office action identifier (e.g., `FER`, `OA1`).
* `issuing_authority`: Patent office authority (e.g., `IPO`, `USPTO`).
* `issued_date`, `response_deadline`: Official timeline constraints (BR-PMS-065).
* `status`: `PENDING`, `RESPONDED`, `CLOSED`.
* `requires_applicant_review`: Flag for substantive objection review (BR-PMS-146).

### 2.6 AttorneyPanelMember
Empanelled patent attorney roster:
* `user_id`: Attorney user account.
* `firm_name`: Empanelled IP law firm.
* `expertise_domains`: JSON mapping of technological domain proficiencies (BR-PMS-041..043).
* `active_workload`: Count of active drafting/prosecution assignments.
* `is_approved_panel`: Operational qualification flag.

---

## 3. Data Transfer Objects (DTOs)

The domain exposes dataclasses for layer boundaries:
* `ApplicationDetailDTO`: Full invention disclosure and relations.
* `ApplicationSummaryDTO`: Lightweight queue view.
* `ReviewDecisionDTO`: Technical evaluation outcome and justification.
* `AppealRecordDTO`: Contested rejection appeal and grounds.
* `PriorArtResultDTO`: Retrieved patent references.
* `ReportsSummaryDTO`: Aggregate institutional metrics.
