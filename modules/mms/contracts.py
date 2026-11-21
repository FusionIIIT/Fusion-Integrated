"""Cross-module contracts for MMS conforming to ADR-0004 (Plural Getters)."""

from typing import Any, Dict, List, Sequence
from modules.mms.models import MessRegistration, MessRoleAssignment, RebateRequest


def get_student_mess_registrations(student_ids: Sequence[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Return mess registrations for given student IDs."""
    qs = MessRegistration.objects.filter(student_id__in=student_ids).select_related("window")
    results = [
        {
            "id": reg.id,
            "student_id": reg.student_id,
            "mess_name": reg.mess_name,
            "semester": reg.window.semester,
            "status": reg.status,
            "registered_date": str(reg.registered_date),
        }
        for reg in qs
    ]
    return {"results": results}


def get_student_approved_rebates(student_ids: Sequence[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Return approved rebates for given student IDs."""
    qs = RebateRequest.objects.filter(student_id__in=student_ids, status="APPROVED")
    results = [
        {
            "id": r.id,
            "student_id": r.student_id,
            "mess_name": r.mess_name,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "duration_days": r.duration_days,
        }
        for r in qs
    ]
    return {"results": results}


def get_active_mess_roles(employee_ids: Sequence[int]) -> Dict[str, List[Dict[str, Any]]]:
    """Return active mess roles assigned to given employee IDs."""
    qs = MessRoleAssignment.objects.filter(employee_id__in=employee_ids, is_active=True)
    results = [
        {
            "id": role.id,
            "employee_id": role.employee_id,
            "role": role.role,
            "mess_name": role.mess_name,
        }
        for role in qs
    ]
    return {"results": results}

