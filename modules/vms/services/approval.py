"""Host decision on a visit request and the Admin urgent exception.

decide / bulk_decide : VMS-UC-013, CFR-010, BW-VMS-01 (approve), BW-VMS-02 (reject)
decide_urgent        : VMS-UC-035, CFR-031, BW-VMS-22 (Admin exception)
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import request_state
from modules.vms.models import VisitPass, VisitRequest
from modules.vms.services import passes, policy, registration
from modules.vms.services.common import audit, authz, notify

APPROVE, REJECT = "approve", "reject"


def _kind(vr: VisitRequest) -> str:
    return request_state.kind_for_source(vr.source)


def _narrow(vr, zones, window):
    """Validate the host's restrictions: zones within the requested set, window
    within the requested window (the policy cap is applied by issue_pass)."""
    zone_list = None
    if zones is not None:
        wanted = {z.pk if hasattr(z, "pk") else int(z) for z in zones}
        allowed = set(vr.requested_zones.values_list("pk", flat=True))
        if not wanted <= allowed:
            raise BadRequestError("Zones may only be narrowed, never added.",
                                  code="zones_not_subset")
        zone_list = sorted(wanted)
    start = end = None
    if window:
        start = window.get("start") or vr.scheduled_start
        end = window.get("end") or vr.scheduled_end
        if end <= start or start < vr.scheduled_start or end > vr.scheduled_end:
            raise BadRequestError("The window may only be narrowed, never widened.",
                                  code="window_not_narrower")
    return zone_list, start, end


def _notify_visitor(vr, topic, subject, body):
    for visitor in {vr.visitor, vr.created_by_visitor} - {None}:
        notify.enqueue(topic=topic, dedupe_key=f"{topic}:{vr.pk}:{visitor.pk}",
                       subject=subject, body=body, visitor=visitor)


def _rescreen(host_actor, request_id):
    """BR-051/116: a blacklist published after submission still blocks approval."""
    vr = (VisitRequest.objects.select_related("visitor")
          .filter(pk=request_id, host_user_id=host_actor.user_id,
                  status=VisitRequest.Status.PENDING).first())
    if vr is None:
        return          # not found / not pending: reported by the locked path below
    checkpoint = "walk_in" if _kind(vr) == request_state.WALK_IN else "pre_registration"
    if registration.rescreen_request(vr, checkpoint=checkpoint, actor=host_actor):
        raise BadRequestError("This visitor is not permitted entry.",
                              code="visitor_blacklisted")


def decide(*, host_actor, request_id: int, decision: str, note: str = "",
           zones=None, window=None):
    """Host approves or rejects. Returns ``(request, pass_or_None)``.

    Not the assigned host -> NotFoundError (BR no enumeration). A request that
    is no longer pending -> ConflictError.
    """
    if decision not in (APPROVE, REJECT):
        raise BadRequestError("decision must be 'approve' or 'reject'.", code="invalid_decision")
    if not authz.is_host(host_actor):
        raise PermissionDeniedError()
    note = (note or "").strip()
    if decision == REJECT and not note:
        raise BadRequestError("A reason is required to reject a request.",
                              code="reason_required")
    now = timezone.now()
    if decision == APPROVE:
        _rescreen(host_actor, request_id)
    with transaction.atomic():
        vr = (VisitRequest.objects.select_for_update(of=("self",))
              .select_related("visitor", "created_by_visitor")
              .filter(pk=request_id, host_user_id=host_actor.user_id).first())
        if vr is None:
            raise NotFoundError()
        event = request_state.HOST_APPROVE if decision == APPROVE else request_state.HOST_REJECT
        try:
            new = request_state.next_state(_kind(vr), vr.status, event, request_state.HOST)
        except request_state.InvalidTransition:
            raise ConflictError("Only a pending request can be decided.",
                                code="not_pending") from None
        if vr.expires_at and vr.expires_at <= now:
            raise ConflictError("This request has expired.", code="request_expired")
        zone_list, start, end = (_narrow(vr, zones, window) if decision == APPROVE
                                 else (None, None, None))
        vr.status, vr.decision_note, vr.decided_at = new, note, now
        vr.save(update_fields=["status", "decision_note", "decided_at"])
        detail = {"note": note, "policy_version": policy.snapshot_for(vr).version}
        vp = None
        if decision == APPROVE:
            vp = passes.issue_pass(
                request=vr, issued_by=host_actor,
                pass_type=(VisitPass.PassType.WALK_IN if _kind(vr) == request_state.WALK_IN
                           else VisitPass.PassType.PRE_REGISTERED),
                valid_from=start, valid_until=end, zones=zone_list)
            detail["pass_id"] = vp.pk
            if zone_list is not None:
                detail["zones"] = zone_list
        audit.record(actor=host_actor, action=f"vms.request.{new}", entity=vr, detail=detail)
        if decision == APPROVE:
            _notify_visitor(vr, "request.approved", "Visit approved",
                            "Your visit request was approved.")
            _notify_visitor(vr, "pass.issued", "Your visit pass is ready",
                            "Open the pass from your visits page.")
        else:
            _notify_visitor(vr, "request.rejected", "Visit not approved",
                            f"Your visit request was rejected: {note}")
    return vr, vp


def bulk_decide(*, host_actor, ids, decision: str, note: str = "") -> list[dict]:
    """Decide many requests (recurring vendors). Each id is independent: one
    failure never rolls back another. Returns one result dict per id."""
    results = []
    for rid in dict.fromkeys(ids):
        try:
            vr, vp = decide(host_actor=host_actor, request_id=rid, decision=decision,
                            note=note)
            results.append({"id": rid, "ok": True, "status": vr.status,
                            "pass_id": vp.pk if vp else None})
        except DomainError as exc:
            results.append({"id": rid, "ok": False, "error": exc.code,
                            "message": str(exc.message)})
    return results


def decide_urgent(*, admin_actor, request_id: int, decision: str, note: str = "") -> VisitRequest:
    """Admin decides a same-day urgent exception (BR-203).

    The SRS (BW-VMS-22 row 2) sends an approved exception to *Pending Host
    Approval*, not straight to a pass; the host then decides as usual.
    """
    if decision not in (APPROVE, REJECT):
        raise BadRequestError("decision must be 'approve' or 'reject'.", code="invalid_decision")
    authz.require_role(admin_actor, "admin")
    note = (note or "").strip()
    if decision == REJECT and not note:
        raise BadRequestError("A reason is required to reject a request.",
                              code="reason_required")
    now = timezone.now()
    with transaction.atomic():
        vr = (VisitRequest.objects.select_for_update(of=("self",))
              .select_related("visitor", "created_by_visitor")
              .filter(pk=request_id, is_urgent=True,
                      source=VisitRequest.Source.PRE_REGISTERED).first())
        if vr is None:
            raise NotFoundError()
        event = (request_state.URGENT_APPROVE if decision == APPROVE
                 else request_state.URGENT_REJECT)
        try:
            new = request_state.next_state(_kind(vr), vr.status, event, request_state.ADMIN)
        except request_state.InvalidTransition:
            raise ConflictError("Only an urgent request awaiting an Admin can be decided.",
                                code="not_awaiting_admin") from None
        pol = policy.effective()
        vr.status = new
        vr.urgent_decision = (VisitRequest.UrgentDecision.APPROVED if decision == APPROVE
                              else VisitRequest.UrgentDecision.REJECTED)
        vr.urgent_decided_by_user_id = admin_actor.user_id
        fields = ["status", "urgent_decision", "urgent_decided_by_user_id"]
        if decision == APPROVE:
            vr.expires_at = now + timedelta(hours=pol.approval_timeout_hours)
            fields.append("expires_at")
        else:
            vr.decision_note, vr.decided_at = note, now
            fields += ["decision_note", "decided_at"]
        vr.save(update_fields=fields)
        audit.record(actor=admin_actor, action=f"vms.request.urgent_{decision}d", entity=vr,
                     detail={"note": note, "state": new})
        if decision == APPROVE:
            notify.enqueue(
                topic="request.submitted", dedupe_key=f"request-submitted:{vr.pk}",
                subject="New visit request",
                body=f"{vr.visitor.full_name} asked to visit you: {vr.purpose}",
                user_id=vr.host_user_id)
            _notify_visitor(vr, "request.urgent_approved", "Urgent visit cleared",
                            "An Admin cleared your same-day request; awaiting your host.")
        else:
            _notify_visitor(vr, "request.rejected", "Visit not approved",
                            f"Your urgent visit request was rejected: {note}")
    return vr
