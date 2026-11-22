"""Read-only public contracts for modules that need HR-owned employment facts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.hr.models import EmployeeRecord


@dataclass(frozen=True)
class EmploymentDTO:
    user_id: int
    employee_category: str
    employment_status: str
    department: str
    designation: str
    appointment_type: str
    appointment_start_date: str | None
    appointment_end_date: str | None
    appointment_details: dict


def get_employments(user_ids: Sequence[int]) -> dict[int, EmploymentDTO]:
    """Return a batched mapping; unknown employee ids are absent."""
    ids = {int(user_id) for user_id in user_ids if user_id is not None}
    if not ids:
        return {}
    rows = EmployeeRecord.objects.filter(user_id__in=ids)
    return {
        row.user_id: EmploymentDTO(
            user_id=row.user_id,
            employee_category=row.employee_category,
            employment_status=row.employment_status,
            department=row.department,
            designation=row.designation,
            appointment_type=row.appointment_type,
            appointment_start_date=(
                row.appointment_start_date.isoformat() if row.appointment_start_date else None
            ),
            appointment_end_date=(
                row.appointment_end_date.isoformat() if row.appointment_end_date else None
            ),
            appointment_details=row.appointment_details,
        )
        for row in rows
    }
