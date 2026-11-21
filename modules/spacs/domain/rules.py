"""Pure business rules for Awards and Scholarships (BR-SPACS-001 through BR-SPACS-023). Pure Python."""

from datetime import date, datetime
from typing import Any, Iterable

from .errors import (
    AuditProtectionError,
    AwardPolicyError,
    CompletenessError,
    DocumentReuseError,
    DuplicateApplicationError,
    EligibilityError,
    RenewalEligibilityError,
    UnauthorizedActionError,
)
from .state_machine import (
    EDITABLE_APPLICATION_STATES,
    READY_FOR_PUBLICATION,
    TERMINAL_APPLICATION_STATES,
    WITHDRAWABLE_STATES,
)


# BR-SPACS-001: Eligibility Must Be Satisfied
def validate_eligibility(
    student_cpi: float,
    student_family_income: float | None,
    min_cpi: float = 0.0,
    max_family_income: float | None = None,
    active_backlogs: int = 0,
    max_backlogs: int = 0,
) -> None:
    if student_cpi < min_cpi:
        raise EligibilityError(
            f"CPI {student_cpi:.2f} is below the required minimum of {min_cpi:.2f}."
        )
    if max_family_income is not None and student_family_income is not None:
        if student_family_income > max_family_income:
            raise EligibilityError(
                f"Family income ₹{student_family_income:.2f} exceeds maximum threshold ₹{max_family_income:.2f}."
            )
    if active_backlogs > max_backlogs:
        raise EligibilityError(
            f"Active backlogs ({active_backlogs}) exceed maximum allowed ({max_backlogs})."
        )


# BR-SPACS-002: No Duplicate Applications
def check_no_duplicate(
    existing_applications_states: Iterable[str],
    allow_resubmission_on_terminal: bool = True,
) -> None:
    for state in existing_applications_states:
        if state not in {"withdrawn", "rejected"}:
            raise DuplicateApplicationError(
                f"An active application already exists in state '{state}'. Only one active application is permitted per cycle."
            )


# BR-SPACS-003: Reuse of Previously Uploaded Documents
def validate_document_reuse(
    doc_user_id: int,
    applicant_user_id: int,
    doc_type: str,
    required_doc_type: str,
    doc_valid_until: date | None = None,
    reference_date: date | None = None,
) -> None:
    if doc_user_id != applicant_user_id:
        raise DocumentReuseError("Cannot reuse a document belonging to another user.")
    if doc_type != required_doc_type:
        raise DocumentReuseError(
            f"Document type '{doc_type}' does not match required type '{required_doc_type}'."
        )
    if doc_valid_until is not None:
        ref = reference_date or date.today()
        if doc_valid_until < ref:
            raise DocumentReuseError(
                f"Document expired on {doc_valid_until.isoformat()}; cannot be reused."
            )


# BR-SPACS-004: Application Completeness
def validate_completeness(
    application_data: dict[str, Any],
    mandatory_fields: Iterable[str],
    uploaded_doc_types: Iterable[str],
    required_doc_types: Iterable[str],
) -> None:
    missing_fields = [f for f in mandatory_fields if not application_data.get(f)]
    if missing_fields:
        raise CompletenessError(
            f"Mandatory application field(s) missing: {', '.join(missing_fields)}."
        )
    uploaded_set = set(uploaded_doc_types)
    missing_docs = [d for d in required_doc_types if d not in uploaded_set]
    if missing_docs:
        raise CompletenessError(
            f"Required supporting document(s) missing: {', '.join(missing_docs)}."
        )


# BR-SPACS-005: Application Review Access
def check_application_review_access(user_roles: Iterable[str]) -> None:
    allowed_roles = {"spacs_assistant", "spacs_convener", "admin"}
    if not any(r in allowed_roles for r in user_roles):
        raise UnauthorizedActionError(
            "Access denied: only SPACS Assistant or SPACS Convener may review scholarship applications."
        )


# BR-SPACS-006: Verification Is Not Final Sanction
def assert_assistant_action_permitted(action: str) -> None:
    prohibited_assistant_actions = {"approve", "reject", "sanction"}
    if action in prohibited_assistant_actions:
        raise UnauthorizedActionError(
            f"SPACS Assistant cannot perform final sanction action '{action}'."
        )


# BR-SPACS-007: Draft Preservation on Timeout/Error
def preserve_draft_payload(existing_data: dict[str, Any], new_input: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing_data)
    merged.update(new_input)
    return merged


# BR-SPACS-008: Notification on Significant Status Change
SIGNIFICANT_EVENTS = {
    "submitted",
    "correction_required",
    "resubmitted",
    "verified",
    "approved",
    "rejected",
    "withdrawn",
    "renewal_reminder",
    "award_published",
}


def should_notify_event(event_name: str) -> bool:
    return event_name in SIGNIFICANT_EVENTS


# BR-SPACS-009: Withdrawal Before Final Decision
def validate_can_withdraw(current_state: str, convener_review_started: bool = False) -> None:
    if current_state in TERMINAL_APPLICATION_STATES:
        raise UnauthorizedActionError(
            f"Application in terminal state '{current_state}' cannot be withdrawn."
        )
    if current_state not in WITHDRAWABLE_STATES:
        raise UnauthorizedActionError(
            f"Application in state '{current_state}' is not withdrawable."
        )
    if current_state == "verified" and convener_review_started:
        raise UnauthorizedActionError(
            "Application review has already begun by the Convener; withdrawal is locked."
        )


# BR-SPACS-010: Owner-Only Modification/Withdrawal
def assert_ownership(applicant_user_id: int, acting_user_id: int) -> None:
    if applicant_user_id != acting_user_id:
        raise UnauthorizedActionError(
            f"User {acting_user_id} is not the owner of application belonging to user {applicant_user_id}."
        )


# BR-SPACS-011: Correction and Revalidation
def validate_can_modify(current_state: str) -> None:
    if current_state not in EDITABLE_APPLICATION_STATES:
        raise UnauthorizedActionError(
            f"Modification not permitted: application is in state '{current_state}', not editable."
        )


# BR-SPACS-012: Download/Print Access
def validate_download_access(applicant_user_id: int, acting_user_id: int, user_roles: Iterable[str]) -> None:
    if applicant_user_id == acting_user_id:
        return
    allowed_staff_roles = {"spacs_assistant", "spacs_convener", "admin"}
    if not any(r in allowed_staff_roles for r in user_roles):
        raise UnauthorizedActionError(
            "Unauthorized export: students may only export their own applications, and staff must hold an authorized role."
        )


# BR-SPACS-013: Review SLA and Escalation
def is_sla_breached(task_created_at: datetime, sla_hours: int, now: datetime) -> bool:
    elapsed_seconds = (now - task_created_at).total_seconds()
    return elapsed_seconds > (sla_hours * 3600)


# BR-SPACS-014: Published Catalogue Version Is Source of Truth
def validate_catalogue_published_and_open(
    status: str,
    window_start: datetime | None,
    window_end: datetime | None,
    reference_time: datetime,
) -> None:
    if status != "published":
        raise EligibilityError(
            f"Scheme catalogue entry is not active (status: '{status}')."
        )
    if window_start and reference_time < window_start:
        raise EligibilityError("Scheme application window has not yet opened.")
    if window_end and reference_time > window_end:
        raise EligibilityError("Scheme application window is closed.")


# BR-SPACS-015: Catalogue Must Reflect Approved Policy
def validate_catalogue_publication_prerequisites(
    policy_approval_ref: str,
    effective_from: date | None,
    effective_to: date | None = None,
) -> None:
    if not policy_approval_ref or not policy_approval_ref.strip():
        raise AwardPolicyError("Policy approval reference is mandatory for publication.")
    if not effective_from:
        raise AwardPolicyError("Effective start date is mandatory for publication.")
    if effective_to and effective_to < effective_from:
        raise AwardPolicyError("Effective end date cannot precede effective start date.")


# BR-SPACS-016: Document Authenticity Requires Authorized Verification
def validate_document_verification_recording(
    is_authenticity_confirmed: bool,
    findings: str,
) -> None:
    if not findings or not findings.strip():
        raise CompletenessError("Verification findings and notes must be recorded.")


# BR-SPACS-017: Renewal Uses Scheme-Specific Rules and Fresh Decision
def validate_renewal_conditions(
    parent_state: str,
    renewal_allowed: bool,
    renewal_window_start: datetime | None,
    renewal_window_end: datetime | None,
    current_time: datetime,
) -> None:
    if not renewal_allowed:
        raise RenewalEligibilityError("The selected scheme does not permit renewals.")
    if parent_state != "approved":
        raise RenewalEligibilityError(
            f"Only previously approved applications can be renewed (prior state: '{parent_state}')."
        )
    if renewal_window_start and current_time < renewal_window_start:
        raise RenewalEligibilityError("Renewal window has not opened yet.")
    if renewal_window_end and current_time > renewal_window_end:
        raise RenewalEligibilityError("Renewal window has closed.")


# BR-SPACS-018: Scholarship Decision Authority
def assert_decision_authority(user_roles: Iterable[str]) -> None:
    allowed = {"spacs_convener", "admin"}
    if not any(r in allowed for r in user_roles):
        raise UnauthorizedActionError(
            "Access denied: only SPACS Convener may approve or reject scholarship applications."
        )


# BR-SPACS-019: Award Evaluation and Approval Follow Award Policy
def validate_award_publication_allowed(cycle_state: str, approval_evidence: str) -> None:
    if cycle_state != READY_FOR_PUBLICATION:
        raise AwardPolicyError(
            f"Cannot publish award: current state is '{cycle_state}', expected '{READY_FOR_PUBLICATION}'."
        )
    if not approval_evidence or not approval_evidence.strip():
        raise AwardPolicyError(
            "Institutional approval evidence reference is required before publication."
        )


# BR-SPACS-020: Award Criteria Versioning
def validate_award_criteria_version(expected_version: int, candidate_version: int) -> None:
    if expected_version != candidate_version:
        raise AwardPolicyError(
            f"Criteria version mismatch: expected version {expected_version}, got {candidate_version}."
        )


# BR-SPACS-021: Audit Records Protected and Restricted
def assert_audit_modification_prohibited() -> None:
    raise AuditProtectionError(
        "Audit log records are immutable and protected by policy from alteration or deletion."
    )


# BR-SPACS-022: Role Reassignment Preserves History
def filter_reassignable_tasks(tasks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [t for t in tasks if t.get("status") == "pending"]


# BR-SPACS-023: Award Candidate Source Is Scheme-Specific
def filter_eligible_candidates(
    candidates: list[dict[str, Any]],
    source_method: str,
    min_cpi: float = 0.0,
) -> list[dict[str, Any]]:
    if source_method == "system_pool":
        return [c for c in candidates if c.get("cpi", 0.0) >= min_cpi]
    elif source_method in {"application", "nomination"}:
        return [c for c in candidates if c.get("is_submitted", False)]
    return candidates
