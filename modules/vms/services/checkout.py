"""Check-out and visit completion (VMS-CFR-015, CFR-023; BR-105, BR-101).

Every path (gate, visitor self check-out, lane I's auto check-out) ends in
`_complete`: log the exit, move the request to ``completed`` through
`domain.request_state`, audit, notify the host. SRS workflows BW-VMS-01/04/05/
06/07/16/18 all show check-out -> Completed, including after a termination
(pass deactivated, visitor "pending exit").
"""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import request_state as rs
from modules.vms.models import Gate, IntegrationSetting, VisitLog, VisitPass, VisitRequest
from modules.vms.selectors import roster
from modules.vms.services.common import audit, authz, notify

GATE_PERM = "vms.gate.operate"
KIOSK_SETTING = "kiosk_enabled"
NOTIFY_SETTING = "notify_host_on_checkout"
E = VisitLog.Event


def _kind(vr) -> str:
    return rs.kind_for_source(vr.source)


def _setting_on(key: str, default: bool) -> bool:
    row = IntegrationSetting.objects.filter(key=key).first()
    if row is None:
        return default
    value = row.value
    if isinstance(value, dict):
        value = value.get("enabled", default)
    return bool(value)


def _complete(vp, *, event, actor, actor_kind, reason="", gate=None, strict=True):
    """Write the exit log and complete the request. Returns the VisitLog, or
    None when `strict` is false and there is nothing to check out."""
    with transaction.atomic():
        vr = VisitRequest.objects.select_for_update().get(pk=vp.visit_request_id)
        if roster.open_check_in(vp) is None:
            if strict:
                raise BadRequestError("No open check-in for this pass.", code="no_open_check_in")
            return None
        try:
            new = rs.next_state(_kind(vr), vr.status, rs.COMPLETE, actor_kind)   # BR-105
        except rs.InvalidTransition:
            if strict:
                raise ConflictError("This visit cannot be completed from its current state.",
                                    code="invalid_state") from None
            return None
        user_id = getattr(actor, "user_id", None)
        log = VisitLog.objects.create(
            visit_pass=vp, event=event, reason=reason, gate=gate,
            logged_by_user_id=user_id)
        vr.status = new
        vr.save(update_fields=["status"])
        audit.record(actor=actor, action="vms.visit.completed", entity=vr, detail={
            "pass_id": vp.pk, "event": event, "reason": reason,
            "gate_id": gate.pk if gate else None})
        if _setting_on(NOTIFY_SETTING, True):
            notify.enqueue(
                topic="visit.checked_out", dedupe_key=f"visit-checked-out:{vp.pk}:{log.pk}",
                subject="Your visitor has left",
                body=f"{vr.visitor.full_name} checked out.", user_id=vr.host_user_id)
        return log


def _find_on_site_pass(credential: str):
    """Resolve a QR token, else an OTP, to a pass. OTPs are only unique among
    active passes, and a terminated pass may still be on site, so the OTP is
    matched against the on-site roster."""
    credential = (credential or "").strip()
    if not credential:
        raise BadRequestError("A pass credential is required.", code="credential_required")
    vp = VisitPass.objects.filter(qr_token=credential).first()
    if vp is None:
        vp = roster.on_site().filter(otp=credential).first()
    if vp is None:
        raise NotFoundError("Pass not found.")
    return vp


def gate_checkout(*, security_actor, credential: str, gate_id: int | None = None):
    """Security checks a visitor out at the gate (UC-021; BR-105)."""
    authz.require(security_actor, GATE_PERM)
    authz.require_role(security_actor, "security", gate_id=gate_id)
    gate = None
    if gate_id is not None:
        gate = Gate.objects.filter(pk=gate_id).first()
        if gate is None:
            raise BadRequestError("Unknown gate.", code="unknown_gate")
    vp = _find_on_site_pass(credential)
    return _complete(vp, event=E.CHECK_OUT, actor=security_actor,
                     actor_kind=rs.SECURITY, gate=gate)


def self_checkout(*, session, pass_token: str):
    """Visitor checks themselves out (CFR-023, manual half). `session` is the
    verified visitor principal. Only allowed when the kiosk setting is on."""
    if not _setting_on(KIOSK_SETTING, False):
        raise PermissionDeniedError("Self check-out is not enabled.",
                                    code="self_checkout_disabled")
    vp = (VisitPass.objects.select_related("visit_request")
          .filter(qr_token=(pass_token or ""),
                  visit_request__visitor_id=getattr(session, "visitor_id", None)).first())
    if vp is None:
        raise NotFoundError("Pass not found.")
    # Domain table allows COMPLETE by security or system only; a self check-out
    # is an unattended system-recorded exit.
    return _complete(vp, event=E.CHECK_OUT, actor=None, actor_kind=rs.SYSTEM, reason="self")


def complete_visit(pass_id: int, reason: str, actor=None):
    """Complete the visit of `pass_id` (lane I auto check-out, BR-101/105).

    Records ``auto_check_out`` for the system (actor None) and ``check_out``
    when a user is given. Idempotent: returns None when the visitor is not on
    site or the request is already completed.
    """
    vp = VisitPass.objects.filter(pk=pass_id).first()
    if vp is None:
        raise NotFoundError("Pass not found.")
    if actor is None:
        return _complete(vp, event=E.AUTO_CHECK_OUT, actor=None, actor_kind=rs.SYSTEM,
                         reason=reason, strict=False)
    return _complete(vp, event=E.CHECK_OUT, actor=actor, actor_kind=rs.SECURITY,
                     reason=reason, strict=False)


__all__ = ["complete_visit", "gate_checkout", "self_checkout"]
