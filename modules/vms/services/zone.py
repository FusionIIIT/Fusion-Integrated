"""Zone access validation and temporary elevation.

VMS-BR-005  no zone violation while the pass is approved and in zone.
VMS-BR-009  a safe-listed visitor has NO implicit zone access.
VMS-BR-010  a successful visibility check auto-closes open violations.
VMS-BR-015  safe-list status needs explicit access; the pass QR is the
            primary exception at the gate, never at the zone.
VMS-BR-031  a VIP pass only ever reaches a designated VIP zone.
VMS-BR-041  access to a zone not on the pass is denied.
VMS-BR-042  expanded access requires a time-boxed elevation; the pass's
            designated zones are never rewritten.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from modules.vms.models import Pass, Visit, VisitLog, Visitor, Zone, ZoneElevation
from modules.vms.services import blacklist as blacklist_service
from modules.vms.services import policies, roles
from modules.vms.services.alerts import close_alerts_on_entry, open_alert
from modules.vms.services.errors import (
    NotFoundError,
    ZoneAccessDeniedError,
)
from modules.vms.services.passes import expire_if_due, find_pass, pass_is_live
from modules.vms.services.violations import close_on_visibility, raise_violation


def active_elevation(visit_id: int, zone_code: str, *,
                     at=None) -> ZoneElevation | None:
    at = at or timezone.now()
    return (ZoneElevation.objects
            .filter(visit_id=visit_id, zone_code=zone_code, is_active=True,
                    starts_at__lte=at, expires_at__gte=at)
            .first())


def validate_zone_access(*, pass_code: str, zone_code: str,
                         machine_id: str = "", actor=None,
                         gate_code: str = "") -> dict:
    """The single decision point for 'may this pass enter this zone?'."""
    if machine_id:
        policies.require_nominal_machine(policies.effective(),
                                         machine_id)          # BR-029

    pass_obj = find_pass(pass_code)
    if pass_obj is None:
        raise NotFoundError("Pass not found.", code="pass_not_found")
    visitor = Visitor.objects.get(pk=pass_obj.visitor_id)
    visit = Visit.objects.get(pk=pass_obj.visit_id)

    pass_obj = expire_if_due(pass_obj)
    if not pass_is_live(pass_obj):
        raise_violation(kind="EXPIRED_PASS", visit_id=visit.id,
                        visitor_id=visitor.id, pass_id=pass_obj.id,
                        zone_code=zone_code)                  # BR-003
        raise ZoneAccessDeniedError("This pass has expired.",
                                    code="pass_expired")

    zone = Zone.objects.filter(code=zone_code).first()
    if zone is None:
        raise NotFoundError("Zone not found.", code="zone_not_found")

    policy = policies.effective()
    designated = zone_code in set(pass_obj.permitted_zones)
    elevated = active_elevation(visit.id, zone_code) is not None
    restricted = zone_code in policies.restricted_zone_codes(policy)
    vip_ok = pass_obj.pass_type != "VIP" or zone.is_vip_designated

    # Safe-list status never widens a zone (BR-009 / BR-015): `allowed`
    # starts from the pass's designated zones only.
    allowed = designated and not restricted and vip_ok
    if not allowed and elevated and not restricted:
        allowed = True                                        # BR-042 path

    actor_id = getattr(actor, "user_id", None)
    if allowed:
        VisitLog.objects.create(
            visit_id=visit.id, visitor_id=visitor.id,
            event_type="ZONE_ACCESS_ALLOWED", pass_id=pass_obj.id,
            zone_code=zone_code, gate_code=gate_code,
            machine_id=machine_id, occurred_at=timezone.now(),
            recorded_by_user_id=actor_id,
            details={"designated": designated, "elevated": elevated})
        close_on_visibility(visit.id, actor_user_id=actor_id)  # BR-010
        close_alerts_on_entry(visitor.id, visit_id=visit.id,   # BR-028
                              actor_user_id=actor_id)
        return {"allowed": True, "zone_code": zone_code,
                "via": "elevation" if elevated else "pass",
                "visit_id": visit.id}

    reason = "restricted" if restricted else (
        "vip_zone_only" if not vip_ok else "not_on_pass")
    VisitLog.objects.create(
        visit_id=visit.id, visitor_id=visitor.id,
        event_type="ZONE_ACCESS_DENIED", pass_id=pass_obj.id,
        zone_code=zone_code, gate_code=gate_code, machine_id=machine_id,
        occurred_at=timezone.now(), recorded_by_user_id=actor_id,
        details={"reason": reason})
    raise_violation(                                            # BR-003
        kind="UNAUTHORIZED_ZONE", visit_id=visit.id,
        visitor_id=visitor.id, pass_id=pass_obj.id, zone_code=zone_code,
        details={"reason": reason})
    open_alert(alert_type="ZONE_VIOLATION", severity="MEDIUM",
               message=f"Unauthorized zone access to {zone_code}",
               visitor_id=visitor.id, visit_id=visit.id,
               pass_id=pass_obj.id, zone_code=zone_code)        # dedupe
    raise ZoneAccessDeniedError(
        f"This pass does not permit zone {zone_code}.",
        details=[{"reason": reason,
                  "designated_zones": list(pass_obj.permitted_zones)}])


def grant_elevation(*, visit_id: int, zone_code: str, actor,
                    hours: int = 2, reason: str = "") -> ZoneElevation:
    """Admin grants time-boxed access beyond the pass (VMS-UC-024)."""
    roles.require_admin(actor)
    visit = Visit.objects.filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.", code="visit_not_found")
    if not Zone.objects.filter(code=zone_code).exists():
        raise NotFoundError("Zone not found.", code="zone_not_found")
    now = timezone.now()
    return ZoneElevation.objects.create(
        visit_id=visit.id, zone_code=zone_code,
        granted_by_user_id=getattr(actor, "user_id", None),
        reason=reason, starts_at=now, expires_at=now + timedelta(hours=hours))


def safe_list_has_no_zones(visitor: Visitor) -> bool:
    """VMS-BR-009: being safe-listed grants no zone by itself."""
    return blacklist_service.is_safe_listed(visitor)
