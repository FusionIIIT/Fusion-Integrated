"""Defines the public contract for the Leave Management module.

Other modules may import this file to know what data and services
are available from the Leave module.
"""
from typing import TypedDict, List

# --- Data Structures ---

class LeaveCategory(TypedDict):
    name: str
    code: str
    description: str

class LeaveApplicationStatus(TypedDict):
    status_code: str
    display_name: str

class LeaveBalance(TypedDict):
    employee_id: int
    leave_category_code: str
    year: int
    balance_days: float

# --- Service Interfaces (What other modules can call) ---

class LeaveServiceContract:
    """Defines the interface for core leave operations."""

    def get_leave_balance(self, user_id: int, category_code: str, year: int) -> LeaveBalance:
        """Retrieves the current balance for a specific leave category and year."""
        raise NotImplementedError

    def submit_leave_request(self, user_id: int, category_code: str, start_date: str, end_date: str, details: dict) -> int:
        """Submits a new leave request and returns the application ID."""
        raise NotImplementedError

    def get_application_history(self, application_id: int) -> List[LeaveApplicationStatus]:
        """Retrieves the status history of a specific leave application."""
        raise NotImplementedError

# --- Domain Logic Interfaces (What other modules can query) ---

class EligibilityContract:
    """Defines the interface for eligibility checks."""

    def check_eligibility(self, user_id: int, category_code: str) -> bool:
        """Checks if the user is eligible for the specified leave category."""
        raise NotImplementedError

    def check_overlap(self, user_id: int, start_date: str, end_date: str) -> bool:
        """Checks if the requested period overlaps with existing approved/pending leave."""
        raise NotImplementedError
