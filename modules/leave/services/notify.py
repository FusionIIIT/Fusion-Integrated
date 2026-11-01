"""In-app notices (BR-EL-032/033/035, PS §7). Keyed rows are written once."""
from __future__ import annotations

from collections.abc import Iterable

from modules.leave.models import LeaveNotification, LeaveRequest


def notify(user_ids: Iterable[int | None], kind: str, message: str, *,
           request: LeaveRequest | None = None, key: str | None = None) -> int:
    sent = 0
    for uid in sorted({u for u in user_ids if u}):
        if key:
            _, created = LeaveNotification.objects.get_or_create(
                idempotency_key=f"{key}:{uid}",
                defaults={"user_id": uid, "kind": kind, "message": message[:300],
                          "request": request})
            sent += int(created)
        else:
            LeaveNotification.objects.create(user_id=uid, kind=kind,
                                             message=message[:300], request=request)
            sent += 1
    return sent
