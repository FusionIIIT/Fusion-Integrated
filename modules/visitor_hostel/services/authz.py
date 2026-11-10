"""Write authority, stated once. Every service write path calls it.

Three separate questions, in this order:

    permission   does the acting role hold the code?     (the IAM decides)
    duty         is this the one Caretaker / In-Charge on duty? (BR-VH-045/046)
    self         is this person deciding their own booking?
"""
from __future__ import annotations

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.visitor_hostel.domain import duty
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.selectors import duty as duty_selectors

#: Lanes that act on behalf of an office and so must be the one on duty.
_LANE_ROLE = {sm.CARETAKER: duty.CARETAKER, sm.INCHARGE: duty.INCHARGE}


def require(actor, *codes: str) -> None:
    if actor is None:
        raise PermissionDeniedError("Authentication required.",
                                    code="not_authenticated")
    check = getattr(actor, "has_permission", None)
    if check is None or not any(check(c) for c in codes):
        raise PermissionDeniedError(f"This action needs {' or '.join(codes)}.",
                                    code="permission_denied")


def require_on_duty(actor, lane: str) -> None:
    """BR-VH-048: a reassignment takes effect the moment it is recorded,
    because the previous holder stops passing this check at once."""
    role = _LANE_ROLE.get(lane)
    if role is None:
        return
    holder = duty_selectors.current_holder_id(role)
    label = duty.LABELS[role]
    if holder is None:
        raise ConflictError(
            f"No {label} is on duty in VHMS. Ask the administrator to record the "
            f"current {label} (manage.py vh_assign_duty) and try again.",
            code="no_one_on_duty")
    if holder != getattr(actor, "user_id", None):
        raise PermissionDeniedError(
            f"Only the {label} currently on duty may do this.",
            code="not_on_duty")


def refuse_own(actor, booking) -> None:
    """Nobody reviews, decides or settles a booking they raised themselves."""
    if (booking.indenter_user_id is not None
            and booking.indenter_user_id == getattr(actor, "user_id", None)):
        raise PermissionDeniedError(
            "You raised this booking, so another officer must act on it.",
            code="self_decision")


def require_operator(actor, lane: str, *codes: str, booking=None) -> None:
    require(actor, *codes)
    require_on_duty(actor, lane)
    if booking is not None:
        refuse_own(actor, booking)
