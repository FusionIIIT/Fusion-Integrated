"""Cross-module contracts for the Mess Management System (MMS).

All contract getters are plural and accept Sequence arguments (ADR-0004).
Zero cross-module foreign keys or internal model leaking.
"""

from collections.abc import Sequence
from typing import TypedDict

from modules.mms.domain.constants import RebateStatus
from modules.mms.models import MessRegistration, MessRoleAssignment, RebateRequest


class StudentRegistrationContract(TypedDict):
    id: int
    mess_name: str
    status: str
    start_date: str


class StudentRebateContract(TypedDict):
    id: int
    start_date: str
    end_date: str
    duration_days: int
    status: str


class ActiveRoleContract(TypedDict):
    id: int
    employee_id: int
    role: str
    start_date: str


def get_student_mess_registrations(
    student_ids: Sequence[int],
) -> dict[int, list[StudentRegistrationContract]]:
    """Return active and pending registrations for the requested students (ADR-0004)."""
    regs = MessRegistration.objects.filter(student_id__in=student_ids)
    results: dict[int, list[StudentRegistrationContract]] = {}
    for r in regs:
        results.setdefault(r.student_id, []).append(
            {
                "id": r.id,
                "mess_name": r.mess_name,
                "status": r.status,
                "start_date": r.start_date.isoformat(),
            }
        )
    return results


def get_student_approved_rebates(
    student_ids: Sequence[int],
) -> dict[int, list[StudentRebateContract]]:
    """Return approved rebates for the requested students (ADR-0004)."""
    rebates = RebateRequest.objects.filter(
        student_id__in=student_ids,
        status=RebateStatus.APPROVED.value,
    )
    results: dict[int, list[StudentRebateContract]] = {}
    for rb in rebates:
        results.setdefault(rb.student_id, []).append(
            {
                "id": rb.id,
                "start_date": rb.start_date.isoformat(),
                "end_date": rb.end_date.isoformat(),
                "duration_days": rb.duration_days,
                "status": rb.status,
            }
        )
    return results


def get_active_mess_roles(
    roles: Sequence[str],
) -> dict[str, list[ActiveRoleContract]]:
    """Return active staff role assignments for the requested roles (ADR-0004)."""
    assignments = MessRoleAssignment.objects.filter(role__in=roles, is_active=True)
    results: dict[str, list[ActiveRoleContract]] = {}
    for a in assignments:
        results.setdefault(a.role, []).append(
            {
                "id": a.id,
                "employee_id": a.employee_id,
                "role": a.role,
                "start_date": a.start_date.isoformat(),
            }
        )
    return results
