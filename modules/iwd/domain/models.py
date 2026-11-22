"""Domain models and permission definitions for IWD."""
from enum import Enum
from decimal import Decimal

# Permission codes enforced across IWD endpoints and services
PERM_VIEW = "iwd.complaint.view"
PERM_CREATE = "iwd.complaint.create"
PERM_MANAGE = "iwd.complaint.manage"
PERM_APPROVE = "iwd.complaint.approve"
PERM_AUDIT = "iwd.complaint.audit"
PERM_SETTLE = "iwd.complaint.settle"

class Role(str, Enum):
    EMPLOYEE = "employee"
    ENGINEER = "engineer"
    IWD_ADMIN = "admin"
    DEPARTMENT_HEAD = "hod"
    DEAN = "dean"
    DIRECTOR = "director"
    AUDITOR = "auditor"
    ACCOUNTS = "accounts"

class CostBand(str, Enum):
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"

LOW_THRESHOLD = Decimal("25000.00")
HIGH_THRESHOLD = Decimal("250000.00")

def determine_cost_band(total: Decimal) -> CostBand:
    if total < LOW_THRESHOLD:
        return CostBand.LOW
    elif total <= HIGH_THRESHOLD:
        return CostBand.MID
    else:
        return CostBand.HIGH
