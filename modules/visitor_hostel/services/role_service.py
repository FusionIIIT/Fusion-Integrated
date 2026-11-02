from django.db import transaction
from datetime import date
from typing import Optional
from modules.visitor_hostel.models import VHRoleAssignment

def assign_active_role(user: str, role: str, start_date: date) -> VHRoleAssignment:
    with transaction.atomic():
        # Deactivate any existing active assignments for the given role
        VHRoleAssignment.objects.filter(role=role, active=True).update(active=False, end_date=start_date)
        
        # Create a new active assignment for the given user and role
        return VHRoleAssignment.objects.create(user=user, role=role, active=True, start_date=start_date)

def get_active_role_user(role: str) -> Optional[str]:
    # Get the first active assignment for the given role
    assignment = VHRoleAssignment.objects.filter(role=role, active=True).first()
    
    # Return the user associated with the assignment if it exists; otherwise return None
    return assignment.user if assignment else None
