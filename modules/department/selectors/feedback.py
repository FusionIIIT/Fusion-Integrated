from modules.department.domain.roles import role_kind
from modules.department.models import Feedback
from modules.department.selectors.scoping import department_ids_for_role


def visible_feedback(actor):
    """Returns feedback visible to the actor based on their role."""
    kind = role_kind(actor.active_role)

    if kind == "student" or kind == "faculty":
        return Feedback.objects.filter(
            submitter_user_id=actor.user_id
        ).select_related("department")

    if kind == "dept_admin":
        return Feedback.objects.filter(
            department_id__in=department_ids_for_role(actor, "dept_admin")
        ).select_related("department")

    if kind == "hod":
        return Feedback.objects.filter(
            department_id__in=department_ids_for_role(actor, "hod")
        ).exclude(
            state="new"
        ).select_related("department")

    return Feedback.objects.none()
