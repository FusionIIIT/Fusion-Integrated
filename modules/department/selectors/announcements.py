from modules.department.domain.announcements import is_relevant
from modules.department.domain.roles import role_kind
from modules.department.models import Announcement
from modules.department.selectors.scoping import department_ids_for_role, member_department_codes
from modules.directory import contracts as directory


def visible_announcements(actor):
    """Returns announcements visible to the actor based on their role and department."""
    kind = role_kind(actor.active_role)
    if kind in ("hod", "dept_admin"):
        return Announcement.objects.filter(
            status="active",
            department_id__in=department_ids_for_role(actor, kind)
        )
    if kind in ("student", "faculty"):
        user_record = directory.get_users([actor.user_id]).get(actor.user_id)
        if not user_record:
            return Announcement.objects.none()

        queryset = Announcement.objects.filter(
            status="active",
            department__code__in=member_department_codes(actor)
        ).select_related("department")

        collected_keys = []
        for ann in queryset:
            if is_relevant(
                ann.target_roles,
                ann.target_programme,
                ann.target_batch_year,
                kind,
                user_record.programme,
                user_record.batch_year,
            ):
                collected_keys.append(ann.pk)

        return Announcement.objects.filter(pk__in=collected_keys)
    return Announcement.objects.none()

def manageable_announcements(actor):
    """Returns active announcements manageable by the actor if they are an HOD."""
    if role_kind(actor.active_role) != "hod":
        return Announcement.objects.none()
    return Announcement.objects.filter(
        status="active",
        department_id__in=department_ids_for_role(actor, "hod")
    )
