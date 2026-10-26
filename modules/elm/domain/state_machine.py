"""Pure Python workflow and counting rules, independent of Django."""

from datetime import timedelta
from decimal import Decimal

PENDING = frozenset(
    {"PENDING_SUBSTITUTE", "APPLICANT_ACTION", "PENDING_UNIT_HEAD", "PENDING_AUTHORITY"}
)
ACTIVE = PENDING | {"APPROVED"}
HIGHER = frozenset({"SCL", "EL", "COL", "VL"})
CONTINUOUS = frozenset({"EL", "COL", "VL"})
CREDITS = {"CL": "8", "RH": "2", "SCL": "15", "EL": "30", "COL": "20", "VL": "60"}


class WorkflowTransitionError(ValueError):
    pass


def can_transition(current_status: str, target_status: str) -> bool:
    transitions = {
        "DRAFT": {"PENDING_SUBSTITUTE", "PENDING_UNIT_HEAD", "PENDING_AUTHORITY"},
        "PENDING_SUBSTITUTE": {
            "APPLICANT_ACTION",
            "PENDING_UNIT_HEAD",
            "PENDING_AUTHORITY",
            "WITHDRAWN",
        },
        "APPLICANT_ACTION": {"PENDING_SUBSTITUTE", "WITHDRAWN"},
        "PENDING_UNIT_HEAD": {"PENDING_AUTHORITY", "APPROVED", "REJECTED", "WITHDRAWN"},
        "PENDING_AUTHORITY": {"APPROVED", "REJECTED", "WITHDRAWN"},
        "APPROVED": {"CANCELLED"},
    }
    return target_status in transitions.get(current_status, set())


def determine_initial_status(has_substitute: bool) -> str:
    return "PENDING_SUBSTITUTE" if has_substitute else "PENDING_UNIT_HEAD"


def count_days(
    category, start, end, *, half_day=False, session="", closed=(), restricted=(), weekends=(5, 6)
):
    if end < start:
        raise ValueError("End date must be on or after start date.")
    if category not in CREDITS:
        raise ValueError("Unsupported leave category.")
    if half_day:
        if category != "CL" or start != end or session not in {"FN", "AN"}:
            raise ValueError("Half-day leave requires single-date CL and FN or AN session.")
    elif session:
        raise ValueError("A session is valid only for half-day CL.")
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    if category == "RH":
        if any(d.isoformat() not in restricted for d in days):
            raise ValueError("Every RH date must be in the effective published RH calendar.")
        count = len(days)
    elif category in CONTINUOUS:
        count = len(days)
    else:
        count = sum(d.weekday() not in weekends and d.isoformat() not in closed for d in days)
    if not count:
        raise ValueError("The requested interval contains no eligible leave days.")
    return Decimal("0.5") if half_day else Decimal(count)


def intervals_overlap(
    start,
    end,
    other_start,
    other_end,
    *,
    half=False,
    session="",
    other_half=False,
    other_session="",
):
    if end < other_start or other_end < start:
        return False
    return not (
        half
        and other_half
        and start == end == other_start == other_end
        and session != other_session
    )
