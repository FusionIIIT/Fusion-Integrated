from enum import Enum
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional

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
