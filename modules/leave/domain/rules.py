from datetime import date


def get_annual_entitlement(category_code: str) -> float:
    """Returns the base annual entitlement for a given leave category."""
    entitlements = {
        "CL": 8.0,
        "RH": 2.0,
        "SCL": 15.0,
        "EL": 30.0,
        "COL": 20.0,
        "VL": 60.0,
    }
    return entitlements.get(category_code.upper(), 0.0)


def is_carry_forward_allowed(category_code: str) -> bool:
    """Checks whether unused leave in this category carries forward to the next year."""
    return category_code.upper() in {"EL", "COL"}


def calculate_leave_days(start_date: date, end_date: date, is_half_day: bool = False) -> float:
    """Calculates requested leave days between start and end date inclusive."""
    if is_half_day and start_date == end_date:
        return 0.5
    days = (end_date - start_date).days + 1
    return max(0.0, float(days))


def convert_vl_to_el(unused_vl: float) -> float:
    """Converts unused Vacation Leave (VL) to Earned Leave (EL) at 2:1 ratio."""
    return round(unused_vl / 2.0, 1)
