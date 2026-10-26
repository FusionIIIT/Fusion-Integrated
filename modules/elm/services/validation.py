"""Leave validation rules: BR-EL-003, 006, 010, 011, 012, 014."""
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.models import CalendarDay, LeaveAccount, LeaveRequest, LeaveType

#: Pending or approved leave counts as active for overlap checks (BR-EL-012).
ACTIVE_STATUSES = [
    LeaveRequest.Status.AWAITING_SUBSTITUTE,
    LeaveRequest.Status.AWAITING_UNIT_HEAD,
    LeaveRequest.Status.AWAITING_ESTABLISHMENT,
    LeaveRequest.Status.AWAITING_FINAL,
    LeaveRequest.Status.AWAITING_DIRECTOR_SELF,
    LeaveRequest.Status.APPROVED,
    LeaveRequest.Status.CANCELLATION_PENDING,
    LeaveRequest.Status.AWAITING_RESUMPTION,
]

CONTINUOUS_TYPES = (LeaveType.EL, LeaveType.COL, LeaveType.VL)


class LeaveValidationError(Exception):
    pass


def chargeable_days(leave_type, start: date, end: date, half: str = "",
                    closed_days: frozenset = frozenset()) -> Decimal:
    """BR-EL-010 and BR-EL-011.

    EL/COL/VL: every calendar day counts, weekends and closed holidays included.
    CL/SCL/RH: weekends and closed holidays do not count (assumption: Sat/Sun).
    Half-day: only CL on a single date, costs 0.5.
    """
    if end < start:
        raise LeaveValidationError("End date is before start date.")
    if half:
        if leave_type != LeaveType.CL or start != end:
            raise LeaveValidationError("Half-day applies only to CL on a single date.")
        return Decimal("0.5")
    if leave_type in CONTINUOUS_TYPES:
        return Decimal((end - start).days + 1)
    count, day = 0, start
    while day <= end:
        if day.weekday() < 5 and day not in closed_days:
            count += 1
        day += timedelta(days=1)
    return Decimal(count)


def ranges_overlap(a_start, a_end, a_half, b_start, b_end, b_half) -> bool:
    """BR-EL-012: first and second half of the same date do not overlap."""
    if a_end < b_start or b_end < a_start:
        return False
    same_single_day = a_start == a_end == b_start == b_end
    return not (same_single_day and a_half and b_half and a_half != b_half)


def find_overlapping(user_id: int, start: date, end: date, half: str = "",
                     exclude_id: int | None = None) -> list[LeaveRequest]:
    qs = LeaveRequest.objects.filter(
        applicant_id=user_id, status__in=ACTIVE_STATUSES,
        start_date__lte=end, end_date__gte=start,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return [r for r in qs
            if ranges_overlap(start, end, half, r.start_date, r.end_date, r.half)]


def check_no_overlap(user_id, start, end, half="", exclude_id=None) -> None:
    if find_overlapping(user_id, start, end, half, exclude_id):
        raise LeaveValidationError("Overlaps with an existing pending or approved leave.")


def check_substitute(applicant_id: int, nominee_id: int, start: date, end: date,
                     nominee_user=None) -> None:
    """BR-EL-014: another employee, with no overlapping pending/approved leave."""
    if nominee_id == applicant_id:
        raise LeaveValidationError("Applicant cannot be their own substitute.")
    if nominee_user is not None and getattr(nominee_user, "kind", None) not in ("faculty", "staff"):
        raise LeaveValidationError("Substitute must be an active employee (faculty or staff).")
    if find_overlapping(nominee_id, start, end, half=""):
        raise LeaveValidationError("Substitute has overlapping leave in this period.")


def calendar_dates(calendar, kind: str, start: date, end: date) -> set[date]:
    return set(CalendarDay.objects.filter(
        calendar=calendar, kind=kind, date__gte=start, date__lte=end
    ).values_list("date", flat=True))


def check_rh_date(calendar, day: date) -> None:
    """BR-EL-003: RH must be a published Restricted Holiday."""
    if not calendar_dates(calendar, "rh", day, day):
        raise LeaveValidationError("Date is not a published Restricted Holiday.")


def check_vl_period(calendar, start: date, end: date) -> None:
    """BR-EL-006: every day of VL must fall in a published vacation period."""
    total = (end - start).days + 1
    if len(calendar_dates(calendar, "vacation", start, end)) != total:
        raise LeaveValidationError("VL is allowed only within a published vacation period.")


def get_balance(user_id: int, year: int, leave_type: str) -> Decimal:
    acct = LeaveAccount.objects.filter(
        user_id=user_id, year=year, leave_type=leave_type).first()
    return acct.balance if acct else Decimal("0")


def check_balance(user_id: int, year: int, leave_type: str, days: Decimal) -> None:
    if get_balance(user_id, year, leave_type) < days:
        raise LeaveValidationError("Insufficient leave balance.")
