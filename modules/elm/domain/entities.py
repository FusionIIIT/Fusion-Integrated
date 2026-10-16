from enum import Enum
from dataclasses import dataclass
from datetime import date

class LeaveCategory(Enum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"

@dataclass(frozen=True)
class LeaveRequestDateRange:
    start_date: date
    end_date: date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be later than end_date")

@dataclass(frozen=True)
class LeaveRequest:
    category: LeaveCategory
    date_range: LeaveRequestDateRange
