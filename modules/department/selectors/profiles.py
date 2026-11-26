from modules.department.domain.roles import role_kind
from modules.department.models import CourseRoster, DepartmentProfile, OfficialChangeProposal
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.directory import contracts as directory


def visible_profiles(actor):
    """Returns visible profiles based on the actor's role."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return DepartmentProfile.objects.filter(
            department_id__in=department_ids_for_role(actor, kind), is_active=True
        )
    if kind in ("student", "faculty"):
        user_record = directory.get_users([actor.user_id]).get(actor.user_id)
        if not user_record:
            return DepartmentProfile.objects.none()
        return DepartmentProfile.objects.filter(
            department__code__in=member_department_codes(actor), is_active=True
        )
    return DepartmentProfile.objects.none()


def is_in_course(faculty_user_id, student_user_id):
    """Checks if a faculty member is rostered with a student in any course."""
    return CourseRoster.objects.filter(
        faculty_user_id=faculty_user_id, student_user_id=student_user_id
    ).exists()


def visible_official_changes(actor):
    """Returns official change proposals visible to the actor."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return OfficialChangeProposal.objects.filter(
            department_id__in=department_ids_for_role(actor, kind)
        )
    return OfficialChangeProposal.objects.none()


def visible_rosters(actor):
    """Returns course rosters visible to the actor."""
    kind = role_kind(actor.active_role)
    if kind == "dept_admin":
        return CourseRoster.objects.filter(
            department_id__in=department_ids_for_role(actor, "dept_admin")
        )
    return CourseRoster.objects.none()
