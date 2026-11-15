"""Notification creation rules.

VMS only records the trigger; the campus mail/SMS/push infrastructure does
the delivering. What lives here is WHO may be notified, on which channel,
and with which id attached:

VMS-BR-007  every send preserves the ORIGINAL visit-request id.
VMS-BR-012  a request on a shared badge still notifies the host.
VMS-BR-014  host notifications go push/call/email, with an informed timeout.
VMS-BR-022  a disabled contact suppresses every channel.
VMS-BR-036  an event's lead contact overrides the individual contacts.
VMS-BR-037  a guest who is NOT safe-listed gets no notification.
VMS-BR-038  a safe-listed guest's payload is safe-list context ONLY.
VMS-BR-046  a guest notification requires valid host contacts.
"""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import Visitor, VmsNotification
from modules.vms.services.blacklist import find_safe_list

HOST_CHANNELS = ("PUSH", "EMAIL", "CALL")      # VMS-BR-014


def _request_id(visit_request) -> str:
    """VMS-BR-007: the original request id, never a fresh one."""
    if visit_request is None:
        return ""
    return visit_request.original_request_id or str(visit_request.pk)


def send(*, kind: str, channel: str, recipient_type: str,
         recipient_contact: str = "", subject: str = "",
         payload: dict | None = None, visit_request=None,
         visit_id: int | None = None, pass_id: int | None = None,
         suppressed_reason: str = "") -> VmsNotification:
    """Record one notification. An empty contact or an explicit suppression
    reason lands as SUPPRESSED rather than silently vanishing (VMS-BR-022)."""
    if suppressed_reason or not recipient_contact:
        status = "SUPPRESSED"
        suppressed_reason = suppressed_reason or "no_contact"
    else:
        status = "SENT"
    return VmsNotification.objects.create(
        kind=kind, channel=channel, recipient_type=recipient_type,
        recipient_contact=recipient_contact, subject=subject,
        payload=payload or {}, status=status,
        suppressed_reason=suppressed_reason,
        related_visit_request_id=getattr(visit_request, "id", None),
        related_visit_id=visit_id, related_pass_id=pass_id,
        request_id=_request_id(visit_request),
        sent_at=timezone.now() if status == "SENT" else None)


def notify_host(visit_request, *, kind: str, subject: str = "",
                payload: dict | None = None) -> list[VmsNotification]:
    """One record per configured host channel (VMS-BR-014).

    VMS-BR-012: shared badge or not, the host is notified. VMS-BR-022:
    disabled contacts suppress everything. VMS-BR-046: no valid contact
    data means no delivery.
    """
    base = {"kind": kind, "visit_request": visit_request,
                "payload": {"shared_badge": visit_request.is_shared_badge,
                         **(payload or {})}}
    out = []
    if visit_request.host_contacts_disabled:                # VMS-BR-022
        out.extend(
            send(
                channel=channel,
                recipient_type="HOST",
                recipient_contact="",
                subject=subject,
                suppressed_reason="contact_disabled",
                **base,
            )
            for channel in HOST_CHANNELS
        )
        return out
    contacts = {
        "PUSH": f"user:{visit_request.host_user_id}",       # always reachable
        "EMAIL": visit_request.host_contact_email,
        "CALL": visit_request.host_contact_phone,
    }
    for channel in HOST_CHANNELS:
        contact = contacts[channel]
        reason = "" if contact else "no_valid_host_contact"   # VMS-BR-046
        out.append(send(channel=channel, recipient_type="HOST",
                        recipient_contact=contact, subject=subject,
                        suppressed_reason=reason, **base))
    return out


def notify_visitor(visitor: Visitor, *, kind: str, subject: str = "",
                   payload: dict | None = None,
                   visit_request=None) -> VmsNotification | None:
    """Guest notifications, gated by the safe-list.

    VMS-BR-037: not safe-listed -> no notification at all (returns None).
    VMS-BR-046: safe-listed but the host has no valid contact -> suppressed.
    VMS-BR-038: the payload is safe-list context ONLY.
    """
    safe = find_safe_list(full_name=visitor.full_name, phone=visitor.phone,
                          email=visitor.email,
                          id_doc_number=visitor.id_doc_number)
    if safe is None:                                         # VMS-BR-037
        return None
    context = {
        "safe_list_id": safe.id,
        "name": visitor.full_name,
        "expiry_date": safe.expiry_date.isoformat()
        if safe.expiry_date else None,
    }
    host_ok = bool(visit_request is None
                   or visit_request.host_contact_email
                   or visit_request.host_contact_phone)
    reason = "" if host_ok else "no_valid_host_contact"      # VMS-BR-046
    return send(kind=kind, channel="IN_APP", recipient_type="VISITOR",
                recipient_contact=visitor.email or visitor.phone,
                subject=subject, payload=context,               # VMS-BR-038
                visit_request=visit_request, suppressed_reason=reason)


def notify_event_lead(*, lead_email: str, kind: str = "EVENT_LEAD",
                      subject: str = "", payload: dict | None = None,
                      visit_request=None) -> VmsNotification:
    """VMS-BR-036: the batch/event lead contact overrides every other
    contact on the list — the lead is the only recipient."""
    return send(kind=kind, channel="EMAIL", recipient_type="ADMIN",
                recipient_contact=lead_email, subject=subject,
                payload={"recipient_override": "lead", **(payload or {})},
                visit_request=visit_request)


def notify_approval_timeout(visit_request, *,
                            subject: str = "Visit request expiring soon",
                            ) -> list[VmsNotification]:
    """VMS-BR-014: the informed timeout warning, on every host channel."""
    return notify_host(visit_request, kind="APPROVAL_TIMEOUT",
                       subject=subject,
                       payload={"approval_expires_at":
                                visit_request.approval_expires_at.isoformat()
                                if visit_request.approval_expires_at else None})
