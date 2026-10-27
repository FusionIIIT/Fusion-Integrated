# ELM Contracts: Defines the public API surface for all other modules to interact with ELM.
# This MUST be the only public interface.

from typing import List, Optional, Dict
from .domain.entities import LeaveApplication

class ELMContracts:
    """
    Defines standardized data structures for requests and responses.
    This avoids any direct dependency on the internal models.py structure.
    """

    # --- Input Contracts ---
    class LeaveApplicationRequest:
        """Data structure used when an external module submits a leave application."""
        employee_id: str
        leave_type: str # Must match registered LeaveType names (e.g., 'CL', 'EL')
        start_date: str # ISO format YYYY-MM-DD
        end_date: str
        purpose: Optional[str] = None
        is_station_leave: bool = False

    # --- Output Contracts ---
    class LeaveApplicationResponse:
        """Data structure returned by ELM upon successful operation."""
        id: int
        employee_id: str
        leave_type: str
        start_date: str
        end_date: str
        status: str
        sanctioning_authority: Optional[str]
        
    class LeaveBalanceResponse:
        """Data structure returned for balance inquiries."""
        employee_id: str
        leave_type: str
        available_balance: float
        entitled_balance: float

    # --- API Methods (Service-level interface) ---
    @staticmethod
    def submit(data: LeaveApplicationRequest) -> LeaveApplicationResponse:
        """Public interface for creating a leave application."""
        raise NotImplementedError("Must be implemented by the ELM Service.")

    @staticmethod
    def get_applications(employee_id: str) -> List[LeaveApplicationResponse]:
        """Public interface to fetch employee's leave history."""
        raise NotImplementedError("Must be implemented by the ELM Service.")
        
    @staticmethod
    def get_balance(employee_id: str, leave_type: str) -> LeaveBalanceResponse:
        """Public interface to check a specific leave balance."""
        raise NotImplementedError("Must be implemented by the ELM Service.")
