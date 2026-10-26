"""Leave service re-exports and facade for backwards compatibility."""
from __future__ import annotations

import datetime

from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType
from modules.elm.selectors.balances import get_employee_balance_or_none
from modules.elm.services.apply import apply_for_leave
from modules.elm.services.cancellation import decide_cancellation, request_cancellation
from modules.elm.services.review import decide_sanction, review_unit_head
from modules.elm.services.withdraw import withdraw_pending_request


def count_days(start: datetime.date, end: datetime.date) -> float:
    """Calculate days between start and end (inclusive)."""
    return calculate_chargeable_days("EL", start, end)


def get_balance(employee_id: int, leave_type: LeaveType, year: int) -> LeaveBalance:
    """Retrieve balance record or raise NotFoundError."""
    bal = get_employee_balance_or_none(employee_id, leave_type, year)
    if not bal:
        from core.api.exceptions import NotFoundError
        raise NotFoundError("No leave balance for this leave type.", code="no_balance")
    return bal


def apply(actor, leave_type_id: int, start_date: datetime.date, end_date: datetime.date, reason: str, **kwargs) -> LeaveApplication:
    """Facade for apply_for_leave."""
    return apply_for_leave(actor, leave_type_id, start_date, end_date, reason, **kwargs)


def decide(actor, application_id: int, approve: bool, remarks: str = "") -> LeaveApplication:
    """Facade for decision."""
    app = LeaveApplication.objects.get(id=application_id)
    if app.status == "AWAITING_UNIT_HEAD":
        outcome = "RECOMMENDED" if approve else "NOT_RECOMMENDED"
        if app.leave_type.code in ("CL", "RH"):
            outcome = "APPROVE" if approve else "REJECT"
        return review_unit_head(actor, application_id, outcome=outcome, remarks=remarks)
    return decide_sanction(actor, application_id, approve=approve, remarks=remarks)


def withdraw(actor, application_id: int) -> LeaveApplication:
    """Facade for withdraw_pending_request."""
    return withdraw_pending_request(actor, application_id)


def cancel_approved(actor, application_id: int) -> LeaveApplication:
    """Facade for cancel request and auto-approval (for legacy tests)."""
    cancel_req = request_cancellation(actor, application_id, reason="Cancelled by employee")
    decide_cancellation(actor, cancel_req.id, approve=True, remarks="Auto-approved", is_final_authority=True)
    return LeaveApplication.objects.get(id=application_id)
