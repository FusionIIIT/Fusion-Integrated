"""Leave categories and annual entitlement rules for ELM."""

from dataclasses import dataclass
from datetime import date
from enum import Enum


class LeaveCode(Enum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    VL = "VL"
    COL = "COL"


@dataclass(frozen=True)
class LeaveEntitlement:
    code: LeaveCode
    annual_days: float
    carries_forward: bool
    continuous_count: bool


LEAVE_ENTITLEMENTS: dict[str, LeaveEntitlement] = {
    "CL": LeaveEntitlement(
        code=LeaveCode.CL,
        annual_days=8.0,
        carries_forward=False,
        continuous_count=False,
    ),
    "RH": LeaveEntitlement(
        code=LeaveCode.RH,
        annual_days=2.0,
        carries_forward=False,
        continuous_count=False,
    ),
    "SCL": LeaveEntitlement(
        code=LeaveCode.SCL,
        annual_days=15.0,
        carries_forward=False,
        continuous_count=False,
    ),
    "EL": LeaveEntitlement(
        code=LeaveCode.EL,
        annual_days=30.0,
        carries_forward=True,
        continuous_count=True,
    ),
    "VL": LeaveEntitlement(
        code=LeaveCode.VL,
        annual_days=60.0,
        carries_forward=False,
        continuous_count=True,
    ),
    "COL": LeaveEntitlement(
        code=LeaveCode.COL,
        annual_days=20.0,
        carries_forward=True,
        continuous_count=True,
    ),
}


def requested_days(start_date: date, end_date: date) -> int:
    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")
    return (end_date - start_date).days + 1


def validate_substitute_eligibility(applicant_id: int, substitute_id: int) -> None:
    if applicant_id == substitute_id:
        raise ValueError("Applicant cannot be their own substitute.")


def check_date_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    return start_a <= end_b and start_b <= end_a


def validate_balance_sufficiency(
    current_balance: float | int,
    requested_days_count: float | int,
) -> None:
    if requested_days_count > current_balance:
        raise ValueError("Insufficient leave balance")


def is_valid_transition(current_status: str, target_status: str) -> bool:
    allowed_transitions = {
        "AWAITING_SUBSTITUTE": ["AWAITING_APPROVAL", "WITHDRAWN"],
        "AWAITING_APPROVAL": ["APPROVED", "REJECTED", "WITHDRAWN"],
        "APPROVED": ["CANCELLED"],
    }
    return target_status in allowed_transitions.get(current_status, [])
