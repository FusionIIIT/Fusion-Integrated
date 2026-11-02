"""Hostel announcements and notice board services (CFR-HM-030, HM-UC-031, 032, BR-HM-029..031)."""

from __future__ import annotations

from datetime import date

from django.db import transaction

from modules.hostel.domain.constants import NoticeAudience, NotificationEventType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, HostelNotice, RoomAllotment
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def publish_notice(
    hostel_id: int,
    title: str,
    content: str,
    publisher_user_id: int,
    target_audience: str = NoticeAudience.ALL.value,
    expires_at: date | None = None,
) -> HostelNotice:
    """CFR-HM-030, HM-UC-031, BR-HM-029: Caretaker/Warden publishes notice for assigned hostel."""
    if not title or not title.strip():
        raise ValidationError("Title is required for notice")
    if not content or not content.strip():
        raise ValidationError("Content is required for notice")

    hostel = Hostel.objects.get(id=hostel_id)

    notice = HostelNotice.objects.create(
        hostel=hostel,
        title=title.strip(),
        content=content.strip(),
        published_by_user_id=publisher_user_id,
        target_audience=target_audience,
        is_active=True,
        expires_at=expires_at,
    )

    # Notify residents of this hostel
    residents = RoomAllotment.objects.filter(hostel=hostel, status="active").values_list(
        "student_user_id", flat=True
    )
    for s_id in residents:
        emit_notification(
            recipient_user_id=s_id,
            title="New Hostel Notice",
            message=f"{hostel.code}: {notice.title}",
            event_type=NotificationEventType.NOTICE_PUBLISHED,
            link="/hostel/notices",
        )

    return notice
