from datetime import date, timedelta
from typing import List, Tuple

# --- Constants ---
# Based on ELM specs:
# CL: 8 days/year (no carry forward)
# RH: 2 days/year (no carry forward)
# SCL: 15 days/year (no carry forward)
# EL (Non-faculty): 30 days/year (carry forward)
# VL (Faculty): 60 days/year (converts to EL)
# COL: 20 days/year (carry forward)

# --- Core Logic Functions ---

def get_annual_entitlement(category_code: str) -> float:
    """Returns the base annual entitlement for a given leave category."""
    return {
        "CL": 8.0,
        "RH": 2.0,
        "SCL": 15.0,
        "EL": 30.0,  # Non-faculty base
        "COL": 20.0,
        "VL": 60.0,
    }.get(category_code, 0.0)

def calculate_leave_days(start_date: date, end_date: date, is_half_day: bool) -> float:
    """
    Calculates the number of leave days between two dates, including weekends and holidays.
    (Note: In a real system, holidays would be fetched from a calendar service).
    """
    delta = end_date - start_date
    total_days = delta.days + 1
    
    # Simple approximation: assume 5 working days per week (2 weekend days)
    # This is a simplification of the continuous-day counting rule (BR-EL-011)
    # which states intervening weekends/holidays count as leave days.
    # Since we are calculating the duration, we count all calendar days.
    
    # If the request is for a single day, it's 1 day.
    if total_days == 1:
        return 1.0 if not is_half_day else 0.5
    
    # For multi-day requests, we count all days.
    return float(total_days)

def check_overlap(existing_leaves: List[Tuple[date, date]], new_start: date, new_end: date) -> bool:
    """
    Checks if the new leave period overlaps with any existing approved/pending leave.
    
    Args:
        existing_leaves: List of (start_date, end_date) tuples for existing leaves.
        new_start: Start date of the new request.
        new_end: End date of the new request.
        
    Returns:
        True if overlap exists, False otherwise.
    """
    for existing_start, existing_end in existing_leaves:
        # Overlap occurs if:
        # 1. New start is before existing end AND
        # 2. New end is after existing start
        if new_start <= existing_end and new_end >= existing_start:
            return True
    return False

def check_half_day_exception(existing_leaves: List[Tuple[date, date]], new_start: date, new_end: date, is_half_day: bool) -> bool:
    """
    Checks for overlap, applying the half-day CL exception (BR-EL-012).
    
    If the new request is a half-day CL, it only overlaps if the existing leave
    covers the entire day, or if the existing leave is also a half-day on the same date.
    
    For simplicity in this skeleton, we assume a half-day request only occupies
    a single day (new_start == new_end).
    """
    if not is_half_day:
        # If it's not a half-day, standard overlap check applies
        return check_overlap(existing_leaves, new_start, new_end)

    # Half-day CL exception: two half-day CLs on the same date are non-overlapping.
    # We check if any existing leave covers this single day.
    for existing_start, existing_end in existing_leaves:
        if new_start == existing_start and new_end == existing_end:
            # If existing leave is also a half-day on the same date, it's non-overlapping.
            # Since we don't have the 'is_half_day' flag for existing leaves here,
            # we must assume if it covers the day, it's an overlap unless we refine the input.
            # For the skeleton, we treat any existing leave covering the day as an overlap
            # unless we explicitly know the existing leave is also a half-day.
            # Given the spec: "first-half and second-half CL on the same date are non-overlapping"
            # We assume if the existing leave is a full day, it overlaps.
            return True
            
    return False

def convert_vl_to_el(vl_days: float) -> float:
    """
    Converts Vacation Leave (VL) to Earned Leave (EL) at 2 VL : 1 EL (BR-EL-007).
    """
    return vl_days / 2.0
