from datetime import date, timedelta
from decimal import Decimal

ENTITLEMENTS = {
    'CL': Decimal('8'),
    'RH': Decimal('2'),
    'SCL': Decimal('15'),
    'EL': Decimal('30'),
    'VL': Decimal('60'),
    'COL': Decimal('20')
}

def count_leave_days(category: str, start: date, end: date, half_day: str | None = None, closed_dates: set[date] | None = None) -> Decimal:
    if category not in ENTITLEMENTS:
        raise ValueError(f"Invalid leave category: {category}")
    
    if start > end:
        raise ValueError("Start date must be before end date")
    
    if closed_dates is None:
        closed_dates = set()
    
    # BR-EL-010: Half-day CL treatment
    if category == 'CL' and half_day in ('first', 'second'):
        if start != end:
            raise ValueError("Half-day CL must be on the same date")
        return Decimal('0.5')
    
    # BR-EL-011: Continuous-day counting for EL, COL, VL
    if category in ('EL', 'COL', 'VL'):
        return Decimal((end - start).days + 1)
    
    # Working days only for CL, SCL, RH
    total_days = Decimal('0')
    current_date = start
    while current_date <= end:
        if current_date not in closed_dates:
            total_days += Decimal('1')
        current_date += timedelta(days=1)
    
    return total_days

def intervals_overlap(a_start: date, a_end: date, a_half: str | None, b_start: date, b_end: date, b_half: str | None) -> bool:
    if a_end < b_start or b_end < a_start:
        return False
    
    # BR-EL-012: Applicant non-overlap with half-day CL exception
    if a_start == a_end == b_start == b_end:
        if (a_half == 'first' and b_half == 'second') or (a_half == 'second' and b_half == 'first'):
            return False
    
    return True

def calculate_vl_to_el_conversion(unutilized_vl: Decimal, current_el: Decimal, max_el_cap: Decimal = Decimal('300')) -> tuple[Decimal, Decimal, Decimal]:
    # BR-EL-007 & BR-EL-008: 2 VL : 1 EL including fractional conversion
    el_credited = unutilized_vl / Decimal('2')
    credited_el = min(el_credited, max(Decimal('0'), max_el_cap - current_el))
    forfeited_vl = unutilized_vl - (credited_el * Decimal('2'))
    new_el_balance = current_el + credited_el
    return (credited_el, forfeited_vl, new_el_balance)

def validate_station_leave(is_station_leave: bool, destination: str | None, emergency_contact: str | None) -> bool:
    # BR-EL-013: Station Leave coupling
    if is_station_leave:
        if not destination or not destination.strip() or not emergency_contact or not emergency_contact.strip():
            return False
    return True

def can_substitute(applicant_id: int, substitute_id: int) -> bool:
    # BR-EL-014: Substitute eligibility constraint
    return applicant_id != substitute_id
