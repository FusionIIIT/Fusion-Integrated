"""Hostel notice and announcement services (3.11, CFR-HM-032, BR-HM-029..031)."""

from django.db import transaction
from ..domain.constants import NoticeCategory
from ..domain.errors import HostelDomainError
from ..models import Hostel, HostelNotice, RoomAllotment
from .notification_service import create_notification


@transaction.atomic
def publish_notice(
    publisher_user_id: int,
    publisher_role: str,
    title: str,
    body: str,
    hostel_id: int | None = None,
    category: str = NoticeCategory.GENERAL.value,
    is_pinned: bool = False,
) -> HostelNotice:
    """Caretaker or Warden publishes notice for assigned hostel (HM-UC-031, BR-HM-029)."""
    hostel = None
    if hostel_id:
        hostel = Hostel.objects.filter(id=hostel_id).first()
        if not hostel:
            raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    notice = HostelNotice.objects.create(
        hostel=hostel,
        title=title.strip(),
        body=body.strip(),
        category=category,
        is_pinned=is_pinned,
        published_by_user_id=publisher_user_id,
        published_by_role=publisher_role,
        is_active=True,
    )

    # Notify all residents of this hostel (or all students if institution-wide)
    allotments = RoomAllotment.objects.filter(is_active=True)
    if hostel:
        allotments = allotments.filter(hostel=hostel)
    student_user_ids = allotments.values_list("student_user_id", flat=True).distinct()

    for uid in student_user_ids:
        create_notification(
            recipient_user_id=uid,
            event_type="notice_published",
            title=f"New Notice: {title}",
            message=body[:100] + ("..." if len(body) > 100 else ""),
            reference_id=str(notice.id),
        )

    return notice
