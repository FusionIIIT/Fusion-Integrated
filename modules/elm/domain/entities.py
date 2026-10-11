from typing import Optional
from datetime import date

# Domain Entity: Represents a generalized employee profile derived from IAM via ELMContracts.
class EmployeeProfile:
    def __init__(self, employee_id: str, roles: set[str], name: str, org_unit: str):
        self.employee_id = employee_id
        self.roles = roles  # Set of roles (e.g., ACT-01_Faculty)
        self.name = name
        self.org_unit = org_unit
        self.is_faculty: bool = True 

# Domain Entity: Represents a specific category of leave.
class LeaveType:
    def __init__(self, code: str, name: str, description: str, allows_carry_forward: bool = False, is_restricted: bool = False):
        self.code = code # e.g., 'CL', 'EL', 'VL'
        self.name = name
        self.description = description
        self.allows_carry_forward = allows_carry_forward
        self.is_restricted = is_restricted

# Domain Entity: The core representation of a leave request during processing.
class LeaveApplication:
    def __init__(self, 
                 application_id: Optional[int], 
                 employee_id: str, 
                 leave_type: LeaveType, 
                 start_date: date, 
                 end_date: date, 
                 status: str, 
                 substitute_nomination_id: Optional[int] = None):
        self.application_id = application_id
        self.employee_id = employee_id
        self.leave_type = leave_type
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.substitute_nomination_id = substitute_nomination_id
