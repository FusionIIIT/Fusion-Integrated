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
