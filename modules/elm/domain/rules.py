from datetime import date
from typing import List
from .entities import EmployeeProfile, LeaveType, LeaveApplication

def calculate_entitlement(employee: EmployeeProfile, leave_type: LeaveType) -> float:
    """
    Calculates the total leave entitlement for a given employee and leave type.
    Rules based on CFR-EL-011: different types have different accrual logic.
    Returns the total amount (float).
    """
    # Logic implementation:
    # If leave_type is CL (Casual Leave), annual fixed entitlement applies.
    if leave_type.code == 'CL':
        return 18.0 # Standard annual entitlement
    
    # If leave_type is EL (Earned Leave), it accrues monthly based on service period.
    elif leave_type.code == 'EL':
        # NOTE: Currently returns a hardcoded 18.0 as service duration is unavailable.
        # The 1.5 days/month formula is an assumption requiring business confirmation.
        return 18.0 # Placeholder
        
    # If leave_type is VL (Vacation Leave), fixed annual entitlement.
    elif leave_type.code == 'VL':
        return 20.0
        
    # Fallback
    return 0.0

def check_overlap(existing_applications: List[LeaveApplication], 
                   new_start_date: date, 
                   new_end_date: date) -> bool:
    """
    Checks if the new leave period overlaps with any existing approved/pending leaves.
    
    Overlap condition: (StartA <= EndB) AND (EndA >= StartB)
    """
    for app in existing_applications:
        # Assuming 'app' has start_date and end_date attributes of type date
        if (new_start_date <= app.end_date) and (new_end_date >= app.start_date):
            return True
    return False

def process_year_end_conversion(employee: EmployeeProfile, leave_type: LeaveType, available_balance: float) -> float:
    """
    Processes the conversion of unused leave (e.g., VL to EL) at year end.
    Rules based on BR-EL-035.
    """
    if leave_type.code == 'VL':
        # Allow up to 5 days conversion from VL to EL
        return min(available_balance, 5.0)
    
    return 0.0
