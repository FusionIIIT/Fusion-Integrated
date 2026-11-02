"""Walk-in registration and approval (VMS-CFR-016, CFR-027; BW-VMS-06/07/08).

Security registers the walk-in; the host decides (UC-013), or, when the host is
unavailable, an Admin decides the contingency (UC-033). All moves go through
`domain.request_state`.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import request_state as rs
from modules.vms.models import (
    Alert,
    Gate,
    Visitor,
    VisitPass,
    VisitRequest,
    Zone,
)
from modules.vms.services import blacklist, passes, policy
from modules.vms.services.common import audit, authz, notify

REGISTER_PERM = "vms.walkin.register"
CONTINGENCY_PERM = "vms.walkin.contingency_decide"
DECIDE_PERM = "vms.request.decide"
REQUIRED_FIELDS = ("full_name", "phone", "id_doc_type", "id_doc_number", "purpose")
APPROVE, REJECT = "approve", "reject"
DECISIONS = (APPROVE, REJECT)


def _check_decision(decision):
    if decision not in DECISIONS:
        raise BadRequestError("decision must be 'approve' or 'reject'.", code="invalid_decision")


def _pass_window(now, pol):
    hours = min(pol.walk_in_pass_hours, pol.max_visit_hours)   # BR-053
    return now, now + timedelta(hours=hours)


def _walkin_count_last_hour(now, gate_id):
    since = now - timedelta(hours=1)
    if gate_id is None:
        return VisitRequest.objects.filter(source=VisitRequest.Source.WALK_IN,
                                           created_at__gte=since).count()
    return VisitRequest.objects.filter(source=VisitRequest.Source.WALK_IN, gate_id=gate_id,
                                       created_at__gte=since).count()


def register(*, security_actor, data: dict, host_user_id: int) -> VisitRequest:
    """Register a walk-in at the gate (UC-017, BW-VMS-06/07/08 row 1).

    `data`: full_name, phone, id_doc_type, id_doc_number, purpose (mandatory);
    email, gate_id, zone_ids, host_available (default True) optional.
    Raises BadRequestError(code="visitor_blacklisted") on a blacklist hit
    (BR-051, checkpoint BR-112) after recording an Alert.
    """
    authz.require(security_actor, REGISTER_PERM)
    gate_id = data.get("gate_id")
    authz.require_role(security_actor, "security", gate_id=gate_id)
    missing = [f for f in REQUIRED_FIELDS if not str(data.get(f) or "").strip()]
    if not host_user_id:
        missing.append("host_user_id")
    if missing:
        raise BadRequestError("Missing mandatory fields.", code="missing_fields",
                              details=missing)
    if gate_id is not None and not Gate.objects.filter(pk=gate_id, is_active=True).exists():
        raise BadRequestError("Unknown gate.", code="unknown_gate")
    zone_ids = list(set(data.get("zone_ids") or []))
    if zone_ids and Zone.objects.filter(pk__in=zone_ids, is_active=True).count() != len(zone_ids):
        raise BadRequestError("Unknown zone.", code="unknown_zone")
    host_available = bool(data.get("host_available", True))
    now = timezone.now()

    hit = blacklist.check(checkpoint="walk_in", name=data["full_name"],
                          id_doc_number=data["id_doc_number"], phone=data["phone"],
                          email=data.get("email", ""), at=now)
    if hit is not None:
        with transaction.atomic():     # commit before raising
            alert = Alert.objects.create(
                kind=Alert.Kind.BLACKLIST_HIT, severity=Alert.Severity.HIGH,
                ref_type="blacklist_entry", ref_id=hit.entry_id,
                detail={"checkpoint": "walk_in", "gate_id": gate_id,
                        "matched_fields": list(hit.matched_fields)})
            audit.record(actor=security_actor, action="vms.walkin.blacklist_rejected",
                         entity=alert, detail={"entry_id": hit.entry_id,
                                               "matched_fields": list(hit.matched_fields)})
            notify.enqueue(
                topic="walkin.blocked", dedupe_key=f"walkin-blocked:{alert.pk}:{host_user_id}",
                subject="Walk-in registration blocked",
                body="A walk-in naming you as host was refused at the gate.",
                user_id=host_user_id)
        raise BadRequestError("This visitor is not permitted entry.", code="visitor_blacklisted")

    pol = policy.effective(now)
    with transaction.atomic():
        if _walkin_count_last_hour(now, gate_id) >= pol.walkin_rate_limit_per_hour:
            raise ConflictError("Walk-in registration limit reached for this hour.",
                                code="walkin_rate_limited")
        start, end = _pass_window(now, pol)
        to = rs.next_state(rs.WALK_IN, rs.NOT_SUBMITTED, rs.SUBMIT, rs.SECURITY,
                           {"host_available": host_available})
        visitor = Visitor.objects.create(
            full_name=data["full_name"].strip(), phone=data["phone"].strip(),
            email=(data.get("email") or "").strip(), id_doc_type=data["id_doc_type"].strip(),
            id_doc_number=data["id_doc_number"].strip())
        vr = VisitRequest.objects.create(
            visitor=visitor, host_user_id=host_user_id, purpose=data["purpose"].strip(),
            scheduled_start=start, scheduled_end=end, status=to,
            source=VisitRequest.Source.WALK_IN, gate_id=gate_id,
            contingency_requested_at=None if host_available else now)
        if zone_ids:
            vr.requested_zones.set(zone_ids)
        audit.record(actor=security_actor, action="vms.walkin.registered", entity=vr, detail={
            "gate_id": gate_id, "host_available": host_available, "status": to,
            "pass_hours": (end - start).total_seconds() / 3600})
        notify.enqueue(
            topic="walkin.submitted", dedupe_key=f"walkin-submitted:{vr.pk}",
            subject=("Walk-in visitor awaiting your approval" if host_available
                     else "Walk-in visitor registered while you were unavailable"),
            body=f"{visitor.full_name} is at the gate: {vr.purpose}.", user_id=host_user_id)
    return vr


def _locked_walkin(request_id) -> VisitRequest:
    vr = (VisitRequest.objects.select_for_update()
          .filter(pk=request_id, source=VisitRequest.Source.WALK_IN).first())
    if vr is None:
        raise NotFoundError()
    return vr


def _finish(vr, new_status, actor, *, contingency_by, note, now, audit_action):
    """Apply an approve/reject outcome; issue the WALK_IN pass on approval."""
    vr.status = new_status
    vr.decision_note = (note or "")[:255]
    vr.decided_at = now
    update = ["status", "decision_note", "decided_at"]
    if contingency_by is not None:
        vr.contingency_approved_by_user_id = contingency_by
        update.append("contingency_approved_by_user_id")
    vr.save(update_fields=update)
    vp = None
    if new_status == VisitRequest.Status.APPROVED:
        start, end = _pass_window(now, policy.effective(now))
        vp = passes.issue_pass(request=vr, pass_type=VisitPass.PassType.WALK_IN,
                               issued_by=actor, valid_from=start, valid_until=end)
    audit.record(actor=actor, action=audit_action, entity=vr,
                 detail={"decision": new_status, "note": note or "",
                         "pass_id": vp.pk if vp else None})
    notify.enqueue(
        topic="request.decided", dedupe_key=f"walkin-decided:{vr.pk}:{new_status}",
        subject=f"Walk-in request {new_status}",
        body="You may proceed to the gate." if vp else "Entry was not approved.",
        visitor=vr.visitor)
    return vr, vp


def host_decide_walkin(host_actor, request_id: int, decision: str, note: str = ""):
    """Host approves or rejects a pending walk-in (UC-013; BW-VMS-06 R2, BW-VMS-08 R2).

    Wrong host or not a walk-in -> 404. Returns (request, pass_or_None).
    """
    _check_decision(decision)
    authz.require(host_actor, DECIDE_PERM)
    with transaction.atomic():
        vr = _locked_walkin(request_id)
        if vr.host_user_id != host_actor.user_id:
            raise NotFoundError()
        event = rs.HOST_APPROVE if decision == APPROVE else rs.HOST_REJECT
        try:
            new = rs.next_state(rs.WALK_IN, vr.status, event, rs.HOST)
        except rs.InvalidTransition:
            raise ConflictError("This walk-in is not awaiting a host decision.",
                                code="invalid_state") from None
        return _finish(vr, new, host_actor, contingency_by=None, note=note,
                       now=timezone.now(), audit_action="vms.walkin.host_decided")


def _admin_covers(actor, vr) -> bool:
    zone_ids = list(vr.requested_zones.values_list("pk", flat=True))
    for zid in zone_ids or [None]:
        try:
            authz.require_role(actor, "admin", zone_id=zid)
        except PermissionDeniedError:
            continue
        return True
    return False


def contingency_decide(*, admin_actor, request_id: int, decision: str, note: str = ""):
    """Admin decides a walk-in whose host is unavailable (UC-033; BW-VMS-07 R2).

    BR-049: only when the host is unavailable, i.e. the request is
    ``awaiting_admin`` (host explicitly marked unavailable), or still ``pending``
    after ``contingency_sla_minutes`` with no host decision (BR-050, D-13).
    The admin must hold an Admin role covering one of the request's zones.
    """
    _check_decision(decision)
    authz.require(admin_actor, CONTINGENCY_PERM)
    now = timezone.now()
    with transaction.atomic():
        vr = _locked_walkin(request_id)
        if not _admin_covers(admin_actor, vr):
            raise PermissionDeniedError()
        if vr.status == VisitRequest.Status.PENDING:
            sla = timedelta(minutes=policy.snapshot_for(vr).contingency_sla_minutes)
            if now - (vr.contingency_requested_at or vr.created_at) < sla:
                raise ConflictError("The host is still within the response window.",
                                    code="contingency_not_allowed")
        elif vr.status != VisitRequest.Status.AWAITING_ADMIN:
            raise ConflictError("This walk-in is not awaiting a contingency decision.",
                                code="contingency_not_allowed")
        # An unresponsive host past the SLA is treated as unavailable (D-13).
        event = (rs.ADMIN_APPROVE_CONTINGENCY if decision == APPROVE
                 else rs.ADMIN_REJECT_CONTINGENCY)
        new = rs.next_state(rs.WALK_IN, rs.AWAITING_ADMIN, event, rs.ADMIN)
        return _finish(vr, new, admin_actor, contingency_by=admin_actor.user_id, note=note,
                       now=now, audit_action="vms.walkin.contingency_decided")


def list_registrations(*, actor, status: str | None = None):
    """Walk-in requests for Security/Admin work queues (UC-017/033)."""
    authz.require_role(actor, "security")
    qs = (VisitRequest.objects.filter(source=VisitRequest.Source.WALK_IN)
          .select_related("visitor").order_by("-id"))
    if status:
        qs = qs.filter(status=status)
    return qs
