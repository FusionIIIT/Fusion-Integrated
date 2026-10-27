from decimal import Decimal
from datetime import timedelta
from django.core.exceptions import ValidationError
from modules.elm.models import HolidayCalendar, LeaveBalance, LeaveRequest, LeaveCategory, PartOfDay, LeaveStatus

def calculate_leave_days(category: str, start_date, end_date, part_of_day: str = 'full') -> Decimal:
    if category in ('EL', 'COL', 'VL'):
        total = (end_date - start_date).days + 1
        return Decimal(str(total))
    total_days = 0
    cur = start_date
    while cur <= end_date:
        if cur.weekday() not in (5, 6) and not HolidayCalendar.objects.filter(date=cur, is_rh=False).exists():
            total_days += 1
        cur += timedelta(days=1)
    if category == 'CL' and part_of_day in ('first_half', 'second_half') and start_date == end_date:
        return Decimal('0.5')
    return Decimal(str(total_days))

def validate_leave_application(user_id: int, category: str, start_date, end_date, part_of_day: str = 'full', substitute_user_id: int | None = None, station_leave: bool = False, station_destination: str = '') -> Decimal:
    if end_date < start_date:
        raise ValidationError('End date cannot precede start date.')
    if station_leave and not station_destination.strip():
        raise ValidationError('Station destination is required for Station Leave.')
    if category == 'RH':
        if not HolidayCalendar.objects.filter(date=start_date, is_rh=True).exists():
            raise ValidationError('Selected date is not a listed Restricted Holiday in the calendar.')
    if substitute_user_id is not None:
        if substitute_user_id == user_id:
            raise ValidationError('Substitute cannot be the applicant.')
        sub_overlap = LeaveRequest.objects.filter(
            user_id=substitute_user_id,
            status__in=[LeaveStatus.SUBMITTED, LeaveStatus.PENDING_SUBSTITUTE, LeaveStatus.PENDING_UNIT_HEAD, LeaveStatus.RECOMMENDED, LeaveStatus.PENDING_SANCTION, LeaveStatus.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).exists()
        if sub_overlap:
            raise ValidationError('Nominated substitute has overlapping active or pending leave.')
    active_reqs = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=[LeaveStatus.SUBMITTED, LeaveStatus.PENDING_SUBSTITUTE, LeaveStatus.PENDING_UNIT_HEAD, LeaveStatus.RECOMMENDED, LeaveStatus.PENDING_SANCTION, LeaveStatus.APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    for req in active_reqs:
        is_same_day_cl = (category == 'CL' and req.category == 'CL' and start_date == end_date == req.start_date == req.end_date)
        is_different_halves = (part_of_day in ('first_half', 'second_half') and req.part_of_day in ('first_half', 'second_half') and part_of_day != req.part_of_day)
        if is_same_day_cl and is_different_halves:
            continue
        raise ValidationError(f'Overlaps with existing leave request #{req.id}.')
    computed = calculate_leave_days(category, start_date, end_date, part_of_day)
    if computed <= 0:
        raise ValidationError('Computed leave days must be greater than zero.')
    year = start_date.year
    bal = LeaveBalance.objects.filter(user_id=user_id, year=year, category=category).first()
    if bal is None or bal.available_days < computed:
        available = bal.available_days if bal else Decimal('0')
        raise ValidationError(f'Insufficient leave balance. Available: {available}, Required: {computed}.')
    return computed
