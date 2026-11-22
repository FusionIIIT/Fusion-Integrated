from dataclasses import dataclass


@dataclass(frozen=True)
class DepartmentScope:
    department_code: str
    department_name: str
    role: str


class InvalidTransition(ValueError):
    pass


TRANSITIONS = {
    ("pending", "approve", "HOD"): "approved",
    ("pending", "reject", "HOD"): "rejected",
    ("approved", "issue", "Dept_Admin"): "issued",
    ("approved", "cancel", "Dept_Admin"): "cancelled",
    ("new", "review", "Dept_Admin"): "under_review",
    ("under_review", "resolve", "Dept_Admin"): "resolved",
    ("under_review", "close", "Dept_Admin"): "closed",
    ("under_review", "resolve", "HOD"): "resolved",
    ("under_review", "close", "HOD"): "closed",
    ("pending", "approve_detail", "HOD"): "approved",
    ("pending", "reject_detail", "HOD"): "rejected",
}


def transition(state: str, event: str, role: str) -> str:
    try:
        return TRANSITIONS[(state, event, role)]
    except KeyError as exc:
        raise InvalidTransition(f"{role} cannot {event} a {state} record.") from exc


def has_overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a
