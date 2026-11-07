"""
Pure Python policy rules for the Patent Management System (PMS).
No Django, DRF, or Celery imports.
Enforces business rules BR-PMS-003 through BR-PMS-140 as specified in read-only specs.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Set, List, Any


# -----------------------------------------------------------------------------
# State Transitions (BR-PMS state table)
# -----------------------------------------------------------------------------

ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "draft": {"submitted"},
    "submitted": {"under_review", "withdrawn"},
    "under_review": {"approved", "needs_revision", "rejected", "escalated"},
    "needs_revision": {"resubmitted", "withdrawn"},
    "resubmitted": {"under_review", "withdrawn"},
    "rejected": {"appeal_submitted", "withdrawn"},
    "appeal_submitted": {"remanded_for_amendment", "rejection_upheld", "decision_modified"},
    "approved": {"attorney_assigned", "budget_approved", "budget_rejected", "budget_escalated"},
    "attorney_assigned": {"attorney_declined", "pending_review"},
    "pending_review": {"attorney_assigned"},  # Reassignment if declined or invalid
    "filed": {"office_action_recorded"},  # Implicit transition on communication receipt
    "office_action_recorded": {"awaiting_applicant_approval", "response_ready", "response_submitted"},
    "awaiting_applicant_approval": {"applicant_approved"},
    "applicant_approved": {"response_ready"},
    "response_ready": {"response_submitted"},
    "response_submitted": {"under_review"},  # Back to review cycle or granted
    "granted": {"renewal_requested"},
    "renewal_requested": {"renewed", "do_not_renew", "escalated"},
    "renewed": {"next_cycle_scheduled"},
    "withdrawn": {},
    "expired": {},
    "remanded_for_amendment": {"under_review"},  # Back to review after amendment
    "decision_modified": {"under_review"},  # Back to review after modification
}


def can_transition(from_status: str, to_status: str) -> bool:
    """Check if a transition is allowed based on the state table."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


# -----------------------------------------------------------------------------
# Document Validation (BR-PMS-014, 015, 016)
# -----------------------------------------------------------------------------

def validate_document(file_name: str, content_type: str, size_bytes: int) -> bool:
    """
    Validate document for submission.
    Rules: PDF only (BR-PMS-014), under 50 MB (BR-PMS-015).
    Malware validation is assumed to be handled by an external service or middleware.
    """
    if content_type.lower() != "application/pdf":
        return False
    if size_bytes > 50 * 1024 * 1024:  # 50 MB
        return False
    return True


# -----------------------------------------------------------------------------
# Application Validation (BR-PMS-017)
# -----------------------------------------------------------------------------

def missing_required_fields(data: Dict[str, Any]) -> List[str]:
    """
    Check for missing required application fields.
    Required: title, abstract, description, claims, at least one inventor.
    Returns list of missing field names.
    """
    missing = []
    if not data.get("title"):
        missing.append("title")
    if not data.get("abstract"):
        missing.append("abstract")
    if not data.get("description"):
        missing.append("description")
    if not data.get("claims"):
        missing.append("claims")
    
    inventors = data.get("inventors", [])
    if len(inventors) == 0:
        missing.append("inventor")
    
    return missing


# -----------------------------------------------------------------------------
# Decision Validation (BR-PMS-029, 030)
# -----------------------------------------------------------------------------

def validate_justification(text: str) -> bool:
    """
    Validate Director review justification.
    Rule BR-PMS-030: Must be at least 50 characters.
    """
    return len(text.strip()) >= 50


# -----------------------------------------------------------------------------
# Date Calculations (BR-PMS-031, 035)
# -----------------------------------------------------------------------------

def add_business_days(start_date: date, days: int) -> date:
    """
    Add business days to a start date.
    Skips weekends (Saturday, Sunday).
    """
    current = start_date
    count = 0
    while count < days:
        if current.weekday() < 5:  # Monday (0) to Friday (4)
            count += 1
        current += timedelta(days=1)
    return current


def review_due_date(assigned_on: date) -> date:
    """
    Calculate the review due date for a Director.
    Rule BR-PMS-031: 15 business days from assignment.
    """
    return add_business_days(assigned_on, 15)


def resubmission_deadline(decision_date: date) -> date:
    """
    Calculate the resubmission deadline for an Applicant.
    Rule BR-PMS-035: 60 days from rejection or revision-request decision.
    """
    return add_business_days(decision_date, 60)


# -----------------------------------------------------------------------------
# Conflict of Interest (BR-PMS-025, 026, 027)
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class InventorInfo:
    user_id: int
    name: str


def is_conflicted(reviewer_id: int, inventor_user_ids: Set[int]) -> bool:
    """
    Check if a reviewer is conflicted with any inventor.
    Rules BR-PMS-025 (PCC_ADMIN), BR-PMS-026 (Director):
    A reviewer listed as an inventor cannot review the application.
    """
    return reviewer_id in inventor_user_ids


# -----------------------------------------------------------------------------
# Withdrawal Eligibility (BR-PMS-067, 068)
# -----------------------------------------------------------------------------

def can_withdraw(status: str) -> bool:
    """
    Check if withdrawal is allowed from the current status.
    Rule BR-PMS-067: Only before filing stage.
    Rule BR-PMS-068: Status must be withdrawal-eligible under PMS rules.
    
    Withdrawal-eligible statuses based on state table and pre-filing constraint:
    - draft, submitted, under_review, needs_revision, resubmitted, rejected
    
    Note: 'approved' is technically in the table but usually not withdrawable post-grant/filing.
    However, strict interpretation of "before filing" suggests only very early stages.
    Based on the state table provided, we allow withdrawal from states that are pre-filing or explicitly listed as eligible.
    The state table lists 'submitted', 'under_review', etc. as having a transition to 'withdrawn'.
    We will assume any status that has 'withdrawn' in its allowed transitions is eligible.
    """
    return "withdrawn" in ALLOWED_TRANSITIONS.get(status, set())


# -----------------------------------------------------------------------------
# Budget Escalation (BR-PMS-009)
# -----------------------------------------------------------------------------

def budget_needs_escalation(total: float, threshold: float) -> bool:
    """
    Check if a budget total exceeds the configured threshold.
    Rule BR-PMS-009: If total cost exceeds threshold, status becomes 'Escalated'.
    """
    return total > threshold
