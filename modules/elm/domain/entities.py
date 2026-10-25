"""Domain entities and value objects for Leave Management (ELM).

Pure Python — no Django or HTTP dependencies.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LeaveCategorySpec:
    code: str
    name: str
    annual_quota: Decimal
    carries_forward: bool
    continuous_counting: bool
    faculty_only: bool


STANDARD_LEAVE_CATEGORIES = {
    "CL": LeaveCategorySpec(
        code="CL",
        name="Casual Leave",
        annual_quota=Decimal("8.0"),
        carries_forward=False,
        continuous_counting=False,
        faculty_only=False,
    ),
    "RH": LeaveCategorySpec(
        code="RH",
        name="Restricted Holiday",
        annual_quota=Decimal("2.0"),
        carries_forward=False,
        continuous_counting=False,
        faculty_only=False,
    ),
    "SCL": LeaveCategorySpec(
        code="SCL",
        name="Special Casual Leave",
        annual_quota=Decimal("15.0"),
        carries_forward=False,
        continuous_counting=False,
        faculty_only=False,
    ),
    "EL": LeaveCategorySpec(
        code="EL",
        name="Earned Leave",
        annual_quota=Decimal("30.0"),
        carries_forward=True,
        continuous_counting=True,
        faculty_only=False,
    ),
    "COL": LeaveCategorySpec(
        code="COL",
        name="Commuted Leave",
        annual_quota=Decimal("20.0"),
        carries_forward=True,
        continuous_counting=True,
        faculty_only=False,
    ),
    "VL": LeaveCategorySpec(
        code="VL",
        name="Vacation Leave",
        annual_quota=Decimal("60.0"),
        carries_forward=False,
        continuous_counting=True,
        faculty_only=True,
    ),
}


@dataclass(frozen=True)
class LeaveInterval:
    start_date: date
    end_date: date
    half_day: str = "none"  # "none", "first_half", "second_half"
