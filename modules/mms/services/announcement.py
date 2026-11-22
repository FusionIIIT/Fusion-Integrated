"""Announcements (BR-MMS-032/033; UC-022/023)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.mms.models import Announcement
from modules.mms.services import authz, notifications


def publish(actor, title: str, body: str) -> Announcement:
    """BR-MMS-032: only the active Caretaker or Warden publishes."""
    authz.require(actor, "mms.announcement.publish")
    with transaction.atomic():
        ann = Announcement.objects.create(
            title=title, body=body, publisher_user_id=actor.user_id, published_at=timezone.now()
        )
        notifications.enqueue(
            topic="announcement.published",
            dedupe_key=f"announcement.published:{ann.pk}",
            subject="New mess announcement",
            body=f"{title}\n\n{body}",
            recipient_email="mms-broadcast@invalid",
            payload={"audience": "students"},
        )
    return ann
