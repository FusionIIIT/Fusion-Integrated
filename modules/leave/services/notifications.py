"""In-app notifications the ELM writes for the desks it hands work to
(BR-EL-035). Email/outbox delivery is the platform's concern, not a rule."""
from __future__ import annotations

from django.utils import timezone

from modules.leave.models import LeaveNotification
from modules.leave.services import authz


def notify(user_id: int | None, kind: str, message: str,
           request=None) -> LeaveNotification | None:
    if user_id is None:
        return None
    return LeaveNotification.objects.create(
        user_id=user_id, kind=kind, message=message, request=request)


def unread_for(user_id: int) -> list[LeaveNotification]:
    return list(LeaveNotification.objects
                .filter(user_id=user_id, read_at__isnull=True)[:200])


def mark_read(actor, ids: list[int] | None = None) -> int:
    authz.require(actor, "leave.request.view_self")
    rows = LeaveNotification.objects.filter(
        user_id=getattr(actor, "user_id", None), read_at__isnull=True)
    if ids:
        rows = rows.filter(pk__in=ids)
    return rows.update(read_at=timezone.now())
