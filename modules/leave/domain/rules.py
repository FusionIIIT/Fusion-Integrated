from datetime import date

def is_half_day_cl_valid(half_day_cl: bool) -> bool:
    # Half-day CL is valid for CL only.
    return half_day_cl and LeaveCategory.CL in [LeaveCategory.CL, LeaveCategory.SCL]

def is_overlap_valid(start_date: date, end_date: date) -> bool:
    # Overlap check with the half-day CL exception.
    return start_date <= end_date
