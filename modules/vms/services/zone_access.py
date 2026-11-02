"""Zone access checks, time-boxed elevation, alert handling and the shared
gate evaluation core.

# VMS-CFR-026, CFR-014/027 (alerts) · VMS-BR-096, 190, 191, 192, 197 · BW-VMS-12/13/14
# Decisions D-12 (zone events come from a reader/gate), D-15 (elevation cap), D-16 (VIP scope)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.domain import pass_rules
from modules.vms.models import (
    Alert,
    EventAttendee,
    IntegrationSetting,
    VipPermission,
    VisitLog,
    VisitPass,
    Zone,
    ZoneElevation,
)
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import blacklist, policy
from modules.vms.services.common import audit, authz, notify

E = VisitLog.Event
DEFAULT_MAX_ELEVATION_MINUTES = 120
ALERT_OUTCOMES = ("resolved", "false_alarm", "escalated")


# --- shared evaluation core -----------------------------------------------------------

@dataclass
class Evaluation:
    failures: list = field(default_factory=list)
    hit: object = None                 # BlacklistHit | None
    vip_waived: bool = False

    @property
    def codes(self) -> list[str]:
        return [f.code for f in self.failures]

    @property
    def override_eligible(self) -> bool:
        return pass_rules.is_overridable(self.failures)


def vip_zone_ids(visitor_id: int, at) -> set[int]:
    """Zones inside the visitor's active VIP scope (BR-197, D-16)."""
    rows = VipPermission.objects.filter(
        visitor_id=visitor_id, revoked_at__isnull=True,
        valid_from__lte=at, valid_until__gte=at).values_list("zones__pk", flat=True)
    return {z for z in rows if z is not None}


def permitted_zone_ids(vp: VisitPass, at, pol) -> set[int]:
    """Pass zones plus active elevations. An empty pass means every
    non-restricted zone, so an elevation adds to that set rather than
    replacing it."""
    allowed = set(vp.allowed_zones.values_list("pk", flat=True))
    elevated = set(vp.elevations.filter(starts_at__lte=at, ends_at__gt=at,
                                        revoked_at__isnull=True)
                   .values_list("zone_id", flat=True))
    if elevated and not allowed:
        allowed = set(Zone.objects.filter(is_active=True)
                      .exclude(pk__in=pol.restricted_zone_ids).values_list("pk", flat=True))
    return allowed | elevated


def evaluate(vp: VisitPass, *, now, zone_id=None, open_checkin=False, pol=None) -> Evaluation:
    """Run every gate rule for a pass at `now` (BR-077, 190, 112/116, 191, 082).

    `vp` must have visit_request and its visitor loaded. Policy and zone sets
    are read only when a zone is being checked, which keeps a plain entry cheap.
    """
    vr = vp.visit_request
    visitor = vr.visitor
    hit = blacklist.check(
        checkpoint="gate", name=visitor.full_name, id_doc_number=visitor.id_doc_number,
        phone=visitor.phone, email=visitor.email, at=now)
    terminated = vp.terminated_at is not None and vp.terminated_at <= now
    subject = SimpleNamespace(
        is_active=vp.is_active and vr.status == "approved", terminated=terminated,
        valid_from=vp.valid_from, valid_until=vp.valid_until, allowed_zone_ids=set())
    if vp.event_id:
        slot = (EventAttendee.objects.filter(visit_pass_id=vp.pk, slot_start__isnull=False,
                                              slot_end__isnull=False)
                .values_list("slot_start", "slot_end").first())
        if slot:
            subject.slot_start, subject.slot_end = slot
    if zone_id is not None:
        pol = pol or policy.snapshot_for(vr)
        subject.allowed_zone_ids = permitted_zone_ids(vp, now, pol)
    failures = pass_rules.validate_at_gate(
        subject, now, zone_id, pol, blacklisted=hit is not None, open_checkin=open_checkin)
    waived = False
    if (vp.pass_type == VisitPass.PassType.VIP and zone_id is not None
            and any(f.code == pass_rules.ZONE_NOT_PERMITTED for f in failures)
            and zone_id in vip_zone_ids(visitor.pk, now)):
        failures = [f for f in failures if f.code != pass_rules.ZONE_NOT_PERMITTED]
        waived = True
    return Evaluation(failures=failures, hit=hit, vip_waived=waived)


def notify_staff(*, gate_id, topic, key, subject, body) -> None:
    """In-app notice to the admins and the security staff covering `gate_id`."""
    for uid in gate_sel.alert_recipients(gate_id):
        notify.enqueue(topic=topic, dedupe_key=f"{key}:{uid}", subject=subject, body=body,
                       user_id=uid, channels=("inapp",))


def raise_alert(*, kind, severity, ref_type, ref_id, detail) -> Alert:
    return Alert.objects.create(kind=kind, severity=severity, ref_type=ref_type,
                                ref_id=ref_id, detail=detail)


# --- zone check (BW-VMS-12/13) -------------------------------------------------------

def check_zone(*, actor, pass_id: int, zone_id: int, reader_id: str = "", gate_id=None,
               at=None) -> dict:
    """A reader or the gate reports a pass at a zone (D-12). Allowed or denied is logged.

    Callers are a security user scoped to the zone, or a service token (kind
    "service"). A denial raises a zone_violation alert (BR-191/192).
    """
    now = at or timezone.now()
    if getattr(actor, "kind", "") != "service":
        authz.require_role(actor, "security", zone_id=zone_id, gate_id=gate_id, at=now)
    zone = Zone.objects.filter(pk=zone_id, is_active=True).first()
    if zone is None:
        raise NotFoundError("Zone not found.")
    with transaction.atomic():
        vp = (VisitPass.objects.select_related("visit_request__visitor")
              .filter(pk=pass_id).first())
        if vp is None:
            raise NotFoundError("Pass not found.")
        ev = evaluate(vp, now=now, zone_id=zone_id)
        actor_id = getattr(actor, "user_id", None)
        if not ev.failures:
            log = VisitLog.objects.create(
                visit_pass=vp, event=E.ZONE_ALLOWED, zone=zone, device_id=reader_id[:80],
                gate_id=gate_id, logged_by_user_id=actor_id,
                reason="vip_override" if ev.vip_waived else "",
                detail={"vip_override": bool(ev.vip_waived)})
            if ev.vip_waived:
                audit.record(actor=actor, action="vms.zone.vip_override", entity=vp,
                             detail={"zone_id": zone_id, "visit_log_id": log.pk})
            return {"allowed": True, "failures": [], "visit_log": log,
                    "vip_override": ev.vip_waived}
        log = VisitLog.objects.create(
            visit_pass=vp, event=E.ZONE_DENIED, zone=zone, device_id=reader_id[:80],
            gate_id=gate_id, logged_by_user_id=actor_id,
            reason=",".join(ev.codes)[:255], detail={"failures": list(ev.codes)})
        severity = (Alert.Severity.CRITICAL if ev.hit else
                    Alert.Severity.HIGH if zone.is_restricted else Alert.Severity.MEDIUM)
        alert = raise_alert(
            kind=Alert.Kind.ZONE_VIOLATION, severity=severity, ref_type="visitlog",
            ref_id=log.pk, detail={"pass_id": vp.pk, "zone_id": zone_id, "gate_id": gate_id,
                                   "reader_id": reader_id, "failures": ev.codes})
        audit.record(actor=actor, action="vms.zone.denied", entity=log,
                     detail={"failures": ev.codes, "alert_id": alert.pk})
        notify_staff(
            gate_id=gate_id, topic="zone.violation", key=f"zone-violation:{log.pk}",
            subject="Unauthorized zone access",
            body=f"{vp.visit_request.visitor.full_name} was denied zone {zone.name}.")
        return {"allowed": False, "failures": ev.failures, "visit_log": log,
                "alert": alert, "vip_override": False}


# --- elevation (BR-096, D-15) --------------------------------------------------------

def max_elevation_minutes() -> int:
    row = IntegrationSetting.objects.filter(key="max_elevation_minutes").first()
    value = row.value if row else None
    if isinstance(value, dict):
        value = value.get("minutes", value.get("value"))
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 \
        else DEFAULT_MAX_ELEVATION_MINUTES


def grant_elevation(*, admin_actor, pass_id: int, zone_id: int, ends_at,
                    reason: str) -> ZoneElevation:
    """Time-boxed extra zone for one pass. `ends_at` is mandatory and at most
    max_elevation_minutes away (BR-096, D-15). A terminated, inactive or
    blacklisted pass cannot be elevated."""
    authz.require(admin_actor, "vms.zone.elevate")
    authz.require_role(admin_actor, "admin", zone_id=zone_id)
    reason = (reason or "").strip()
    if not reason:
        raise BadRequestError("A reason is required.", code="reason_required")
    if ends_at is None:
        raise BadRequestError("An end time is required.", code="ends_at_required")
    now = timezone.now()
    cap = max_elevation_minutes()
    if ends_at <= now:
        raise BadRequestError("The end time must be in the future.", code="ends_at_past")
    if (ends_at - now).total_seconds() > cap * 60:
        raise BadRequestError(f"An elevation may last at most {cap} minutes.",
                              code="elevation_too_long", details=[{"max_minutes": cap}])
    zone = Zone.objects.filter(pk=zone_id, is_active=True).first()
    if zone is None:
        raise NotFoundError("Zone not found.")
    with transaction.atomic():
        vp = (VisitPass.objects.select_for_update(of=("self",))
              .select_related("visit_request__visitor").filter(pk=pass_id).first())
        if vp is None:
            raise NotFoundError("Pass not found.")
        if (not vp.is_active or vp.terminated_at is not None
                or vp.visit_request.status != "approved" or vp.valid_until <= now):
            raise ConflictError("Only an active pass can be elevated.", code="pass_not_active")
        visitor = vp.visit_request.visitor
        if blacklist.check(checkpoint="gate", name=visitor.full_name,
                           id_doc_number=visitor.id_doc_number, phone=visitor.phone,
                           email=visitor.email, at=now):
            raise ConflictError("This visitor is blacklisted.", code="blacklisted")
        elevation = ZoneElevation.objects.create(
            visit_pass=vp, zone=zone, starts_at=now, ends_at=ends_at,
            granted_by_user_id=admin_actor.user_id, reason=reason[:255])
        audit.record(actor=admin_actor, action="vms.zone.elevation_granted", entity=elevation,
                     detail={"pass_id": vp.pk, "zone_id": zone_id, "reason": reason,
                             "ends_at": ends_at.isoformat()})
    return elevation


def revoke_elevation(*, admin_actor, elevation_id: int) -> ZoneElevation:
    authz.require(admin_actor, "vms.zone.elevate")
    authz.require_role(admin_actor, "admin")
    with transaction.atomic():
        el = ZoneElevation.objects.select_for_update().filter(pk=elevation_id).first()
        if el is None:
            raise NotFoundError()
        now = timezone.now()
        if el.revoked_at is not None or el.ends_at <= now:
            raise ConflictError("This elevation is no longer active.", code="not_active")
        el.revoked_at = now
        el.save(update_fields=["revoked_at"])
        audit.record(actor=admin_actor, action="vms.zone.elevation_revoked", entity=el,
                     detail={"pass_id": el.visit_pass_id, "zone_id": el.zone_id})
    return el


# --- alerts (UC-025) -----------------------------------------------------------------

def handle_alert(*, actor, alert_id: int, outcome: str, note: str = "") -> Alert:
    """Admin or security closes an open alert with an outcome."""
    authz.require_role(actor, "security")
    if outcome not in ALERT_OUTCOMES:
        raise BadRequestError(f"outcome must be one of {', '.join(ALERT_OUTCOMES)}.",
                              code="invalid_outcome")
    with transaction.atomic():
        alert = Alert.objects.select_for_update().filter(pk=alert_id).first()
        if alert is None:
            raise NotFoundError()
        if alert.status != Alert.Status.OPEN:
            raise ConflictError("This alert was already handled.", code="already_handled")
        alert.status = Alert.Status.HANDLED
        alert.handled_by_user_id = actor.user_id
        alert.handled_at = timezone.now()
        alert.detail = {**alert.detail, "outcome": outcome, "handling_note": note}
        alert.save(update_fields=["status", "handled_by_user_id", "handled_at", "detail"])
        audit.record(actor=actor, action="vms.alert.handled", entity=alert,
                     detail={"outcome": outcome, "note": note})
    return alert
