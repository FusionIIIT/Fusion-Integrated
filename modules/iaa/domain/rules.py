"""IAA BR-001..504: terminology and pure submission/routing validation."""

from datetime import timedelta
from decimal import Decimal
from enum import StrEnum


class Role(StrEnum):
    BASIC = "Basic User"
    FINANCE = "Finance Staff"
    HOD = "HoD"
    DEAN = "Dean"
    DIRECTOR = "Director"
    AUDITOR = "Auditor"
    ADMIN = "System Admin"


AUTHORITIES = frozenset({Role.HOD, Role.DEAN, Role.DIRECTOR})
REPORTERS = AUTHORITIES | {Role.FINANCE, Role.AUDITOR}
OPERATORS = REPORTERS | {Role.BASIC}


class State(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    QUERY_RAISED = "query_raised"
    QUERY_RESPONDED = "query_responded"
    FINANCE_VALIDATED = "finance_validated"
    APPROVAL_PENDING = "approval_pending"
    VERIFIED = "verified"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    RECORDED = "recorded"


STATE_CHOICES = [(s.value, s.value) for s in State]


REVIEWABLE = frozenset({State.SUBMITTED, State.QUERY_RESPONDED})
DECIDABLE = frozenset({State.FINANCE_VALIDATED, State.APPROVAL_PENDING, State.ESCALATED})
TERMINAL = frozenset({State.RECORDED, State.REJECTED})


def missing_submission(record, *, require_documents=True):
    """IAA-BR-101: an incomplete expense draft is valid, submission is not."""
    missing = [
        key
        for key in ("request_type", "department", "description")
        if not getattr(record, key, "").strip()
    ]
    if record.amount is None or record.amount <= Decimal(0):
        missing.append("amount")
    if require_documents and not record.documents:
        missing.append("documents")
    if record.kind == "ta":
        if not record.trip_start:
            missing.append("trip_start")
        if not record.trip_end:
            missing.append("trip_end")
        if record.trip_start and record.trip_end and record.trip_end < record.trip_start:
            missing.append("trip_end_before_start")
    return missing


def eligible_steps(steps, creator_id):
    """IAA-BR-001/002: creator steps are bypassed, never self-sanctioned."""
    return [dict(step) for step in steps if step["user_id"] != creator_id]


def overdue(assigned_at, timeout_hours, now):
    """IAA-BR-401: only authority actions use approval timeouts."""
    return assigned_at is not None and now > assigned_at + timedelta(hours=timeout_hours)
