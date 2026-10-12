"""Policy domain definitions.

Pure-Python. No Django imports.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

LeaveCategory = Literal["CL", "RH", "SCL", "EL", "COL", "VL"]


@dataclass(frozen=True)
class LeavePolicy:
    """Current configured leave-policy parameters.

No draft/publish/effective-version lifecycle. Uses current configured values.
"""
    cl_days: int = 8
    rh_days: int = 2
    scl_max_days: int = 15
    el_days: int = 30
    col_days: int = 20
    vl_days: int = 60
    vl_to_el_ratio: Decimal = Decimal("0.5")  # 2 VL : 1 EL

    def get_entitlement(self, category: LeaveCategory) -> Optional[Decimal]:
        """Get entitlement for a leave category."""
        if category == "CL":
            return Decimal(self.cl_days)
        elif category == "RH":
            return Decimal(self.rh_days)
        elif category == "SCL":
            return Decimal(self.scl_max_days)
        elif category == "EL":
            return Decimal(self.el_days)
        elif category == "COL":
            return Decimal(self.col_days)
        elif category == "VL":
            return Decimal(self.vl_days)
        return None

    def get_year_end_outcome(self, category: LeaveCategory) -> Literal["LAPSE", "CARRY_FORWARD", "CONVERT"]:
        """Get year-end outcome for a leave category."""
        if category in ("CL", "RH", "SCL"):
            return "LAPSE"
        elif category == "VL":
            return "CONVERT"
        else:  # EL, COL
            return "CARRY_FORWARD"

    def is_faculty_vl_applicable(self, user_kind: str) -> bool:
        """Check if VL is applicable for faculty."""
        return user_kind == "faculty"


@dataclass(frozen=True)
class HolidayCalendar:
    """Currently effective published holiday/RH calendar."""
    year: int
    holidays: list[date]
    restricted_holidays: list[date]
    is_effective: bool = True

    def is_date_a_holiday(self, d: date) -> bool:
        """Check if a date is a holiday."""
        return d in self.holidays

    def is_restricted_holiday(self, d: date) -> bool:
        """Check if a date is a Restricted Holiday."""
        return d in self.restricted_holidays


@dataclass(frozen=True)
class VacationPeriod:
    """Vacation period for VL applicability.

External dependency from Academic Calendar service/module.
"""
    year: int
    start_date: date
    end_date: date
    name: str

    def contains_date(self, d: date) -> bool:
        """Check if a date falls within this vacation period."""
        return self.start_date <= d <= self.end_date


@dataclass(frozen=True)
class OrganizationalUnit:
    """Department, Section, or Office."""
    code: str
    name: str
    parent_unit_id: Optional[int] = None
    unit_head_user_id: int = 0

    def is_parent_of(self, other: "OrganizationalUnit") -> bool:
        """Check if this unit is a parent of another unit."""
        return self.code == other.parent_unit_id


@dataclass(frozen=True)
class LeaveHierarchy:
    """Configured hierarchy for leave sanctioning paths."""
    name: str
    description: str = ""
    steps: list["LeaveHierarchyStep"] = None

    def __post_init__(self):
        if self.steps is None:
            object.__setattr__(self, "steps", [])


@dataclass(frozen=True)
class LeaveHierarchyStep:
    """Step in a leave sanctioning hierarchy."""
    order: int
    role_code: str
    is_establishment_step: bool = False
