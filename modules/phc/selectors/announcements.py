"""Health announcement selectors (CFR-PHC-009, AFR-PHC-033)."""
from modules.phc.models.announcements import HealthAnnouncement


def list_active_announcements() -> list[HealthAnnouncement]:
    return list(HealthAnnouncement.objects.filter(is_active=True).order_by("-priority", "-published_date"))


def list_all_announcements() -> list[HealthAnnouncement]:
    return list(HealthAnnouncement.objects.all().order_by("-published_date"))
