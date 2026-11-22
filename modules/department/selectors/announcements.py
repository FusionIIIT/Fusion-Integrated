from django.db.models import QuerySet

from modules.department.models import Announcement


def active_announcements() -> QuerySet[Announcement]:
    """Return published announcements that have not been hidden or deleted."""
    return Announcement.objects.filter(
        published_at__isnull=False,
        is_hidden=False,
        deleted_at__isnull=True,
    ).order_by("-published_at", "-created_at")


def announcement_for_management(announcement_id: int) -> Announcement | None:
    """Retrieve an announcement, including drafts, for an authorized manager."""
    return Announcement.objects.filter(
        pk=announcement_id,
        deleted_at__isnull=True,
    ).first()


def relevant_announcements(*, role=None, program=None, academic_year=None):
    """Return published announcements filtered by audience matching."""
    qs = active_announcements()
    filtered_ids = []
    for ann in qs:
        role_match = not ann.target_roles or (role in ann.target_roles)
        prog_match = not ann.target_programs or (program in ann.target_programs)
        year_match = not ann.target_academic_years or (academic_year in ann.target_academic_years)
        if role_match and prog_match and year_match:
            filtered_ids.append(ann.pk)
    return qs.filter(pk__in=filtered_ids)
