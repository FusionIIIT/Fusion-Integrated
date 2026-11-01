from django.db.models import Q

from modules.department.domain.roles import role_kind
from modules.department.models import AcademicProgram, LabResource, TimetableSlot
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.directory import contracts as directory


def visible_slots(actor):
    """Returns timetable slots visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return TimetableSlot.objects.filter(
            department_id__in=department_ids_for_role(actor, kind)
        )
    if kind == "faculty":
        return TimetableSlot.objects.filter(
            department__code__in=member_department_codes(actor)
        )
    if kind == "student":
        user_record = directory.get_users([actor.user_id]).get(actor.user_id)
        if not user_record:
            return TimetableSlot.objects.none()
        return TimetableSlot.objects.filter(
            Q(programme__isnull=True) | Q(programme=user_record.programme),
            Q(batch_year__isnull=True) | Q(batch_year=user_record.batch_year)
        )
    return TimetableSlot.objects.none()


def visible_labs(actor):
    """Returns lab resources visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind == "faculty":
        return LabResource.objects.filter(
            department__code__in=member_department_codes(actor)
        )
    if kind in ("hod", "dept_admin"):
        return LabResource.objects.filter(
            department_id__in=department_ids_for_role(actor, "dept_admin")
        )
    return LabResource.objects.none()


def visible_programs(actor):
    """Returns academic programs visible to the actor based on their role."""
    kind = role_kind(actor.active_role)
    if kind == "student":
        user_record = directory.get_users([actor.user_id]).get(actor.user_id)
        if not user_record:
            return AcademicProgram.objects.none()
        return AcademicProgram.objects.filter(
            department__code__in=member_department_codes(actor)
        )
    if kind in ("hod", "dept_admin"):
        return AcademicProgram.objects.filter(
            department_id__in=department_ids_for_role(actor, "dept_admin")
        )
    return AcademicProgram.objects.none()
