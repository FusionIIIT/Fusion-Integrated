"""The ONLY door other modules may reach into the mess management module through.

Enforced by .importlinter and ops/checks/contracts_are_plural.py.
All cross-module getters are strictly plural (accepting a Sequence).
"""
from collections.abc import Sequence
from datetime import date

MODULE_CODE = "mess_module"

PERMISSION_ROLE_MANAGE = "mess_module.role.manage"
PERMISSION_REGISTRATION_SUBMIT = "mess_module.registration.submit"
PERMISSION_REGISTRATION_REVIEW = "mess_module.registration.review"
PERMISSION_MENU_MANAGE = "mess_module.menu.manage"
PERMISSION_MENU_VIEW = "mess_module.menu.view"
PERMISSION_REBATE_APPLY = "mess_module.rebate.apply"
PERMISSION_REBATE_REVIEW = "mess_module.rebate.review"
PERMISSION_FEEDBACK_SUBMIT = "mess_module.feedback.submit"
PERMISSION_FEEDBACK_VIEW = "mess_module.feedback.view"
PERMISSION_OVERSIGHT_VIEW = "mess_module.oversight.view"


def get_student_mess_registrations(student_ids: Sequence[int]) -> dict[int, list[dict]]:
    """Retrieve mess registration records for multiple students (plural contract)."""
    from modules.mms.models import MessRegistration

    registrations = MessRegistration.objects.filter(student_id__in=student_ids)
    result: dict[int, list[dict]] = {sid: [] for sid in student_ids}
    for r in registrations:
        result.setdefault(r.student_id, []).append({
            "id": r.id,
            "student_id": r.student_id,
            "mess_name": r.mess_name,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "status": r.status,
            "created_at": r.created_at,
        })
    return result


def get_student_approved_rebates(
    student_ids: Sequence[int],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[int, list[dict]]:
    """Retrieve approved mess rebates for multiple students (plural contract)."""
    from modules.mms.models import RebateRequest

    qs = RebateRequest.objects.filter(student_id__in=student_ids, status="APPROVED")
    if start_date:
        qs = qs.filter(end_date__gte=start_date)
    if end_date:
        qs = qs.filter(start_date__lte=end_date)

    result: dict[int, list[dict]] = {sid: [] for sid in student_ids}
    for r in qs:
        result.setdefault(r.student_id, []).append({
            "id": r.id,
            "student_id": r.student_id,
            "mess_name": r.mess_name,
            "start_date": r.approved_start_date or r.start_date,
            "end_date": r.approved_end_date or r.end_date,
            "duration_days": r.duration_days,
        })
    return result


def get_active_mess_roles(role_names: Sequence[str]) -> dict[str, dict | None]:
    """Retrieve current active role assignments for requested roles (plural contract)."""
    from modules.mms.models import MessRoleAssignment

    assignments = MessRoleAssignment.objects.filter(role__in=role_names, is_active=True)
    result: dict[str, dict | None] = dict.fromkeys(role_names)
    for a in assignments:
        result[a.role] = {
            "id": a.id,
            "employee_id": a.employee_id,
            "role": a.role,
            "start_date": a.start_date,
            "end_date": a.end_date,
            "assigned_by_id": a.assigned_by_id,
        }
    return result
