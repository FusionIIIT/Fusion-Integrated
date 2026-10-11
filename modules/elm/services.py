# ELM Services Layer: Core business logic that modifies state.

from .domain.entities import LeaveApplication, EmployeeProfile, LeaveType
from .domain.rules import check_overlap, calculate_entitlement, process_year_end_conversion
from .selectors import ELMSellector
from .selectors import ELMSellector
from typing import Optional

class ELMService:
    """Manages state changes and executes workflow transitions."""

    def __init__(self, auth_user_id: str):
        self.auth_user_id = auth_user_id

    def submit_leave_application(self, application_data: dict) -> LeaveApplication:
        """
        Initiates a new leave application.
        1. Validates entitlement using domain rules.
        2. Checks for overlap using domain rules.
        3. Creates the pending record via models.py.
        """
        # 1. Fetch employee profile and calculate max entitlement
        employee = ELMSellector.get_employee(self.auth_user_id)
        
        # Convert leave_type code string to domain object
        leave_type_obj = LeaveType(
            code=application_data['leave_type'],
            name="Unknown", # Placeholder, ideally fetched from DB/Config
            description="", # Placeholder
            allows_carry_forward=False, # Placeholder
            is_restricted=False # Placeholder
        )

        # 2. Validation checks
        entitlement = calculate_entitlement(employee, leave_type_obj)
        if entitlement <= 0:
            raise ValueError(f"Leave type {application_data['leave_type']} is invalid or entitlement is zero.")
             
        # Check for overlap
        existing_apps = ELMSellector.get_applications_by_employee(self.auth_user_id)
        if check_overlap(existing_apps, application_data['start_date'], application_data['end_date']):
            raise ValueError("Leave period overlaps with existing approved leave.")

        # 3. Create and return the pending application
        application = LeaveApplication(
            application_id=None,
            employee_id=self.auth_user_id,
            leave_type=leave_type_obj,
            start_date=application_data['start_date'],
            end_date=application_data['end_date'],
            status='PENDING'
        )
        
        # Calls ORM save method via selector/models
        return ELMSellector.create_application(application)

    def review_and_approve_request(self, application_id: int, actor_id: str) -> LeaveApplication:
        """
        Handles the approval/rejection process by the applicable actor (Unit Head, Sanctioning Authority).
        """
        application = ELMSellector.get_application(application_id)
        
        if actor_id not in self._get_allowed_actors(application):
            raise PermissionError("Unauthorized actor.")
        
        # Transition logic: update status and call balance adjustment service
        if application.status == 'PENDING':
            application.status = 'APPROVED'
            # Update balances here based on approval status
            ELMSellector.update_application_status(application.application_id, 'APPROVED')
            
        return application

    # Helper methods for internal logic
    def _get_allowed_actors(self, application: LeaveApplication) -> set[str]:
        """Determines who can approve this specific request based on hierarchy."""
        # Complex logic referencing actor registry and employee profiles
        return set()
        return set()
        return set() 

    def _save_application(self, application: LeaveApplication) -> LeaveApplication:
        # Calls ORM save method
        return ELMSellector.create_application(application)

