"""
Database Query Layer (Selectors) for Employee Leave Management (ELM).

This module contains all repository/query functions, accessing the database via
Django ORM. It isolates data access from business logic.
"""

from modules.leave_elm.models import LeaveBalance, LeaveApplication
from typing import Optional, List, Dict

# --- Balance Selectors ---

def get_employee_balance(employee_id: str, category: str) -> Optional[Dict]:
    """
    Fetches the available leave balance for a specific employee and category.
    
    :param employee_id: The employee ID (string).
    :param category: The leave category code (e.g., 'EL', 'CL').
    :return: Dictionary containing balance details, or None if not found.
    """
    try:
        balance, created = LeaveBalance.objects.get_or_create(
            user_id=employee_id, 
            category=category,
            defaults={'available_balance': 0.0, 'annual_entitlement': 0.0}
        )
        return {
            'available_balance': balance.available_balance,
            'annual_entitlement': balance.annual_entitlement,
        }
    except LeaveBalance.DoesNotExist:
        # Should not happen due to get_or_create, but kept for safety
        return None

def get_all_balances(employee_ids: List[str]) -> Dict[str, Dict]:
    """
    Fetches balances for a list of employees, combining multiple categories/roles.
    
    :param employee_ids: List of employee IDs.
    :return: Dictionary mapping employee ID to a map of category balances.
    """
    balances_map: Dict[str, Dict] = {}
    
    # Fetch all relevant balances for the given employees
    query = LeaveBalance.objects.filter(user_id__in=employee_ids)
    
    for balance in query:
        if balance.user_id not in balances_map:
            balances_map[balance.user_id] = {}
        
        balances_map[balance.user_id][balance.category] = {
            'available_balance': balance.available_balance,
            'annual_entitlement': balance.annual_entitlement,
        }
        
    return balances_map

# --- Application Selectors ---

def get_applications_for_employee(employee_id: str) -> List[Dict]:
    """
    Retrieves all leave applications submitted by a specific employee, ordered by date.
    
    :param employee_id: The employee ID (string).
    :return: List of application details dictionaries.
    """
    applications = LeaveApplication.objects.filter(employee_id=employee_id).order_by('-start_date')
    
    return [{
        'id': app.pk,
        'category': app.category,
        'start_date': app.start_date.isoformat(),
        'end_date': app.end_date.isoformat(),
        'reason': app.reason,
        'status': app.status,
        'substitute_id': app.substitute_id,
    } for app in applications]

def get_all_applications(is_admin: bool = False) -> List[Dict]:
    """
    Retrieves all leave applications in the system.
    
    :param is_admin: Flag to indicate if this call is made by a privileged user (HOD/Registrar).
    :return: List of application details dictionaries.
    """
    # In a real system, this would apply filtering based on the user's department/scope.
    if not is_admin:
        # Only return personal applications for non-admin users if needed for general view
        return []

    applications = LeaveApplication.objects.all().order_by('-start_date')
    
    return [{
        'id': app.pk,
        'employee_id': app.employee_id,
        'category': app.category,
        'start_date': app.start_date.isoformat(),
        'end_date': app.end_date.isoformat(),
        'reason': app.reason,
        'status': app.status,
        'substitute_id': app.substitute_id,
    } for app in applications]

def get_applications_by_approver_scope(approver_id: str) -> List[Dict]:
    """
    Retrieves applications that are awaiting action by the specified approver.
    (e.g., applications where status is 'pending' and the approver is designated to review it).
    
    For this implementation, we simplify the scope: find all pending applications.
    A proper system would join with organizational structure.
    """
    applications = LeaveApplication.objects.filter(status='pending').order_by('-start_date')
    
    return [{
        'id': app.pk,
        'employee_id': app.employee_id,
        'category': app.category,
        'start_date': app.start_date.isoformat(),
        'end_date': app.end_date.isoformat(),
        'reason': app.reason,
        'status': app.status,
        'substitute_id': app.substitute_id,
    } for app in applications]
