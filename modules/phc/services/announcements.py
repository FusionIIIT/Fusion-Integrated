"""Health announcement publishing service (CFR-PHC-009, AFR-PHC-033; UC-PHC-12)."""
from django.utils import timezone

from modules.phc.models.announcements import HealthAnnouncement


def publish_health_announcement(
    title: str,
    content: str,
    priority: str,
    published_by_user_id: int,
) -> HealthAnnouncement:
    return HealthAnnouncement.objects.create(
        title=title.strip(),
        content=content.strip(),
        priority=priority,
        published_date=timezone.now(),
        is_active=True,
        published_by_user_id=published_by_user_id,
    )
