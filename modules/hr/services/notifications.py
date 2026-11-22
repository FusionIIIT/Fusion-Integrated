from __future__ import annotations

from uuid import uuid4

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.hr.models import EmployeeRecord, HRNotification
from modules.hr.services.common import audit


def enqueue(
    *,
    recipient_user_id: int,
    topic: str,
    dedupe_key: str,
    subject: str,
    body: str,
    payload: dict | None = None,
) -> HRNotification | None:
    if recipient_user_id <= 0 or not topic or not dedupe_key or not subject:
        raise ValueError("A notification requires a recipient, topic, key, and subject.")
    try:
        with transaction.atomic():
            return HRNotification.objects.create(
                recipient_user_id=recipient_user_id,
                topic=topic,
                dedupe_key=dedupe_key,
                subject=subject[:160],
                body=body[:2000],
                payload=payload or {},
            )
    except IntegrityError:
        return None


@transaction.atomic
def publish_notice(
    *, actor, recipient_user_ids: list[int], subject: str, body: str
) -> list[HRNotification]:
    from modules.hr.services import authz

    authz.require(actor, "hr.notification.manage")
    user_ids = list(dict.fromkeys(recipient_user_ids))
    if not user_ids or any(user_id <= 0 for user_id in user_ids):
        raise ConflictError(
            "At least one valid employee recipient is required.", code="notice_recipients_required"
        )
    people = directory.get_users(user_ids)
    employees = set(
        EmployeeRecord.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True)
    )
    if (
        len(people) != len(user_ids)
        or employees != set(user_ids)
        or any(people[user_id].kind not in {"faculty", "staff"} for user_id in user_ids)
    ):
        raise ConflictError(
            "All notice recipients must be employees.", code="invalid_notice_recipient"
        )

    publication_id = uuid4().hex
    notifications = []
    for user_id in user_ids:
        notification = enqueue(
            recipient_user_id=user_id,
            topic="hr.notice",
            dedupe_key=f"notice:{publication_id}:{user_id}",
            subject=subject,
            body=body,
            payload={"published_by_user_id": actor.user_id},
        )
        if notification is None:
            raise ConflictError("The notice could not be published.", code="notice_publish_failed")
        audit(
            actor=actor,
            entity_type="notification",
            entity_id=notification.pk,
            action="notice.published",
            details={"recipient_user_id": user_id, "subject": subject},
        )
        notifications.append(notification)
    return notifications
