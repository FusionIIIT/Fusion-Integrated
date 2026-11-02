"""Early pass/visit termination (VMS-CFR-024; UC-016, UC-036; BR-073;
BW-VMS-15/16/17/18).

The host of the visit, or an Admin whose scope covers it, deactivates the pass
with a mandatory reason. Before check-in the visit ends at once (BW-15/17). On
site the visitor stays "pending exit" until Security records the physical exit
through check-out (BW-16/18, BR-105); Security is alerted to escort them.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import request_state
from modules.vms.models import Alert, VisitLog, VisitPass, VisitRequest
from modules.vms.selectors import roster
from modules.vms.services.common import audit, authz, notify

PERM = "vms.pass.terminate"


def _is_admin_for(actor, vp) -> bool:
    zone_ids = list(vp.allowed_zones.values_list("pk", flat=True))
    if not zone_ids:
        zone_ids = list(vp.visit_request.requested_zones.values_list("pk", flat=True))
    for zid in zone_ids or [None]:
        try:
            authz.require_role(actor, "admin", zone_id=zid)
        except PermissionDeniedError:
            continue
        return True
    return False


def terminate(*, actor, pass_id: int, reason: str) -> VisitPass:
    """Terminate a pass. Host: own visitor only (else 404). Admin: any in scope."""
    authz.require(actor, PERM)
    reason = (reason or "").strip()
    if not reason:                                            # BR-073
        raise BadRequestError("A termination reason is required.", code="reason_required")
    now = timezone.now()
    with transaction.atomic():
        vp = (VisitPass.objects.select_for_update(of=("self",))
              .select_related("visit_request__visitor").filter(pk=pass_id).first())
        if vp is None:
            raise NotFoundError()
        vr = vp.visit_request
        is_admin = _is_admin_for(actor, vp)
        if not is_admin and vr.host_user_id != actor.user_id:
            raise NotFoundError()                             # no id enumeration
        if not vp.is_active or vp.terminated_at is not None:
            raise ConflictError("This pass is already inactive.", code="pass_not_active")
        vr = VisitRequest.objects.select_for_update().get(pk=vr.pk)
        on_site = roster.open_check_in(vp) is not None
        vp.is_active = False
        vp.terminated_at = now
        vp.terminated_by_user_id = actor.user_id
        vp.termination_reason = reason[:255]
        vp.save(update_fields=["is_active", "terminated_at", "terminated_by_user_id",
                               "termination_reason"])
        alert = None
        if on_site:                                           # BW-16/18: pending exit
            VisitLog.objects.create(visit_pass=vp, event=VisitLog.Event.TERMINATED,
                                    reason=reason[:255], logged_by_user_id=actor.user_id)
            alert = Alert.objects.create(
                kind=Alert.Kind.SUSPICIOUS, severity=Alert.Severity.HIGH,
                ref_type="visit_pass", ref_id=vp.pk,
                detail={"action": "escort_out", "reason": reason,
                        "visitor": vr.visitor.full_name, "request_id": vr.pk})
        elif vr.status == VisitRequest.Status.APPROVED:       # BW-15/17: visit ends now
            vr.status = request_state.next_state(
                request_state.kind_for_source(vr.source), vr.status, request_state.TERMINATE,
                request_state.ADMIN if is_admin else request_state.HOST)
            vr.save(update_fields=["status"])
        audit.record(actor=actor, action="vms.pass.terminated", entity=vp, detail={
            "reason": reason, "request_id": vr.pk, "on_site": on_site,
            "alert_id": alert.pk if alert else None,
            "by": "admin" if is_admin else "host"})
        notify.enqueue(
            topic="pass.terminated", dedupe_key=f"pass-terminated:{vp.pk}:visitor",
            subject="Your visit pass was terminated",
            body="Your pass is no longer valid."
            + (" Please exit the premises." if on_site else ""),
            visitor=vr.visitor)
        if vr.host_user_id != actor.user_id:
            notify.enqueue(
                topic="pass.terminated", dedupe_key=f"pass-terminated:{vp.pk}:host",
                subject="A visitor pass was terminated",
                body=f"The pass for {vr.visitor.full_name} was terminated: {reason}",
                user_id=vr.host_user_id)
    return vp
