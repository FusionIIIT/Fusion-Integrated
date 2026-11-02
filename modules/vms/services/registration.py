"""Online pre-registration (VMS-CFR-019, CFR-031, CFR-032, CFR-029; UC-010).

`submit` is the one entry point. In a single transaction it validates the
submission, screens the blacklist, applies the advance-window rule, detects a
VIP override or host pre-authorisation, and creates the request in the state
the transition table dictates (BW-VMS-01/04/05/22).

Helpers other lanes may reuse (walk-in, bulk events, pre-authorisation):
`validate_fields`, `validate_id_document`, `resolve_visitor`, `ensure_host`,
`record_blacklist_hit`, `active_vip`, `matching_pre_authorization`,
`role_user_ids`.
"""
from __future__ import annotations

import re
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.directory import contracts as directory
from modules.vms.auth import VisitorPrincipal
from modules.vms.domain import policy_eval, request_state
from modules.vms.models import (
    Alert,
    PreAuthorization,
    RoleAssignment,
    VipPermission,
    Visitor,
    VisitPass,
    VisitRequest,
    Zone,
)
from modules.vms.services import blacklist, passes, policy
from modules.vms.services.common import audit, authz, notify

#: VMS-BR-187. Extending the domain is a one-line change.
ID_DOC_TYPES = ("passport", "aadhaar", "driving_licence", "voter_id")
_ID_NUMBER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/\- ]{3,59}$")
_PHONE = re.compile(r"^\+?[0-9][0-9 \-]{6,18}$")

MANDATORY = ("full_name", "phone", "id_doc_type", "id_doc_number", "host_user_id",
             "purpose", "scheduled_start", "scheduled_end")


def _fail(message, code="validation_error", **details):
    raise BadRequestError(message, code=code, details=[details] if details else None)


# --- validation ------------------------------------------------------------------------

def validate_fields(data: dict) -> None:
    """VMS-BR-037: every mandatory field present before a request exists."""
    missing = [f for f in MANDATORY
               if data.get(f) in (None, "") or str(data.get(f)).strip() == ""]
    if missing:
        _fail("Mandatory fields are missing: " + ", ".join(missing) + ".",
              code="missing_fields", fields=missing)
    if data["scheduled_end"] <= data["scheduled_start"]:
        _fail("scheduled_end must follow scheduled_start.", code="invalid_window")
    if not _PHONE.match(str(data["phone"]).strip()):
        _fail("The phone number is not valid.", code="invalid_phone")


def validate_id_document(id_doc_type: str, id_doc_number: str) -> None:
    """VMS-BR-186 (valid document) and BR-187 (supported types)."""
    if id_doc_type not in ID_DOC_TYPES:
        _fail(f"Unsupported identity document type; use one of {', '.join(ID_DOC_TYPES)}.",
              code="unsupported_id_doc_type")
    if not _ID_NUMBER.match((id_doc_number or "").strip()):
        _fail("The identity document number is not valid.", code="invalid_id_document")


def ensure_host(host_user_id: int) -> None:
    """The host must exist and be faculty/staff (BR-185)."""
    dto = directory.get_users([host_user_id]).get(host_user_id)
    if dto is None or dto.kind not in authz.HOST_KINDS:
        _fail("The host is not a faculty or staff member.", code="invalid_host")


# --- blacklist rejection (BR-051) --------------------------------------------------------

def role_user_ids(role) -> list[int]:
    """Users holding `role` right now (to address Admin / Security notices)."""
    now = timezone.now()
    return sorted(set(RoleAssignment.objects.filter(
        role=role, revoked_at__isnull=True, starts_at__lte=now, ends_at__gt=now)
        .values_list("user_id", flat=True)))


def record_blacklist_hit(*, actor, hit, visitor_label: str) -> Alert:
    """Alert + audit + security notice. Run it in its own committed block."""
    alert = Alert.objects.create(
        kind=Alert.Kind.BLACKLIST_HIT, severity=getattr(hit, "severity", "") or "high",
        ref_type="blacklist_entry", ref_id=hit.entry_id,
        detail={"checkpoint": hit.checkpoint, "matched": list(hit.matched_fields),
                "version": hit.version, "visitor": visitor_label})
    audit.record(actor=actor, action="vms.request.blacklist_rejected", entity=alert,
                 detail={"entry_id": hit.entry_id})
    for uid in role_user_ids(RoleAssignment.Role.SECURITY):
        notify.enqueue(
            topic="alert.blacklist_hit", dedupe_key=f"alert:{alert.pk}:{uid}",
            subject="Blacklisted visitor blocked",
            body=f"A {hit.checkpoint} attempt by {visitor_label} matched blacklist "
                 f"entry #{hit.entry_id} and was rejected.",
            user_id=uid)
    return alert


# --- visitor master data (CFR-032, CFR-029) ----------------------------------------------

def resolve_visitor(*, session_visitor, data: dict, update_existing=True) -> Visitor:
    """The visiting person's master record, keyed on the identity document.

    A fresh login row (no document yet) is completed in place when the submitted
    email is its own, so one person keeps one record.
    """
    doc_type, doc_no = data["id_doc_type"], data["id_doc_number"].strip().upper()
    fields = {"full_name": data["full_name"].strip(), "phone": data["phone"].strip(),
              "email": (data.get("email") or "").strip().lower()}
    visitor = (Visitor.objects.select_for_update()
               .filter(id_doc_type=doc_type, id_doc_number=doc_no).first())
    if visitor is not None:
        changed = ([k for k, v in fields.items() if v and getattr(visitor, k) != v]
                   if update_existing else [])
        for k in changed:
            setattr(visitor, k, fields[k])
        if changed:
            visitor.save(update_fields=changed)
        return visitor
    own = (Visitor.objects.select_for_update().filter(pk=session_visitor.pk).first()
           if session_visitor is not None else None)
    if (own is not None and not own.id_doc_number
            and (not fields["email"] or fields["email"] == own.email.lower())):
        for k, v in {**fields, "id_doc_type": doc_type, "id_doc_number": doc_no}.items():
            if v:
                setattr(own, k, v)
        own.save()
        return own
    return Visitor.objects.create(id_doc_type=doc_type, id_doc_number=doc_no, **fields)


# --- bypass detection (BR-195 / BR-196 / BR-197, decision D-16) ----------------------------

def _zone_ids(requested) -> set[int]:
    return {z.pk if hasattr(z, "pk") else int(z) for z in requested}


def active_vip(visitor, start, end, zone_ids, now) -> VipPermission | None:
    """VIP override applies only inside its recorded scope: validity window and zones."""
    rows = VipPermission.objects.filter(
        visitor=visitor, revoked_at__isnull=True, valid_from__lte=now,
        valid_until__gte=now).order_by("-valid_until")
    for vip in rows:
        if (start >= vip.valid_from and end <= vip.valid_until
                and zone_ids <= set(vip.zones.values_list("pk", flat=True))):
            return vip
    return None


def matching_pre_authorization(*, visitor, host_user_id, start, end, zone_ids, now,
                               lock=False) -> PreAuthorization | None:
    """A live pre-authorisation of this host for this visitor covering the visit."""
    qs = PreAuthorization.objects.filter(
        host_user_id=host_user_id, visitor=visitor, revoked_at__isnull=True,
        valid_from__lte=now, valid_until__gte=now, used_visits__lt=F("max_visits"))
    if lock:
        qs = qs.select_for_update()
    for pa in qs.order_by("valid_until"):
        if (start >= pa.valid_from and end <= pa.valid_until
                and zone_ids <= set(pa.zones.values_list("pk", flat=True))):
            return pa
    return None


# --- submit ---------------------------------------------------------------------------------

def _principal(visitor):
    if visitor is None:
        return None
    return VisitorPrincipal(visitor_id=visitor.pk, email=visitor.email,
                            display_name=visitor.full_name)


def submit(*, session_visitor, data: dict) -> VisitRequest:
    """File a pre-registration. Returns the request in `pending`, `awaiting_admin`
    (urgent, BW-22) or `approved` with its pass (pre-authorised / VIP).

    Raises BadRequestError (validation, advance window, blacklist, duplicate).
    """
    validate_fields(data)
    validate_id_document(data["id_doc_type"], data["id_doc_number"])
    now = timezone.now()
    start, end = data["scheduled_start"], data["scheduled_end"]
    if start <= now:
        _fail("The visit must start in the future.", code="start_in_past")
    host_id = int(data["host_user_id"])
    ensure_host(host_id)
    zones = list(data.get("requested_zones") or [])
    zone_ids = _zone_ids(zones)
    if zone_ids and Zone.objects.filter(pk__in=zone_ids, is_active=True).count() != len(zone_ids):
        _fail("A requested zone does not exist or is inactive.", code="invalid_zone")
    pol = policy.effective()
    l_start, l_end = timezone.localtime(start), timezone.localtime(end)
    if not (l_start.date() == l_end.date()
            and policy_eval.within_visiting_hours(
                l_start, pol.visiting_hours_start, pol.visiting_hours_end)
            and policy_eval.within_visiting_hours(
                l_end, pol.visiting_hours_start, pol.visiting_hours_end)):
        _fail("The visit falls outside visiting hours.", code="outside_visiting_hours")

    hit = blacklist.check(
        checkpoint="pre_registration", name=data["full_name"],
        id_doc_number=data["id_doc_number"], phone=data["phone"],
        email=data.get("email", ""))
    if hit is not None:
        with transaction.atomic():   # commit the alert before refusing (BR-051)
            record_blacklist_hit(actor=_principal(session_visitor), hit=hit,
                                 visitor_label=data["full_name"])
        raise BadRequestError("This visitor is not permitted entry.",
                              code="visitor_blacklisted")

    with transaction.atomic():
        visitor = resolve_visitor(session_visitor=session_visitor, data=data)
        if VisitRequest.objects.filter(
                visitor=visitor, host_user_id=host_id, scheduled_start=start,
                status__in=[VisitRequest.Status.PENDING, VisitRequest.Status.AWAITING_ADMIN,
                            VisitRequest.Status.APPROVED]).exists():
            raise BadRequestError("A request already exists for this visit.",
                                  code="duplicate_request")

        vip = active_vip(visitor, start, end, zone_ids, now)
        pre_auth = None
        if vip is None:
            pre_auth = matching_pre_authorization(
                visitor=visitor, host_user_id=host_id, start=start, end=end,
                zone_ids=zone_ids, now=now, lock=True)
        bypass = vip is not None or pre_auth is not None

        urgent = False
        if not bypass and not policy_eval.advance_ok(now, start, pol.advance_registration_hours):
            if pol.allow_same_day_urgent and policy_eval.is_same_day(now, start):
                urgent = True        # BR-203
            else:
                _fail(f"Register at least {pol.advance_registration_hours} hours ahead.",
                      code="advance_window")

        state = request_state.next_state(
            request_state.PRE_REGISTERED, request_state.NOT_SUBMITTED,
            request_state.SUBMIT, request_state.VISITOR,
            {"urgent": urgent, "bypass_approval": bypass})
        source = (VisitRequest.Source.VIP if vip else
                  VisitRequest.Source.PRE_AUTHORIZED if pre_auth else
                  VisitRequest.Source.PRE_REGISTERED)
        vr = VisitRequest.objects.create(
            visitor=visitor, created_by_visitor=session_visitor, host_user_id=host_id,
            purpose=data["purpose"].strip(), scheduled_start=start, scheduled_end=end,
            status=state, source=source, is_urgent=urgent,
            urgent_decision=(VisitRequest.UrgentDecision.PENDING if urgent
                             else VisitRequest.UrgentDecision.NONE),
            expires_at=(now + timedelta(hours=pol.approval_timeout_hours)
                        if state == VisitRequest.Status.PENDING else None),
            decided_at=now if bypass else None)
        vr.requested_zones.set(zones)
        audit.record(actor=_principal(session_visitor), action="vms.request.submitted",
                     entity=vr, detail={"host_user_id": host_id, "source": source,
                                        "urgent": urgent, "state": state,
                                        "policy_version": pol.version})
        if state == VisitRequest.Status.APPROVED:
            _issue_bypass_pass(vr, vip, pre_auth)
        elif state == VisitRequest.Status.AWAITING_ADMIN:
            for uid in role_user_ids(RoleAssignment.Role.ADMIN):
                notify.enqueue(
                    topic="request.urgent", dedupe_key=f"request-urgent:{vr.pk}:{uid}",
                    subject="Same-day urgent visit needs a decision",
                    body=f"{visitor.full_name} asked for an urgent same-day visit.",
                    user_id=uid)
        else:
            notify.enqueue(
                topic="request.submitted", dedupe_key=f"request-submitted:{vr.pk}",
                subject="New visit request",
                body=f"{visitor.full_name} asked to visit you: {vr.purpose}",
                user_id=host_id)
    return vr


def _issue_bypass_pass(vr, vip, pre_auth) -> VisitPass:
    """BW-VMS-05 (VIP pass) and BW-VMS-04 (pre-authorised, PRE_REGISTERED pass)."""
    if vip is not None:
        vp = passes.issue_pass(request=vr, pass_type=VisitPass.PassType.VIP,
                               issued_by=vip.granted_by_user_id)
        audit.record(actor=None, action="vms.request.vip_override", entity=vr,
                     detail={"vip_permission_id": vip.pk})
    else:
        vp = passes.issue_pass(request=vr, pass_type=VisitPass.PassType.PRE_REGISTERED,
                               issued_by=pre_auth.host_user_id)
        pre_auth.used_visits += 1
        pre_auth.save(update_fields=["used_visits"])
        audit.record(actor=None, action="vms.preauth.used", entity=pre_auth,
                     detail={"request_id": vr.pk, "used_visits": pre_auth.used_visits})
    notify.enqueue(topic="pass.issued", dedupe_key=f"pass-issued:{vp.pk}",
                   subject="Your visit pass is ready",
                   body="Your visit is approved. Open the pass from your visits page.",
                   visitor=vr.visitor)
    return vp


def record_pass_viewed(*, visitor, visit_request, visit_pass) -> None:
    """UC-012: retrieving the pass is itself audited."""
    audit.record(actor=_principal(visitor), action="vms.pass.viewed",
                 entity=visit_pass, detail={"request_id": visit_request.pk})
