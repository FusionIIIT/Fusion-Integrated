from decimal import Decimal

def leave_days(start_date, end_date, half_day):
    """Calendar days from start_date to end_date inclusive; 0.5 for a half day."""
    if half_day != "NONE":
        if half_day not in ("FIRST", "SECOND") or start_date != end_date:
            raise ValueError("Half-day requests must have start_date equal to end_date")
        return Decimal("0.5")
    return Decimal((end_date - start_date).days + 1)


def half_days_overlap(a_start, a_end, a_half, b_start, b_end, b_half):
    """True if the two requests overlap. Two single-day requests on the same
    date for different halves (FIRST/SECOND) do not overlap."""
    both_single_halves = (a_start == a_end and a_half != "NONE"
                          and b_start == b_end and b_half != "NONE")
    if both_single_halves:
        return a_start == b_start and a_half == b_half
    return not (b_end < a_start or b_start > a_end)


def validate_balance(requested, entitled, used):
    """
    Validate if the requested days are within the entitlement.
    
    :param requested: The number of days requested as a Decimal.
    :param entitled: The total entitled days as a Decimal.
    :param used: The number of days already used as a Decimal.
    :raises ValueError: If the requested days exceed the entitlement minus used days.
    """
    if requested > entitled - used:
        raise ValueError("Insufficient entitlement")

def validate_rh_date(leave_date, published_rh_dates):
    """
    Validate if the leave date is in the list of published holidays.
    
    :param leave_date: The leave date as a datetime.date object.
    :param published_rh_dates: A set of published holiday dates as datetime.date objects.
    :raises ValueError: If the leave date is not in the list of published holidays.
    """
    if leave_date not in published_rh_dates:
        raise ValueError("Invalid RH date")

def validate_scl(requested, used_this_year, admissible):
    """
    Validate if the SCL request is within the allowed limits.
    
    :param requested: The number of days requested as a Decimal.
    :param used_this_year: The number of days already used this year as a Decimal.
    :param admissible: A boolean indicating if the request is admissible.
    :raises ValueError: If the request is not admissible or exceeds the allowed limit.
    """
    if not admissible or used_this_year + requested > Decimal(15):
        raise ValueError("Invalid SCL days")

def year_end_lapse(entitled, used):
    """
    Calculate the amount to lapse at year-end for CL and RH.
    
    :param entitled: The total entitled days as a Decimal.
    :param used: The number of days already used as a Decimal.
    :return: The amount to lapse as a Decimal (never below 0).
    """
    return max(entitled - used, Decimal(0))
