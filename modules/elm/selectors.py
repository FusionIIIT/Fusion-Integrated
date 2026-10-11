# ELM Selectors Layer: All reads and ownership filtering.

from typing import List, Dict, Any
from .domain.entities import LeaveApplication, EmployeeProfile
from .services import ELMService # Dependency Injection: Selector relies on Service for writes

class ELMSellector:
    """Handles all data retrieval and persistence for ELM.
    
    Note: In a production system, this would contain the ORM logic (Django/SQLAlchemy).
    For prototyping, it delegates persistence to the ELMService instance.
    """
    
    # Static storage simulation for prototype testing (In reality, this is the DB)
    _application_store: Dict[int, LeaveApplication] = {}
    _next_application_id: int = 1

    @staticmethod
    def get_employee(employee_id: str) -> EmployeeProfile:
        """Retrieves employee profile from the IAM system via a remote call."""
        # Placeholder implementation simulating IAM lookup
        print(f"Fetching employee profile for: {employee_id}...")
        return EmployeeProfile(
            employee_id=employee_id, 
            roles={"ACT-01_Faculty", "ACT-03_UnitHead"}, # Simulated roles
            name="John Doe", 
            org_unit="CS"
        )

    @staticmethod
    def get_applications_by_employee(employee_id: str) -> List[LeaveApplication]:
        """Retrieves all leave applications for a specific employee."""
        # Simulated database query
        return [app for app in ELMSellector._application_store.values() if app.employee_id == employee_id]

    @staticmethod
    def get_application(application_id: int) -> LeaveApplication:
        """Retrieves a single application by ID."""
        if application_id not in ELMSellector._application_store:
            raise ValueError(f"Application ID {application_id} not found.")
        return ELMSellector._application_store[application_id]

    @staticmethod
    def create_application(application: LeaveApplication) -> LeaveApplication:
        """
        Persists a new leave application record and returns the saved entity.
        This is the primary persistence method used by the Service layer.
        """
        global _next_application_id
        application.application_id = _next_application_id
        ELMSellector._application_store[_next_application_id] = application
        _next_application_id += 1
        print(f"Application {application.application_id} created and persisted.")
        return application

    @staticmethod
    def update_application_status(application_id: int, new_status: str):
        """Updates the status of an existing application record."""
        if application_id in ELMSellector._application_store:
            app = ELMSellector._application_store[application_id]
            app.status = new_status
            print(f"Application {application_id} status updated to {new_status}.")
        else:
            raise ValueError(f"Application ID {application_id} not found for update.")
            
    @staticmethod
    def get_balances(employee_id: str):
        """Retrieves all current leave balances for an employee."""
        # Placeholder
        return []

    @staticmethod
    def find_pending_requests_by_actor(actor_id: str):
        """Finds pending requests routed to a specific actor (e.g., Unit Head)."""
        # Placeholder
        return []
