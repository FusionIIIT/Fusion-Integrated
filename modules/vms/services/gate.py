"""Gate validation, check-in, override, escalation and manual entries.

# VMS-CFR-013, 014, 015, 027 · VMS-UC-018/019/020 · BW-VMS-09/10/11
# VMS-BR-077, 082, 085, 112, 116, 117, 190, 191
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.domain import pass_rules, request_state
from modules.vms.models import (
    Alert,
    Escalation,
    Gate,
    GateOverride,
    VisitLog,
    VisitPass,
    VisitRequest,
    Zone,
)
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import zone_access
from modules.vms.services.common import audit, authz, notify

E = VisitLog.Event
MIN_JUSTIFICATION = 15

CHECKED_IN = "checked_in"
DENIED = "denied"
UNKNOWN = "unknown_credential"


@dataclass
class GateResult:
    outcome: str                                   # CHECKED_IN | DENIED | UNKNOWN
    log: VisitLog | None = None
    failures: list = field(default_factory=list)   # domain Failure objects
    override_eligible: bool = False
    vip_override: bool = False
    visit_request: VisitRequest | None = None


# --- helpers -------------------------------------------------------------------------

def _active_gate(gate_id) -> Gate:
    gate = Gate.objects.filter(pk=gate_id).first()
    if gate is None:
        raise NotFoundError("Gate not found.")
    if not gate.is_active:
        raise ConflictError("This gate is not active.", code="gate_inactive")
    return gate


def _check_zone_exists(zone_id) -> None:
    if zone_id is not None and not Zone.objects.filter(pk=zone_id).exists():
        raise BadRequestError("Unknown zone.", code="unknown_zone")


def locked_pass(*, pass_id=None, credential=None) -> VisitPass | None:
    """Fetch and row-lock the pass so concurrent check-ins serialise."""
    qs = (VisitPass.objects.select_for_update(of=("self",))
          .select_related("visit_request__visitor"))
    if pass_id is not None:
        return qs.filter(pk=pass_id).first()
    if credential.get("qr_token"):
        return qs.filter(qr_token=credential["qr_token"]).first()
    if credential.get("otp"):                       # OTP only among active passes
        return qs.filter(otp=credential["otp"], is_active=True).order_by("-id").first()
    raise BadRequestError("qr_token or otp is required.", code="credential_required")


def _is_admin(actor, gate_id) -> bool:
    try:
        authz.require_role(actor, "admin", gate_id=gate_id)
    except PermissionDeniedError:
        return False
    return True


def _fingerprint(credential: dict) -> str:
    kind = "qr_token" if credential.get("qr_token") else "otp"
    return f"{kind}:{hashlib.sha256(credential[kind].encode()).hexdigest()[:12]}"


def _unknown_credential(*, actor, gate, credential, device_id) -> GateResult:
    """No pass, so no VisitLog (it needs one): an alert plus an audit row (CFR-013)."""
    alert = zone_access.raise_alert(
        kind=Alert.Kind.GATE_FAILURE, severity=Alert.Severity.MEDIUM, ref_type="gate",
        ref_id=gate.pk, detail={"gate_id": gate.pk, "device_id": device_id,
                                "failures": ["unknown_credential"],
                                "credential": _fingerprint(credential)})
    audit.record(actor=actor, action="vms.gate.unknown_credential", entity=alert,
                 detail={"gate_id": gate.pk, "credential": _fingerprint(credential)})
    zone_access.notify_staff(
        gate_id=gate.pk, topic="gate.denied", key=f"gate-denied-unknown:{alert.pk}",
        subject="Unrecognised credential at gate",
        body=f"An unknown pass was presented at {gate.name}.")
    return GateResult(outcome=UNKNOWN)


def _deny(*, actor, gate, vp, ev, zone_id, device_id, manual=False) -> GateResult:
    """Log the denial, raise the alert and tell staff (BR-082, 116, 117)."""
    log = VisitLog.objects.create(
        visit_pass=vp, event=E.DENIED, reason=",".join(ev.codes)[:255], zone_id=zone_id,
        detail={"failures": list(ev.codes), "manual": manual},
        gate=gate, device_id=device_id[:80], entry_point="manual" if manual else gate.name,
        logged_by_user_id=actor.user_id)
    visitor = vp.visit_request.visitor
    if ev.hit:                                              # BR-117
        kind, severity = Alert.Kind.BLACKLIST_HIT, ev.hit.severity
        detail_extra = {"blacklist_entry_id": ev.hit.entry_id,
                        "matched_fields": list(ev.hit.matched_fields)}
    else:
        kind, severity, detail_extra = Alert.Kind.GATE_FAILURE, Alert.Severity.MEDIUM, {}
    alert = zone_access.raise_alert(
        kind=kind, severity=severity, ref_type="visitlog", ref_id=log.pk,
        detail={"gate_id": gate.pk, "pass_id": vp.pk, "failures": ev.codes,
                "device_id": device_id, **detail_extra})
    audit.record(actor=actor, action="vms.gate.denied", entity=log, detail={
        "pass_id": vp.pk, "failures": ev.codes, "alert_id": alert.pk, "manual": manual})
    zone_access.notify_staff(
        gate_id=gate.pk, topic="gate.denied", key=f"gate-denied:{log.pk}",
        subject="Gate entry denied",
        body=f"{visitor.full_name} was denied at {gate.name}: {', '.join(ev.codes)}.")
    return GateResult(outcome=DENIED, log=log, failures=ev.failures,
                      override_eligible=ev.override_eligible, visit_request=vp.visit_request)


def _admit(*, actor, gate, vp, zone_id, device_id, vip_waived, reason="", entry_point="",
           action="vms.gate.checked_in", extra=None, log_detail=None) -> GateResult:
    vr = vp.visit_request
    # `reason` keeps the legacy codes (reports parse them); `detail` is the structured record.
    log = VisitLog.objects.create(
        visit_pass=vp, event=E.CHECK_IN, zone_id=zone_id or gate.zone_id, gate=gate,
        device_id=device_id[:80], entry_point=entry_point or gate.name,
        reason=reason or ("vip_override" if vip_waived else ""),
        detail={"vip_override": bool(vip_waived), **(log_detail or {})},
        logged_by_user_id=actor.user_id)
    audit.record(actor=actor, action=action, entity=vp, detail={
        "visit_log_id": log.pk, "gate_id": gate.pk, "vip_override": vip_waived, **(extra or {})})
    notify.enqueue(
        topic="visit.checked_in", dedupe_key=f"checked-in:{log.pk}",
        subject="Your visitor has arrived",
        body=f"{vr.visitor.full_name} checked in at {gate.name}.",
        user_id=vr.host_user_id, channels=("inapp",))
    return GateResult(outcome=CHECKED_IN, log=log, vip_override=vip_waived, visit_request=vr)


# --- validate and check in (BW-VMS-09) ------------------------------------------------

def validate_and_check_in(*, security_actor, credential: dict, gate_id: int,
                          zone_id: int | None = None, device_id: str = "") -> GateResult:
    """Validate a QR token or OTP and check the visitor in.

    `credential` is ``{"qr_token": ...}`` or ``{"otp": ...}``. Every failure is
    returned (rule order); the first is the logged reason. A denial commits
    its log, alert and notice, so the caller gets a result, not an exception.
    A concurrent second check-in waits on the pass row lock and is then denied
    ``already_inside`` (BR-082).
    """
    now = timezone.now()
    gate = _active_gate(gate_id)
    authz.require_role(security_actor, "security", gate_id=gate.pk, at=now)    # BR-181
    _check_zone_exists(zone_id)
    with transaction.atomic():
        vp = locked_pass(credential=credential)
        if vp is None:
            return _unknown_credential(actor=security_actor, gate=gate,
                                       credential=credential, device_id=device_id)
        inside = gate_sel.open_check_in(vp.pk) is not None
        ev = zone_access.evaluate(vp, now=now, zone_id=zone_id, open_checkin=inside)
        if ev.failures:
            return _deny(actor=security_actor, gate=gate, vp=vp, ev=ev, zone_id=zone_id,
                         device_id=device_id)
        return _admit(actor=security_actor, gate=gate, vp=vp, zone_id=zone_id,
                      device_id=device_id, vip_waived=ev.vip_waived)


# --- override (BW-VMS-10, BR-085) -----------------------------------------------------

def override(*, admin_actor, denial_log_id: int, justification: str) -> GateResult:
    """An Admin lets a denied visitor in. Only override-eligible failures qualify
    (D-14); the blacklist is re-checked now so a hit since the denial blocks it."""
    authz.require(admin_actor, "vms.gate.override")
    justification = (justification or "").strip()
    if len(justification) < MIN_JUSTIFICATION:
        raise BadRequestError(
            f"A justification of at least {MIN_JUSTIFICATION} characters is required.",
            code="justification_required")
    denial = (VisitLog.objects.select_related("gate").filter(pk=denial_log_id,
                                                              event=E.DENIED).first())
    if denial is None:
        raise NotFoundError("Denial not found.")
    authz.require_role(admin_actor, "admin", gate_id=denial.gate_id)
    codes = (denial.detail or {}).get("failures") or [c for c in denial.reason.split(",") if c]
    if not codes or not all(c in pass_rules.OVERRIDE_ELIGIBLE for c in codes):
        raise ConflictError("This denial cannot be overridden.", code="not_overridable",
                            details=[{"failures": codes}])
    now = timezone.now()
    with transaction.atomic():
        vp = locked_pass(pass_id=denial.visit_pass_id)
        if GateOverride.objects.filter(visit_log=denial).exists():
            raise ConflictError("This denial was already overridden.", code="already_overridden")
        if denial.gate is None:
            raise ConflictError("Only gate denials can be overridden.", code="not_overridable")
        fresh = zone_access.evaluate(vp, now=now, open_checkin=False)
        if fresh.hit or any(f.code == pass_rules.TERMINATED for f in fresh.failures):
            raise ConflictError("This denial can no longer be overridden.",
                                code="not_overridable")
        if gate_sel.open_check_in(vp.pk) is not None:
            raise ConflictError("The visitor is already inside.", code="already_inside")
        GateOverride.objects.create(visit_log=denial, admin_user_id=admin_actor.user_id,
                                    justification=justification[:500])
        return _admit(
            actor=admin_actor, gate=denial.gate, vp=vp, zone_id=denial.zone_id,
            device_id=denial.device_id, vip_waived=False, reason="override_check_in",
            entry_point=denial.entry_point, action="vms.gate.override_check_in",
            log_detail={"override": True, "denial_log_id": denial.pk},
            extra={"denial_log_id": denial.pk, "overridden": codes,
                   "justification": justification})


# --- escalation (UC-019) -------------------------------------------------------------

def escalate(*, security_actor, visit_log_id: int, note: str) -> Escalation:
    """Security passes a denial to an Admin; raises a 'suspicious' alert."""
    log = VisitLog.objects.select_related("gate", "visit_pass").filter(
        pk=visit_log_id, event=E.DENIED).first()
    if log is None:
        raise NotFoundError("Denial not found.")
    authz.require_role(security_actor, "security", gate_id=log.gate_id)
    note = (note or "").strip()
    if not note:
        raise BadRequestError("A note is required.", code="note_required")
    with transaction.atomic():
        if Escalation.objects.filter(visit_log=log, status=Escalation.Status.OPEN).exists():
            raise ConflictError("This denial is already escalated.", code="already_escalated")
        esc = Escalation.objects.create(
            visit_log=log, raised_by_user_id=security_actor.user_id, note=note[:500])
        alert = zone_access.raise_alert(
            kind=Alert.Kind.SUSPICIOUS, severity=Alert.Severity.HIGH, ref_type="escalation",
            ref_id=esc.pk, detail={"gate_id": log.gate_id, "visit_log_id": log.pk,
                                   "pass_id": log.visit_pass_id, "note": note})
        audit.record(actor=security_actor, action="vms.gate.escalated", entity=esc,
                     detail={"visit_log_id": log.pk, "alert_id": alert.pk})
        zone_access.notify_staff(
            gate_id=log.gate_id, topic="gate.escalated", key=f"gate-escalated:{esc.pk}",
            subject="Gate denial escalated", body=note)
    return esc


def resolve_escalation(*, admin_actor, escalation_id: int, note: str) -> Escalation:
    authz.require(admin_actor, "vms.gate.override")
    authz.require_role(admin_actor, "admin")
    note = (note or "").strip()
    if not note:
        raise BadRequestError("A resolution note is required.", code="note_required")
    with transaction.atomic():
        esc = Escalation.objects.select_for_update().filter(pk=escalation_id).first()
        if esc is None:
            raise NotFoundError()
        if esc.status != Escalation.Status.OPEN:
            raise ConflictError("This escalation is already resolved.", code="already_resolved")
        esc.status = Escalation.Status.RESOLVED
        esc.resolved_by_user_id = admin_actor.user_id
        esc.resolved_at = timezone.now()
        esc.save(update_fields=["status", "resolved_by_user_id", "resolved_at"])
        audit.record(actor=admin_actor, action="vms.gate.escalation_resolved", entity=esc,
                     detail={"note": note})
    return esc


# --- manual entry (UC-020, CFR-015) --------------------------------------------------

def record_manual_entry(*, security_actor, pass_id: int, event: str, reason: str,
                        gate_id: int, zone_id: int | None = None) -> GateResult:
    """Log an entry by hand when the gate device fails. A reason is mandatory.

    Check-in runs the same validations; an Admin may waive override-eligible
    failures but never the blacklist or a terminated pass (D-14).
    """
    reason = (reason or "").strip()
    if not reason:
        raise BadRequestError("A reason is required.", code="reason_required")
    if event not in (E.CHECK_IN, E.CHECK_OUT):
        raise BadRequestError("event must be check_in or check_out.", code="invalid_event")
    now = timezone.now()
    gate = _active_gate(gate_id)
    authz.require_role(security_actor, "security", gate_id=gate.pk, at=now)
    _check_zone_exists(zone_id)
    admin = _is_admin(security_actor, gate.pk)
    with transaction.atomic():
        vp = locked_pass(pass_id=pass_id)
        if vp is None:
            raise NotFoundError("Pass not found.")
        inside = gate_sel.open_check_in(vp.pk) is not None
        if event == E.CHECK_OUT:
            return _manual_check_out(actor=security_actor, gate=gate, vp=vp, inside=inside,
                                     reason=reason)
        ev = zone_access.evaluate(vp, now=now, zone_id=zone_id, open_checkin=inside)
        waivable = admin and ev.failures and ev.override_eligible
        if ev.failures and not waivable:
            return _deny(actor=security_actor, gate=gate, vp=vp, ev=ev, zone_id=zone_id,
                         device_id=gate.device_id, manual=True)
        return _admit(
            actor=security_actor, gate=gate, vp=vp, zone_id=zone_id, device_id=gate.device_id,
            vip_waived=ev.vip_waived, reason=f"manual: {reason}"[:255], entry_point="manual",
            action="vms.gate.manual_entry",
            log_detail={"manual": True, "manual_reason": reason,
                        "waived": list(ev.codes) if waivable else []},
            extra={"manual": True, "event": "check_in", "reason": reason,
                   "waived": ev.codes if waivable else []})


def _manual_check_out(*, actor, gate, vp, inside, reason) -> GateResult:
    if not inside:
        raise ConflictError("No open check-in for this pass.", code="no_open_check_in")
    vr = VisitRequest.objects.select_for_update().get(pk=vp.visit_request_id)
    kind = (request_state.WALK_IN if vr.source == VisitRequest.Source.WALK_IN
            else request_state.PRE_REGISTERED)
    try:
        vr.status = request_state.next_state(
            kind, vr.status, request_state.COMPLETE, request_state.SECURITY)
    except request_state.InvalidTransition:
        raise ConflictError("This visit cannot be completed from its current state.") from None
    log = VisitLog.objects.create(
        visit_pass=vp, event=E.CHECK_OUT, gate=gate, zone_id=gate.zone_id,
        entry_point="manual", device_id=gate.device_id[:80],
        reason=f"manual: {reason}"[:255], logged_by_user_id=actor.user_id,
        detail={"manual": True, "manual_reason": reason})
    vr.save(update_fields=["status"])
    audit.record(actor=actor, action="vms.gate.manual_entry", entity=vp, detail={
        "manual": True, "event": "check_out", "reason": reason, "visit_log_id": log.pk})
    return GateResult(outcome="checked_out", log=log, visit_request=vr)
