"""The behaviour of the pre-Phase-0 endpoints, rebuilt on the shared services.

TODO: this is a seed, not a feature. Lane A replaces `pre_register` and
`decide` (services/registration.py, approval.py); lane B replaces
`gate_validate` and `gate_checkout` (services/gate.py). Delete the matching
function when you do. Do not extend this file.
"""
from __future__ import annotations

from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.domain import pass_rules, request_state
from modules.vms.models import VisitLog, Visitor, VisitPass, VisitRequest
from modules.vms.services import blacklist, passes, policy
from modules.vms.services.common import audit, notify

E = VisitLog.Event

#: Messages the old gate endpoint returned, keyed by the domain failure code.
GATE_MESSAGES = {
    pass_rules.PASS_INACTIVE: "Pass is not active.",
    pass_rules.OUTSIDE_VALIDITY: "Pass is outside its validity window.",
    pass_rules.OUTSIDE_SLOT: "Outside the event slot.",
    pass_rules.BLACKLISTED: "Visitor is blacklisted.",
    pass_rules.ZONE_NOT_PERMITTED: "Zone not permitted for this pass.",
    pass_rules.ALREADY_INSIDE: "Already checked in.",
    pass_rules.TERMINATED: "Pass was terminated.",
}


class GateDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _kind(vr: VisitRequest) -> str:
    return request_state.WALK_IN if vr.source == VisitRequest.Source.WALK_IN \
        else request_state.PRE_REGISTERED


# --- requests ------------------------------------------------------------------------

def pre_register(*, actor, data: dict) -> VisitRequest:
    """VMS-BR-051 blacklist at pre-registration, BR-038 no duplicate pending."""
    hit = blacklist.check(
        checkpoint="pre_registration", name=data["full_name"],
        id_doc_number=data["id_doc_number"], phone=data["phone"], email=data.get("email", ""))
    if hit:
        raise BadRequestError("This visitor is not permitted entry.",
                              code="visitor_blacklisted")
    with transaction.atomic():
        visitor, _ = Visitor.objects.get_or_create(
            id_doc_number=data["id_doc_number"], id_doc_type=data["id_doc_type"],
            defaults={"full_name": data["full_name"], "phone": data["phone"],
                      "email": data.get("email", "")})
        if VisitRequest.objects.filter(
                visitor=visitor, host_user_id=data["host_user_id"],
                scheduled_start=data["scheduled_start"],
                status=VisitRequest.Status.PENDING).exists():
            raise BadRequestError("A pending request already exists for this visit.",
                                  code="duplicate_request")
        # TODO lane A: urgent / bypass_approval flags (BR-195, 197, 202, 203).
        state = request_state.next_state(
            request_state.PRE_REGISTERED, request_state.NOT_SUBMITTED, request_state.SUBMIT,
            request_state.VISITOR, {"urgent": False, "bypass_approval": False})
        vr = VisitRequest.objects.create(
            visitor=visitor, host_user_id=data["host_user_id"], purpose=data["purpose"],
            scheduled_start=data["scheduled_start"], scheduled_end=data["scheduled_end"],
            status=state, source=VisitRequest.Source.PRE_REGISTERED)
        vr.requested_zones.set(data.get("requested_zones", []))
        audit.record(actor=actor, action="vms.request.submitted", entity=vr,
                     detail={"host_user_id": vr.host_user_id})
        notify.enqueue(
            topic="request.submitted", dedupe_key=f"request-submitted:{vr.pk}",
            subject="New visit request",
            body=f"{visitor.full_name} asked to visit you: {vr.purpose}",
            user_id=vr.host_user_id)
    return vr


def decide(*, actor, request_id: int, decision: str, note: str = ""):
    """Host decision. Returns (request, pass-or-None). Wrong owner is a 404."""
    approve = decision == "approve"
    with transaction.atomic():
        vr = (VisitRequest.objects.select_for_update()
              .filter(pk=request_id, host_user_id=actor.user_id).first())
        if vr is None:
            raise NotFoundError()
        event = request_state.HOST_APPROVE if approve else request_state.HOST_REJECT
        try:
            vr.status = request_state.next_state(
                _kind(vr), vr.status, event, request_state.HOST)
        except request_state.InvalidTransition:
            raise ConflictError("Only a pending request can be decided.") from None
        vr.decision_note = note
        vr.decided_at = timezone.now()
        vr.save()
        audit.record(actor=actor, action=f"vms.request.{vr.status}", entity=vr,
                     detail={"note": note})
        vp = None
        if approve:
            vp = passes.issue_pass(
                request=vr, issued_by=actor,
                pass_type=(VisitPass.PassType.WALK_IN
                           if vr.source == VisitRequest.Source.WALK_IN
                           else VisitPass.PassType.PRE_REGISTERED))
        notify.enqueue(
            topic="request.decided", dedupe_key=f"request-decided:{vr.pk}",
            subject=f"Visit request {vr.status}",
            body=f"Your visit request was {vr.status}.", visitor=vr.visitor)
    return vr, vp


# --- gate ----------------------------------------------------------------------------

def _last_event(vp):
    log = vp.logs.exclude(event=E.DENIED).order_by("-id").first()
    return log.event if log else None


def find_pass(data):
    qs = VisitPass.objects.select_related("visit_request__visitor")
    if data.get("qr_token"):
        return qs.filter(qr_token=data["qr_token"]).first()
    if data.get("otp"):
        return qs.filter(otp=data["otp"], is_active=True).order_by("-id").first()
    raise BadRequestError("qr_token or otp is required.")




def gate_validate(*, actor, data: dict):
    """Returns the visit request id on success; raises GateDenied (logged) or
    returns None when the pass does not exist (not logged: no pass to attach to)."""
    now = timezone.now()
    denial = None
    with transaction.atomic():
        vp = find_pass(data)
        if vp is None:
            return None
        zone = None
        zone_id = data.get("zone_id")
        if zone_id:
            zone = vp.allowed_zones.filter(pk=zone_id).first()
        visitor = vp.visit_request.visitor
        pol = policy.snapshot_for(vp.visit_request)
        elevated = set(vp.elevations.filter(starts_at__lte=now, ends_at__gt=now,
                                            revoked_at__isnull=True)
                       .values_list("zone_id", flat=True))
        subject = SimpleNamespace(
            is_active=vp.is_active, terminated=vp.terminated_at is not None,
            valid_from=vp.valid_from, valid_until=vp.valid_until,
            allowed_zone_ids=set(vp.allowed_zones.values_list("pk", flat=True)) | elevated)
        hit = blacklist.check(
            checkpoint="gate", name=visitor.full_name, id_doc_number=visitor.id_doc_number,
            phone=visitor.phone, email=visitor.email, at=now)
        failures = pass_rules.validate_at_gate(
            subject, now, int(zone_id) if zone_id else None, pol,
            blacklisted=hit is not None, open_checkin=_last_event(vp) == E.CHECK_IN)
        if failures:
            # The denial row must commit, so raise only after leaving the block.
            denial = GATE_MESSAGES[failures[0].code]
            VisitLog.objects.create(visit_pass=vp, event=E.DENIED, reason=denial,
                                    zone=zone, logged_by_user_id=actor.user_id)
        else:
            VisitLog.objects.create(visit_pass=vp, event=E.CHECK_IN, zone=zone,
                                    logged_by_user_id=actor.user_id)
            return vp.visit_request_id
    raise GateDenied(denial)


def gate_checkout(*, actor, qr_token: str) -> None:
    with transaction.atomic():
        vp = VisitPass.objects.filter(qr_token=qr_token or "").first()
        if vp is None:
            raise NotFoundError("Pass not found.")
        if _last_event(vp) != E.CHECK_IN:
            raise BadRequestError("No open check-in for this pass.")
        vr = VisitRequest.objects.select_for_update().get(pk=vp.visit_request_id)
        try:
            vr.status = request_state.next_state(
                _kind(vr), vr.status, request_state.COMPLETE, request_state.SECURITY)
        except request_state.InvalidTransition:
            raise ConflictError("This visit cannot be completed from its current state.") from None
        VisitLog.objects.create(visit_pass=vp, event=E.CHECK_OUT,
                                logged_by_user_id=actor.user_id)
        vr.save(update_fields=["status"])
        audit.record(actor=actor, action="vms.visit.completed", entity=vr)
