"""In-app notices (SRS-EL-054, SRS-EL-061)."""
from __future__ import annotations

from modules.elm.models import LeaveRequest, Notification


def to_user(user_id: int | None, req: LeaveRequest | None, message: str) -> None:
    if user_id is None:
        return
    Notification.objects.create(recipient_user_id=user_id, request=req, message=message)


def to_role(role: str, req: LeaveRequest | None, message: str) -> None:
    if not role:
        return
    Notification.objects.create(recipient_role=role, request=req, message=message)
