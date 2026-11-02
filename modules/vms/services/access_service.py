"""Zone access control and elevation service (BR-005, BR-031, BR-041, BR-042)."""
from django.utils import timezone
from modules.vms.models.visits import VisitPass
from modules.vms.models.access import CampusZone, ZoneAccessLog, GateAlert
from modules.vms.services.pass_service import validate_pass_validity
from modules.vms.services.exceptions import UnauthorizedZoneException


def validate_zone_access(
    pass_record: VisitPass,
    zone_code: str,
    gate_machine_id: str = "",
    verifier_user_id: int | None = None,
) -> bool:
    """Evaluates whether visitor's pass permits entry to a designated zone checkpoint.
    
    Enforces BR-005: No violation if zone is within approved allowed_zones.
    Enforces BR-031: VIP passes restricted strictly to designated zones.
    Enforces BR-041 & BR-042: Non-designated zones trigger immediate access denial & alert.
    """
    # Verify pass is currently valid
    validate_pass_validity(pass_record)

    zone = CampusZone.objects.filter(code=zone_code, is_active=True).first()
    if not zone:
        raise UnauthorizedZoneException(f"Unknown or inactive campus zone code '{zone_code}'.")

    # Check whether the pass explicitly contains this zone name or code
    allowed_list = [z.lower() for z in (pass_record.allowed_zones or [])]
    is_allowed = (zone_code.lower() in allowed_list) or (zone.name.lower() in allowed_list) or ("all_campus" in allowed_list)

    # BR-031: VIP restriction logic
    if pass_record.pass_type == "vip" and zone.requires_special_elevation and not is_allowed:
        is_allowed = False

    if is_allowed:
        # BR-005: Clean entry logged without alert
        ZoneAccessLog.objects.create(
            pass_record=pass_record,
            zone=zone,
            action="granted",
            verified_by_user_id=verifier_user_id,
            gate_machine_id=gate_machine_id,
            notes="Authorized zone entry.",
        )
        # Update visit current zone location
        visit = pass_record.visit
        visit.current_zone = zone.name
        visit.save(update_fields=["current_zone", "updated_at"])
        return True
    else:
        # BR-041 & BR-042: Log denial and create security alert
        ZoneAccessLog.objects.create(
            pass_record=pass_record,
            zone=zone,
            action="denied",
            verified_by_user_id=verifier_user_id,
            gate_machine_id=gate_machine_id,
            notes=f"Unauthorized entry attempt to restricted zone {zone.name} (BR-041).",
        )
        GateAlert.objects.create(
            alert_type="unauthorized_zone",
            severity="medium",
            status="open",
            visitor=pass_record.visitor,
            pass_record=pass_record,
            gate_machine_id=gate_machine_id,
            details=f"Pass #{pass_record.pass_number} denied entry to zone '{zone.name}' [{zone_code}].",
        )
        raise UnauthorizedZoneException(
            f"Access denied: Zone '{zone.name}' is outside visitor's designated pass permissions (BR-041).",
            rule_id="BR-041",
        )


def grant_temporary_zone_elevation(
    pass_record: VisitPass,
    zone_code: str,
    granted_by_user_id: int,
    reason: str = "Authorized temporary elevation",
) -> VisitPass:
    """Grants temporary access elevation to an additional zone (BR-042)."""
    zone = CampusZone.objects.filter(code=zone_code, is_active=True).first()
    if not zone:
        raise UnauthorizedZoneException(f"Zone code '{zone_code}' does not exist.")

    current_zones = list(pass_record.allowed_zones or [])
    if zone.code not in current_zones and zone.name not in current_zones:
        current_zones.append(zone.name)
        pass_record.allowed_zones = current_zones
        pass_record.save(update_fields=["allowed_zones", "updated_at"])

    ZoneAccessLog.objects.create(
        pass_record=pass_record,
        zone=zone,
        action="elevated",
        verified_by_user_id=granted_by_user_id,
        notes=f"Temporary zone elevation granted by user #{granted_by_user_id}. Reason: {reason}",
    )
    return pass_record
