"""Explicit IAA lifecycle transitions. No monetary policy is hard-coded."""

from dataclasses import dataclass


class WorkflowError(ValueError):
    """Raised when a requested transition is not permitted by the lifecycle."""


EXPENSE_TRANSITIONS = {
    "draft": {"submit": "submitted"},
    "submitted": {"query": "query_raised", "validate": "finance_validated"},
    "query_raised": {"respond": "query_responded"},
    "query_responded": {"query": "query_raised", "validate": "finance_validated"},
    "finance_validated": {"route": "approval_pending"},
    "approval_pending": {"approve": "approved", "reject": "rejected"},
    "approved": {"record": "recorded"},
}

TA_TRANSITIONS = {
    "submitted": {"query": "query_raised", "verify": "verified"},
    "query_raised": {"respond": "query_responded"},
    "query_responded": {"query": "query_raised", "verify": "verified"},
    "verified": {"route": "approval_pending", "record": "recorded"},
    "approval_pending": {"approve": "approved", "reject": "rejected"},
    "approved": {"record": "recorded"},
}

OBSERVATION_TRANSITIONS = {
    "open": {"respond": "responded"},
    "responded": {"close": "closed", "return": "open"},
}

ANOMALY_TRANSITIONS = {
    "open": {"resolve": "resolved", "escalate": "escalated"},
    "escalated": {"resolve": "resolved", "escalate": "escalated"},
}


def transition(table: dict[str, dict[str, str]], current: str, action: str) -> str:
    """Return the next state or fail without mutating the record."""
    try:
        return table[current][action]
    except KeyError as exc:
        raise WorkflowError(f"Action '{action}' is not valid while state is '{current}'.") from exc


@dataclass(frozen=True)
class Completeness:
    complete: bool
    missing: tuple[str, ...]


def expense_completeness(data: dict) -> Completeness:
    required = ("request_type", "amount", "department", "description")
    missing = tuple(name for name in required if not data.get(name))
    if not data.get("documents"):
        missing += ("documents",)
    return Completeness(not missing, missing)


def ta_completeness(data: dict) -> Completeness:
    required = ("trip_start", "trip_end", "purpose", "amount", "department")
    missing = tuple(name for name in required if not data.get(name))
    if not data.get("documents"):
        missing += ("documents",)
    return Completeness(not missing, missing)


def is_high_value(amount, threshold) -> bool:
    """Threshold comparison is inclusive; the configured value is required."""
    if threshold is None:
        raise WorkflowError("The high-value TA threshold is not configured.")
    return amount >= threshold


def approval_eligible(*, creator_id: int, approver_id: int,
                      assigned_role: str, active_role: str) -> bool:
    return creator_id != approver_id and assigned_role == active_role


def satisfactory_observation_response(satisfactory: bool) -> str:
    return "closed" if satisfactory else "open"
