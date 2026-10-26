from enum import StrEnum


class LeaveRequestStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_SANCTION = "PENDING_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"


class StateTransitionError(Exception):
    pass


TRANSITIONS = {
    LeaveRequestStatus.SUBMITTED: {
        LeaveRequestStatus.PENDING_UNIT_HEAD,
        LeaveRequestStatus.CANCELLED,
        LeaveRequestStatus.WITHDRAWN,
    },
    LeaveRequestStatus.PENDING_UNIT_HEAD: {
        LeaveRequestStatus.PENDING_SANCTION,
        LeaveRequestStatus.APPROVED,
        LeaveRequestStatus.REJECTED,
        LeaveRequestStatus.CANCELLED,
        LeaveRequestStatus.WITHDRAWN,
    },
    LeaveRequestStatus.PENDING_SANCTION: {
        LeaveRequestStatus.APPROVED,
        LeaveRequestStatus.REJECTED,
        LeaveRequestStatus.CANCELLED,
    },
}


def can_transition(current_status, next_status):
    try:
        current = LeaveRequestStatus(current_status)
        following = LeaveRequestStatus(next_status)
    except ValueError:
        return False

    return following in TRANSITIONS.get(current, set())


def transition(current_status, next_status):
    if not can_transition(current_status, next_status):
        raise StateTransitionError(
            f"Invalid leave request transition: {current_status} -> {next_status}"
        )

    return LeaveRequestStatus(next_status).value
