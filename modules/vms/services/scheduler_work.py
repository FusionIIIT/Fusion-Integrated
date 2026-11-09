"""Lifecycle work run by the beat (UC-037, UC-040, BW-VMS-03, BR-062).

Timing comes from the policy that applied when the request was made
(`policy.snapshot_for`, BR-129), never from the policy in force today.
Decision D-5: one reminder at `reminder_after_hours` (50 % of the timeout by
default), expiry at `approval_timeout_hours`.

`pending` requests expire, and so do pre-registered (urgent) requests still
`awaiting_admin`. A walk-in contingency stays `awaiting_admin` until an Admin
decides it (BR-050): the state table has no expiry move for it.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from modules.vms.domain import request_state as rs
from modules.vms.models import VisitRequest
from modules.vms.services import delivery, policy
from modules.vms.services.common import audit, notify

log = logging.getLogger("fusion.vms.scheduler")


def _kind(req: VisitRequest) -> str:
    return rs.kind_for_source(req.source)


def _expiry_at(req: VisitRequest, snap) -> datetime:
    return req.expires_at or req.created_at + timedelta(hours=snap.approval_timeout_hours)


def _reminder_at(req: VisitRequest, snap) -> datetime:
    hours = snap.reminder_after_hours or snap.approval_timeout_hours / 2
    hours = min(hours, snap.approval_timeout_hours)
    return req.created_at + timedelta(hours=hours)


def send_reminders(now: datetime | None = None) -> int:
    """Remind the host once per pending request, and the admins once per urgent
    request awaiting admin approval (UC-040). Idempotent."""
    now = now or timezone.now()
    ids = list(VisitRequest.objects.filter(
        Q(status=VisitRequest.Status.PENDING)
        | Q(status=VisitRequest.Status.AWAITING_ADMIN, is_urgent=True),
        reminded_at__isnull=True,
    ).values_list("pk", flat=True))
    sent = 0
    for pk in ids:
        try:
            with transaction.atomic():
                req = (VisitRequest.objects.select_for_update().select_related("visitor")
                       .get(pk=pk))
                to_admins = (req.status == VisitRequest.Status.AWAITING_ADMIN
                             and req.is_urgent)
                if (req.status != VisitRequest.Status.PENDING and not to_admins) \
                        or req.reminded_at:
                    continue
                snap = policy.snapshot_for(req)
                if now < _reminder_at(req, snap) or now >= _expiry_at(req, snap):
                    continue
                if to_admins:
                    delivery.notify_role_holders(
                        topic="request.reminder",
                        dedupe_key=f"request.reminder:{req.pk}:admin", roles=("admin",),
                        subject="Reminder: an urgent visit request awaits approval",
                        body=(f"The urgent request for {req.visitor.full_name} "
                              f"({req.purpose}) is still awaiting an Admin decision. "
                              "It expires automatically if it is not decided."))
                else:
                    notify.enqueue(
                        topic="request.reminder", dedupe_key=f"request.reminder:{req.pk}",
                        user_id=req.host_user_id, channels=("inapp", "email"),
                        subject="Reminder: a visit request awaits your decision",
                        body=(f"{req.visitor.full_name} has asked to visit you "
                              f"({req.purpose}). The request expires automatically if it "
                              "is not decided."))
                req.reminded_at = now
                req.save(update_fields=["reminded_at"])
                sent += 1
        except Exception:
            log.exception("vms.scheduler.reminder_failed request=%s", pk)
    return sent


def expire_pending(now: datetime | None = None) -> int:
    """Expire pending requests past their deadline (BR-062, BW-VMS-03). Idempotent."""
    now = now or timezone.now()
    waiting = (Q(status=VisitRequest.Status.PENDING)
               | (Q(status=VisitRequest.Status.AWAITING_ADMIN)
                  & ~Q(source=VisitRequest.Source.WALK_IN)))
    ids = list(VisitRequest.objects.filter(waiting).values_list("pk", flat=True))
    expired = 0
    for pk in ids:
        try:
            with transaction.atomic():
                req = (VisitRequest.objects.select_for_update().select_related("visitor")
                       .get(pk=pk))
                if req.status not in (VisitRequest.Status.PENDING,
                                      VisitRequest.Status.AWAITING_ADMIN):
                    continue
                snap = policy.snapshot_for(req)
                if now < _expiry_at(req, snap):
                    continue
                to = rs.next_state(_kind(req), req.status, rs.AUTO_EXPIRE, rs.SYSTEM)
                before = req.status
                req.status, req.decided_at = to, now
                req.decision_note = (
                    f"Expired: no decision within {snap.approval_timeout_hours} hours.")
                req.save(update_fields=["status", "decided_at", "decision_note"])
                audit.record(actor=None, action="vms.request.expired", entity=req,
                             detail={"from": before, "to": to,
                                     "policy_version": snap.version,
                                     "timeout_hours": snap.approval_timeout_hours})
                subject = "Visit request expired"
                body = (f"The visit request for {req.visitor.full_name} ({req.purpose}) "
                        "expired because it was not decided in time.")
                notify.enqueue(topic="request.expired",
                               dedupe_key=f"request.expired:{req.pk}:visitor",
                               visitor=req.visitor, subject=subject, body=body,
                               channels=("inapp", "email"))
                notify.enqueue(topic="request.expired", dedupe_key=f"request.expired:{req.pk}:host",
                               user_id=req.host_user_id, subject=subject, body=body,
                               channels=("inapp", "email"))
                expired += 1
        except rs.InvalidTransition:
            log.warning("vms.scheduler.no_expiry_move request=%s", pk)
        except Exception:
            log.exception("vms.scheduler.expiry_failed request=%s", pk)
    return expired
