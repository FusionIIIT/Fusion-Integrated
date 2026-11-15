"""Alert lifecycle.

VMS-BR-040: a failed gate validation never opens a SECOND alert while one
of the same type for the same visitor is already open — the open one is
returned instead.

VMS-BR-002: an alert auto-closes on gate entrance; if that close is not
effective (a HIGH-severity blacklist hit still needs a human) it remains
open.

VMS-BR-028: a successful validation auto-closes the visitor's open alerts.
"""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import Alert, VisitLog
from modules.vms.services.errors import NotFoundError


def open_alert(*, alert_type: str, message: str,
               severity: str = "MEDIUM", visitor_id: int | None = None,
               visit_id: int | None = None, pass_id: int | None = None,
               zone_code: str = "", dedupe: bool = True) -> Alert:
    """Open an alert, or hand back the one already open (VMS-BR-040)."""
    if dedupe and visitor_id is not None:
        existing = (Alert.objects
                    .filter(visitor_id=visitor_id, alert_type=alert_type,
                            status="OPEN")
                    .order_by("-opened_at")
                    .first())
        if existing is not None:
            return existing
    return Alert.objects.create(
        alert_type=alert_type, severity=severity, message=message,
        visitor_id=visitor_id, visit_id=visit_id, pass_id=pass_id,
        zone_code=zone_code)


def close_alert(alert: Alert, *, auto: bool = False,
                actor_user_id: int | None = None) -> Alert:
    if alert.status == "CLOSED":
        return alert                      # already closed; nothing to do
    alert.status = "CLOSED"
    alert.closed_at = timezone.now()
    alert.auto_closed = auto
    alert.closed_by_user_id = None if auto else actor_user_id
    alert.save(update_fields=["status", "closed_at", "auto_closed",
                              "closed_by_user_id", "updated_at"])
    return alert


def close_alerts_on_entry(visitor_id: int, *, visit_id: int | None = None,
                          actor_user_id: int | None = None) -> list[Alert]:
    """VMS-BR-002 + VMS-BR-028: successful gate entrance/validation closes
    what can be closed automatically. A HIGH-severity blacklist hit is NOT
    effective that way — it stays open for a human (VMS-BR-002)."""
    closed: list[Alert] = []
    open_rows = Alert.objects.filter(visitor_id=visitor_id, status="OPEN")
    for alert in open_rows:
        if alert.alert_type == "BLACKLIST_HIT" and alert.severity == "HIGH":
            continue                      # not effective — remains open
        close_alert(alert, auto=True, actor_user_id=actor_user_id)
        closed.append(alert)
        if visit_id is not None:
            VisitLog.objects.create(
                visit_id=visit_id, visitor_id=visitor_id,
                event_type="ALERT_CLOSED", occurred_at=timezone.now(),
                details={"alert_id": alert.id, "auto": True})
    return closed


def close_alert_for_user(alert_id: int, *, actor_user_id: int | None) -> Alert:
    try:
        alert = Alert.objects.get(pk=alert_id)
    except Alert.DoesNotExist as exc:
        raise NotFoundError("Alert not found.") from exc
    return close_alert(alert, actor_user_id=actor_user_id)
