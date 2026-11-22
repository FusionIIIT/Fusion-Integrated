"""Notification delivery (VMS-CFR-028, BR-174, decision D-8).

`services.common.notify.enqueue` only writes rows; this module sends them.

Topic catalogue (the contract with the other lanes). Dedupe key convention:
``<topic>:<entity id>[:<qualifier>]``; enqueue appends ``:<channel>``.

=====================================  ===========================  ================
Topic                                  Recipient                    Channels
=====================================  ===========================  ================
visitor.login_otp                      visitor                      email
request.submitted                      host                         inapp,email
request.approved/rejected, pass.issued visitor                      inapp,email,sms
request.reminder                       host                         inapp,email
request.expired                        visitor + host               inapp,email
visit.checked_in                       host                         inapp
visit.checked_out                      host                         inapp
gate.denied, zone.violation,
blacklist.hit                          security/admin by scope      inapp,email
pass.terminated                        visitor, security            inapp,sms
muster.alert                           on-site visitors             sms,inapp
extension.decided                      visitor, host                inapp,email
=====================================  ===========================  ================

Conventions other lanes must follow:

* ``visit.checked_in`` uses dedupe key ``visit.checked_in:<visit_log_id>`` so
  ``GET notify/arrivals`` can join the notification to the request (UC-015).
* Security/admin topics go through `notify_role_holders`, which resolves the
  active `RoleAssignment`s (scoped by zone/gate) at call time, so a reassigned
  guard is not notified (BR-182).

Channel rules: ``inapp`` is marked sent (the row is the inbox); ``email`` goes
through Django `send_mail` to the visitor's address or the directory email;
``sms``/``push`` are *skipped* unless ``IntegrationSetting("sms_gateway")`` /
``("push")`` exists, and then only if a sender was registered with
`register_sender` (no vendor is built in).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.vms.models import IntegrationSetting, Notification, RoleAssignment
from modules.vms.services.common import audit, notify

log = logging.getLogger("fusion.vms.delivery")

MAX_ATTEMPTS = 5
#: Wait after the n-th failed attempt (minutes): 1, 5, 30, 30, ...
BACKOFF_MINUTES = (1, 5, 30)
GATEWAY_KEYS = {"sms": "sms_gateway", "push": "push"}

#: channel -> callable(notification, address) used when a gateway is configured.
_SENDERS: dict = {}


def register_sender(channel: str, fn) -> None:
    _SENDERS[channel] = fn


@dataclass
class DeliveryReport:
    sent: int = 0
    skipped: int = 0
    retrying: int = 0
    failed: int = 0
    locked: int = 0

    def __str__(self) -> str:
        return (f"sent={self.sent} skipped={self.skipped} retrying={self.retrying} "
                f"failed={self.failed} locked={self.locked}")


class _Skip(Exception):
    pass


# --- retry backoff --------------------------------------------------------------------

def _backoff_ready(row: Notification, now: datetime) -> bool:
    return row.next_attempt_at is None or row.next_attempt_at <= now


def _next_attempt(attempts: int, now: datetime) -> datetime:
    return now + timedelta(minutes=BACKOFF_MINUTES[min(attempts, len(BACKOFF_MINUTES)) - 1])


# --- addressing -----------------------------------------------------------------------

def _address(row: Notification, emails: dict[int, str]) -> str:
    if row.channel == Notification.Channel.EMAIL:
        if row.recipient_visitor_id:
            return row.recipient_visitor.email
        return emails.get(row.recipient_user_id, "")
    if row.channel == Notification.Channel.SMS and row.recipient_visitor_id:
        return row.recipient_visitor.phone
    return ""


def _gateway_configured(channel: str) -> bool:
    key = GATEWAY_KEYS.get(channel)
    return bool(key) and IntegrationSetting.objects.filter(key=key).exists()


def _send(row: Notification, address: str) -> None:
    ch = row.channel
    if ch == Notification.Channel.INAPP:
        return
    if ch == Notification.Channel.EMAIL:
        if not address:
            raise _Skip("recipient has no email address")
        send_mail(subject=row.subject, message=row.body,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[address], fail_silently=False)
        return
    if not _gateway_configured(ch):
        raise _Skip(f"{ch} gateway not configured")
    sender = _SENDERS.get(ch)
    if sender is None:
        raise _Skip(f"{ch} gateway configured but no sender registered")
    if not address:
        raise _Skip(f"recipient has no {ch} address")
    sender(row, address)


def _check_still_in_scope(row: Notification, now: datetime) -> None:
    """Role-holder notices go only to users who still hold the role (BR-182)."""
    scope = row.detail or {}
    if not scope.get("roles") or row.recipient_user_id is None:
        return
    holders = role_holder_ids(tuple(scope["roles"]), zone_id=scope.get("zone_id"),
                              gate_id=scope.get("gate_id"), at=now)
    if row.recipient_user_id not in holders:
        raise _Skip("recipient no longer holds the role for this scope")


def _deliver_one(pk: int, emails: dict[int, str], now: datetime, report: DeliveryReport) -> None:
    with transaction.atomic():
        row = (Notification.objects.select_for_update(skip_locked=True)
               .filter(pk=pk, status=Notification.Status.PENDING).first())
        if row is None:
            report.locked += 1      # taken by another worker, or already done
            return
        if not _backoff_ready(row, now):
            return
        try:
            _check_still_in_scope(row, now)
            _send(row, _address(row, emails))
        except _Skip as why:
            row.status, row.last_error = Notification.Status.SKIPPED, str(why)[:500]
            report.skipped += 1
        except Exception as exc:                                     # noqa: BLE001
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:500]
            if row.attempts >= MAX_ATTEMPTS:
                row.status = Notification.Status.FAILED
                row.next_attempt_at = None
                report.failed += 1
            else:
                row.next_attempt_at = _next_attempt(row.attempts, now)
                report.retrying += 1
            log.warning("vms.notify.error id=%s attempts=%s %s", row.pk, row.attempts, exc)
        else:
            row.status, row.last_error = Notification.Status.SENT, ""
            row.next_attempt_at = None
            row.sent_at = now
            row.attempts += 1
            report.sent += 1
        row.save(update_fields=["status", "attempts", "last_error", "next_attempt_at", "sent_at"])


def _user_emails(ids: list[int]) -> dict[int, str]:
    user_ids = set(Notification.objects.filter(
        pk__in=ids, channel=Notification.Channel.EMAIL, recipient_user_id__isnull=False)
        .values_list("recipient_user_id", flat=True))
    if not user_ids:
        return {}
    try:
        return {uid: u.email for uid, u in directory.get_users(sorted(user_ids)).items()}
    except Exception:
        log.exception("vms.notify.directory_lookup_failed")
        return {}


def deliver_pending(limit: int = 100, now: datetime | None = None) -> DeliveryReport:
    """Send up to `limit` pending rows. Concurrent-safe (row locks, skip_locked)
    and never raises out of the loop."""
    now = now or timezone.now()
    report = DeliveryReport()
    ids = list(Notification.objects.filter(status=Notification.Status.PENDING)
               .order_by("created_at", "id").values_list("pk", flat=True)[:limit])
    emails = _user_emails(ids)
    for pk in ids:
        try:
            _deliver_one(pk, emails, now, report)
        except Exception:
            log.exception("vms.notify.unexpected id=%s", pk)
    return report


# --- recipient groups ------------------------------------------------------------------

def role_holder_ids(roles=("security", "admin"), *, zone_id=None, gate_id=None,
                    at=None) -> list[int]:
    """Users holding an active RoleAssignment whose scope covers the zone/gate (BR-181/182)."""
    at = at or timezone.now()
    qs = RoleAssignment.objects.filter(
        revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at, role__in=roles)
    if zone_id is not None or gate_id is not None:
        scope = Q(scope_type=RoleAssignment.ScopeType.CAMPUS)
        if zone_id is not None:
            scope |= Q(scope_type=RoleAssignment.ScopeType.ZONE, scope_id=zone_id)
        if gate_id is not None:
            scope |= Q(scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate_id)
        qs = qs.filter(scope)
    return sorted(set(qs.values_list("user_id", flat=True)))


def notify_role_holders(*, topic, dedupe_key, subject, body, roles=("security", "admin"),
                        zone_id=None, gate_id=None, channels=("inapp", "email")):
    """Fan a security/admin topic out to whoever holds the role right now.

    One row per user and channel; the assignment table is read at call time, and
    the scope is stored in `Notification.detail` so delivery re-checks that the
    user still holds the role (BR-182) when the row is finally sent.
    """
    rows = []
    for uid in role_holder_ids(roles, zone_id=zone_id, gate_id=gate_id):
        rows += notify.enqueue(
            topic=topic, dedupe_key=f"{dedupe_key}:u{uid}", subject=subject, body=body,
            user_id=uid, channels=channels,
            detail={"roles": list(roles), "zone_id": zone_id, "gate_id": gate_id})
    return rows


# --- inbox writes -----------------------------------------------------------------------

def _owner(user_id, visitor_id) -> dict:
    return ({"recipient_user_id": user_id} if user_id is not None
            else {"recipient_visitor_id": visitor_id})


def mark_read(notification_id: int, *, user_id: int | None = None,
              visitor_id: int | None = None) -> Notification:
    """Mark one of the caller's own in-app notifications read; anything else is a 404."""
    row = Notification.objects.filter(
        pk=notification_id, channel=Notification.Channel.INAPP,
        **_owner(user_id, visitor_id)).first()
    if row is None:
        raise NotFoundError()
    if row.read_at is None:
        row.read_at = timezone.now()
        row.save(update_fields=["read_at"])
    return row


def mark_all_read(*, user_id: int | None = None, visitor_id: int | None = None) -> int:
    return Notification.objects.filter(
        channel=Notification.Channel.INAPP, read_at__isnull=True, **_owner(user_id, visitor_id)
    ).update(read_at=timezone.now())


def retry_failed(notification_id: int, *, actor) -> Notification:
    """Ops: put a failed row back in the queue (audited)."""
    with transaction.atomic():
        row = Notification.objects.select_for_update().filter(pk=notification_id).first()
        if row is None:
            raise NotFoundError()
        if row.status != Notification.Status.FAILED:
            raise ConflictError("Only failed notifications can be retried.")
        row.status, row.attempts, row.last_error = Notification.Status.PENDING, 0, ""
        row.next_attempt_at = None
        row.save(update_fields=["status", "attempts", "last_error", "next_attempt_at"])
        audit.record(actor=actor, action="vms.notification.retried", entity=row,
                     detail={"topic": row.topic, "channel": row.channel})
    return row
