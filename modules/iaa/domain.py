"""Pure rules for the expense/voucher lifecycle (CW-IAA-01: BW-IAA-01 and BW-IAA-03).

No Django or DRF here; services.py turns RuleViolation into an HTTP 422.
"""
from decimal import Decimal

DRAFT = "draft"
SUBMITTED = "submitted"
FINANCE_VALIDATED = "finance_validated"
APPROVED = "approved"
REJECTED = "rejected"
RECORDED = "recorded"

STATUS_CHOICES = [
    (DRAFT, "Draft"),
    (SUBMITTED, "Submitted"),
    (FINANCE_VALIDATED, "Finance Validated"),
    (APPROVED, "Approved"),
    (REJECTED, "Rejected"),
    (RECORDED, "Recorded"),
]

APPROVE = "approve"
REJECT = "reject"
DECISIONS = {APPROVE: APPROVED, REJECT: REJECTED}


class RuleViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def check_status(current: str, expected: str, action: str) -> None:
    """BW-IAA-01 / BW-IAA-03 state-transition tables: each step has one From State."""
    if current != expected:
        raise RuleViolation(
            "invalid_transition",
            f"BW-IAA-01: cannot {action} a request that is '{current}' "
            f"(it must be '{expected}').")


def check_editable(status: str) -> None:
    """IAA-BR-104: a request is locked against creator edits once submitted."""
    if status != DRAFT:
        raise RuleViolation(
            "request_locked", "IAA-BR-104: only a Draft request can be edited.")


def check_submission_complete(purpose: str, amount: Decimal | None,
                              department: str) -> None:
    """IAA-BR-101: a Draft may be incomplete, a formal submission may not."""
    missing = []
    if not (purpose or "").strip():
        missing.append("purpose")
    if not (department or "").strip():
        missing.append("department")
    if amount is None or amount <= 0:
        missing.append("amount (greater than zero)")
    if missing:
        raise RuleViolation(
            "incomplete_submission",
            "IAA-BR-101: required before submission: " + ", ".join(missing) + ".")


def check_not_self_approval(creator_user_id: int, approver_user_id: int) -> None:
    """IAA-BR-001: the creator must not approve or reject their own request."""
    if creator_user_id == approver_user_id:
        raise RuleViolation(
            "segregation_of_duties",
            "IAA-BR-001: you cannot decide on a request you created.")


def check_remarks(remarks: str) -> None:
    """IAA-BR-005: every approval or rejection must carry remarks."""
    if not (remarks or "").strip():
        raise RuleViolation(
            "remarks_required", "IAA-BR-005: remarks are required for a decision.")


def status_after_decision(decision: str) -> str:
    """IAA-UC-201: approve leads to Approved (BW-IAA-01), reject to Rejected (BW-IAA-03)."""
    if decision not in DECISIONS:
        raise RuleViolation(
            "invalid_decision", "IAA-UC-201: decision must be 'approve' or 'reject'.")
    return DECISIONS[decision]
