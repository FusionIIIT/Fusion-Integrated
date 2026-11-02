"""Read side of the notification outbox/inbox (VMS-CFR-028, CFR-021, UC-015).

The in-app inbox is the `inapp` rows of `Notification`; there is no second table.
"""
from __future__ import annotations

from modules.vms.models import Notification, VisitLog, VisitRequest

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def clamp_limit(value, default: int = DEFAULT_LIMIT) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, MAX_LIMIT))


def _inbox(**owner):
    return Notification.objects.filter(channel=Notification.Channel.INAPP, **owner)


def inbox_for_user(user_id: int, *, unread_only: bool = False):
    qs = _inbox(recipient_user_id=user_id)
    return (qs.filter(read_at__isnull=True) if unread_only else qs).order_by("-created_at", "-id")


def inbox_for_visitor(visitor_id: int, *, unread_only: bool = False):
    qs = _inbox(recipient_visitor_id=visitor_id)
    return (qs.filter(read_at__isnull=True) if unread_only else qs).order_by("-created_at", "-id")


def unread_count_for_user(user_id: int) -> int:
    return inbox_for_user(user_id, unread_only=True).count()


def unread_count_for_visitor(visitor_id: int) -> int:
    return inbox_for_visitor(visitor_id, unread_only=True).count()


def outbox(*, status: str | None = None, topic: str | None = None):
    """Ops view over every channel (read-only)."""
    qs = Notification.objects.all()
    if status:
        qs = qs.filter(status=status)
    if topic:
        qs = qs.filter(topic=topic)
    return qs.order_by("-created_at", "-id")


def arrivals_for_host(user_id: int, limit: int = 20) -> list[dict]:
    """UC-015: the host's latest `visit.checked_in` notifications with request info.

    Convention (documented in services/delivery.py): the dedupe key of a
    check-in notification is ``visit.checked_in:<visit_log_id>[:...]``; the
    log gives the pass and so the request. A row whose key does not follow it
    is still listed, with ``request`` empty.
    """
    rows = list(_inbox(recipient_user_id=user_id, topic="visit.checked_in")
                .order_by("-created_at", "-id")[:limit])
    log_ids = {}
    for n in rows:
        parts = n.dedupe_key.split(":")
        if len(parts) >= 2 and parts[0] == "visit.checked_in" and parts[1].isdigit():
            log_ids[n.pk] = int(parts[1])
    logs = {lg.pk: lg for lg in VisitLog.objects.filter(pk__in=set(log_ids.values()))
            .select_related("visit_pass__visit_request__visitor")}
    out = []
    for n in rows:
        lg = logs.get(log_ids.get(n.pk))
        req: VisitRequest | None = lg.visit_pass.visit_request if lg else None
        out.append({
            "notification": n,
            "checked_in_at": lg.created_at if lg else n.created_at,
            "request": None if req is None else {
                "id": req.pk, "visitor_name": req.visitor.full_name,
                "purpose": req.purpose, "scheduled_start": req.scheduled_start,
                "scheduled_end": req.scheduled_end},
        })
    return out
