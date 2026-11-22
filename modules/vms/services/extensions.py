"""Visit duration extensions (VMS-CFR-030; UC-034; BW-VMS-23; BR-193, BR-194).

An extension that keeps the whole visit within the policy maximum is granted
to the host at once (BR-193); one that goes beyond it becomes a ``pending``
`ExtensionRequest` that only an Admin may decide (BR-194, AFR-194). Approval
moves ``VisitPass.valid_until`` and ``VisitRequest.scheduled_end`` together
under row locks, so the gate and the auto check-out sweep (lane I, D-11)
always read one end time. The frozen policy snapshot is never touched (BR-129).

SRS note: BW-VMS-23 says the baseline "does not define the actor who originates
the extension request". We let the assigned host (lane default) or an Admin
raise one; Security cannot.
"""
from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import extension_state as es
from modules.vms.domain import policy_eval
from modules.vms.models import ExtensionRequest, VisitPass, VisitRequest
from modules.vms.services import blacklist, delivery, policy
from modules.vms.services.common import audit, authz, notify

DECIDE_PERM = "vms.extension.decide"
REQUEST_PERM = "vms.request.decide"
APPROVE, REJECT = "approve", "reject"
DECISIONS = {APPROVE: es.APPROVE, REJECT: es.REJECT}


def _zone_ids(vr) -> list:
    ids = list(vr.requested_zones.values_list("pk", flat=True))
    for vp in vr.passes.all():
        ids += list(vp.allowed_zones.values_list("pk", flat=True))
    return ids or [None]


def _is_admin_for(actor, vr) -> bool:
    """Holds ``vms.extension.decide`` and an active Admin role covering the visit."""
    if actor is None or not actor.has_permission(DECIDE_PERM):
        return False
    for zid in _zone_ids(vr):
        try:
            authz.require_role(actor, "admin", zone_id=zid)
        except PermissionDeniedError:
            continue
        return True
    return False


def _live_passes(vr, now):
    return [p for p in VisitPass.objects.select_for_update().filter(visit_request=vr)
            if p.is_active and p.terminated_at is None and p.valid_until > now]


def _check_blacklist(vr) -> None:
    """BR-112 gate-semantics re-check: a visitor listed since entry cannot be extended."""
    v = vr.visitor
    if blacklist.check(checkpoint="gate", name=v.full_name, id_doc_number=v.id_doc_number,
                       phone=v.phone, email=v.email):
        raise ConflictError("This visitor is blacklisted; the visit cannot be extended.",
                            code="blacklisted")


def _eligible(vr, new_end, now):
    """Common guards; returns the live passes. Caller holds the request lock."""
    if vr.status != VisitRequest.Status.APPROVED:
        raise ConflictError("Only an approved visit can be extended.", code="invalid_state")
    passes = _live_passes(vr, now)
    if not passes:
        raise ConflictError("The visit has no active pass.", code="pass_not_active")
    if new_end <= max(p.valid_until for p in passes):
        raise BadRequestError("The new end must be later than the current end.",
                              code="end_not_later")
    _check_blacklist(vr)
    return passes


def _apply(ext, vr, passes, new_end, actor, *, via) -> None:
    before = {"scheduled_end": vr.scheduled_end.isoformat(),
              "valid_until": {p.pk: p.valid_until.isoformat() for p in passes}}
    for p in passes:
        p.valid_until = new_end
        p.save(update_fields=["valid_until"])
    vr.scheduled_end = new_end
    vr.save(update_fields=["scheduled_end"])
    audit.record(actor=actor, action="vms.extension.applied", entity=ext, detail={
        "request_id": vr.pk, "pass_ids": [p.pk for p in passes],
        "new_end": new_end.isoformat(), "before": before, "via": via})


def request_extension(*, requester, request_id: int, new_end: datetime, reason: str = "",
                      now: datetime | None = None) -> ExtensionRequest:
    """Ask to extend a visit (UC-034 trigger; BR-193, BR-194)."""
    now = now or timezone.now()
    with transaction.atomic():
        vr = (VisitRequest.objects.select_for_update(of=("self",))
              .select_related("visitor").filter(pk=request_id).first())
        if vr is None:
            raise NotFoundError()
        is_host = ((authz.is_host(requester) or requester.has_permission(REQUEST_PERM))
                   and vr.host_user_id == requester.user_id)
        if not (is_host or _is_admin_for(requester, vr)):
            raise NotFoundError()                                  # no id enumeration
        if ExtensionRequest.objects.filter(
                visit_request=vr, status=ExtensionRequest.Status.PENDING).exists():
            raise ConflictError("An extension is already pending for this visit.",
                                code="extension_pending")
        passes = _eligible(vr, new_end, now)
        snap = policy.snapshot_for(vr)                             # BR-129
        within_cap = new_end <= policy_eval.capped_end(vr.scheduled_start, new_end,
                                                       snap.max_visit_hours)
        ext = ExtensionRequest.objects.create(
            visit_request=vr, requested_end=new_end, reason=(reason or "")[:255])
        audit.record(actor=requester, action="vms.extension.requested", entity=ext, detail={
            "request_id": vr.pk, "new_end": new_end.isoformat(),
            "max_visit_hours": snap.max_visit_hours, "within_cap": within_cap})
        if within_cap:                                             # BR-193: host extends directly
            ext.status = es.resolve(es.PENDING, es.APPROVE)
            ext.decided_by_user_id, ext.decided_at = requester.user_id, now
            ext.save(update_fields=["status", "decided_by_user_id", "decided_at"])
            _apply(ext, vr, passes, new_end, requester, via="within_cap")
        else:                                                      # BR-194: Admin must decide
            delivery.notify_role_holders(
                topic="extension.requested", dedupe_key=f"extension.requested:{ext.pk}",
                roles=("admin",),
                subject="Visit extension needs a decision",
                body=(f"{vr.visitor.full_name}'s visit needs to run past the "
                      f"{snap.max_visit_hours}-hour maximum, until {new_end:%Y-%m-%d %H:%M}. "
                      f"Reason: {ext.reason or 'not given'}"))
        return ext


def decide_extension(*, admin_actor, extension_id: int, decision: str, note: str = "",
                     now: datetime | None = None) -> ExtensionRequest:
    """Admin approves or rejects a pending extension (UC-034; BW-VMS-23)."""
    now = now or timezone.now()
    authz.require(admin_actor, DECIDE_PERM)
    event = DECISIONS.get(decision)
    if event is None:
        raise BadRequestError("Decision must be 'approve' or 'reject'.", code="bad_decision")
    with transaction.atomic():
        ext = ExtensionRequest.objects.select_for_update().filter(pk=extension_id).first()
        if ext is None:
            raise NotFoundError()
        vr = (VisitRequest.objects.select_for_update(of=("self",)).select_related("visitor")
              .get(pk=ext.visit_request_id))
        if not _is_admin_for(admin_actor, vr):
            raise PermissionDeniedError()
        try:
            new_status = es.resolve(ext.status, event)
        except es.InvalidTransition:
            raise ConflictError("This extension was already decided.",
                                code="already_decided") from None
        if event == es.APPROVE:
            passes = _eligible(vr, ext.requested_end, now)
            _apply(ext, vr, passes, ext.requested_end, admin_actor, via="admin")
        ext.status = new_status
        ext.decided_by_user_id, ext.decided_at = admin_actor.user_id, now
        ext.save(update_fields=["status", "decided_by_user_id", "decided_at"])
        audit.record(actor=admin_actor, action=f"vms.extension.{new_status}", entity=ext,
                     detail={"request_id": vr.pk, "note": note,
                             "requested_end": ext.requested_end.isoformat()})
        notify.enqueue(
            topic="extension.decided", dedupe_key=f"extension.decided:{ext.pk}",
            user_id=vr.host_user_id,
            subject=f"Visit extension {new_status}",
            body=(f"The extension for {vr.visitor.full_name} was {new_status}."
                  + (f" Note: {note}" if note else "")))
        return ext


# --- reads ----------------------------------------------------------------------------

def list_extensions(*, actor, status: str | None = None):
    """Admins (``vms.extension.decide``) see all; a host sees extensions of own visits."""
    qs = ExtensionRequest.objects.select_related("visit_request").order_by("-id")
    if not actor.has_permission(DECIDE_PERM):
        qs = qs.filter(visit_request__host_user_id=actor.user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_extension(*, actor, extension_id: int) -> ExtensionRequest:
    ext = list_extensions(actor=actor).filter(pk=extension_id).first()
    if ext is None:
        raise NotFoundError()
    return ext
