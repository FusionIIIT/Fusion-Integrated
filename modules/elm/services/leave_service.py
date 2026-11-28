from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveActionLog

def calculate_leave_days(start_date: datetime, end_date: datetime, half_day: bool = False) -> Decimal:
    if half_day:
        return Decimal('0.5')
    return Decimal((end_date - start_date).days + 1)

def check_leave_balance(user: str, leave_type: str, requested_days: Decimal, year: Optional[int] = None) -> Tuple[bool, Optional[Decimal]]:
    if year is None:
        year = start_date.year
    balance = LeaveBalance.query.filter_by(user=user, leave_type=leave_type, year=year).first()
    if not balance:
        balance = LeaveBalance(user=user, leave_type=leave_type, year=year, balance=Decimal('0'), used_days=Decimal('0'))
        balance.save()
        return False, None
    if balance.balance >= requested_days:
        return True, balance.balance
    return False, f"Insufficient balance. Available: {balance.balance}, Requested: {requested_days}"

def check_overlapping_leave(user: str, start_date: datetime, end_date: datetime, half_day: bool = False, half_day_period: Optional[str] = None, exclude_request_id: Optional[int] = None) -> Tuple[bool, str]:
    overlapping_requests = LeaveRequest.query.filter_by(applicant=user, status='pending_unit_head').all()
    for request in overlapping_requests:
        if request.id == exclude_request_id:
            continue
        if start_date <= request.end_date and end_date >= request.start_date:
            if request.half_day and half_day and request.half_day_period != half_day_period:
                continue
            return False, "Overlapping leave request exists"
    return True, "No conflict"

def submit_leave_request(applicant: str, leave_type: str, start_date: datetime, end_date: datetime, purpose: str, half_day: bool = False, half_day_period: Optional[str] = None, station_leave: bool = False, station_leave_address: str = "", substitute: Optional[str] = None) -> None:
    is_balance_sufficient, balance = check_leave_balance(applicant, leave_type, calculate_leave_days(start_date, end_date, half_day))
    if not is_balance_sufficient:
        raise ValueError("Insufficient leave balance")
    is_overlap_clean, _ = check_overlapping_leave(applicant, start_date, end_date, half_day, half_day_period)
    if not is_overlap_clean:
        raise ValueError("Overlapping leave request exists")
    status = 'awaiting_substitute' if substitute else 'pending_unit_head'
    leave_request = LeaveRequest(applicant=applicant, leave_type=leave_type, start_date=start_date, end_date=end_date, purpose=purpose, half_day=half_day, half_day_period=half_day_period, station_leave=station_leave, station_leave_address=station_leave_address, substitute=substitute, status=status)
    leave_request.save()
    LeaveActionLog.log(leave_request.id, 'submitted', applicant)

def respond_substitute(leave_request: LeaveRequest, substitute_user: str, decision: str, comments: str = "") -> None:
    if leave_request.substitute != substitute_user:
        raise ValueError("Invalid substitute user")
    if decision == 'accepted':
        leave_request.substitute_status = 'accepted'
        leave_request.status = 'pending_unit_head'
    elif decision == 'declined':
        leave_request.substitute_status = 'declined'
        leave_request.status = 'awaiting_substitute'
    else:
        raise ValueError("Invalid decision")
    leave_request.save()
    LeaveActionLog.log(leave_request.id, decision, substitute_user, comments)

def process_approval(leave_request: LeaveRequest, actor_user: str, role_name: str, action: str, comments: str = "") -> None:
    valid_actions = ['recommended', 'not_recommended', 'approved', 'rejected']
    if action not in valid_actions:
        raise ValueError("Invalid action")
    if action == 'approved':
        leave_request.status = 'approved'
        leave_request.balance -= leave_request.requested_days
        leave_request.used_days += leave_request.requested_days
    elif action == 'rejected':
        leave_request.status = 'rejected'
    elif action == 'recommended':
        leave_request.status = 'pending_higher_sanction'
    leave_request.save()
    LeaveActionLog.log(leave_request.id, action, actor_user, comments)