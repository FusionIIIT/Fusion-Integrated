"""hreis public surface. The ONLY thing other modules may import (ADR-0013)."""
from __future__ import annotations

from dataclasses import dataclass

from modules.hreis.models import EmployeeServiceRecord


@dataclass(frozen=True)
class EmployeeRecordDTO:
    user_id: int
    employee_id: str
    department: str
    designation: str
    category: str
    retirement_status: str
    is_active: bool


def get_employee_record(user_id: int) -> EmployeeRecordDTO | None:
    rec = EmployeeServiceRecord.objects.filter(user_id=user_id).first()
    if not rec:
        return None
    return EmployeeRecordDTO(
        user_id=rec.user_id,
        employee_id=rec.employee_id,
        department=rec.department,
        designation=rec.designation,
        category=rec.category,
        retirement_status=rec.retirement_status,
        is_active=rec.is_active,
    )


def get_leave_balance(user_id: int, leave_type: str) -> float | None:
    rec = EmployeeServiceRecord.objects.filter(user_id=user_id).first()
    if not rec or not rec.leave_balances:
        return None
    return rec.leave_balances.get(leave_type)
