"""Zone validation and temporary zone elevation services."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.vms.models import GateCheckLog, Pass, ZoneElevation


@transaction.atomic
def validate_zone_access(
    pass_id: int,
    zone_name: str,
    operator_id: int | None = None,
) -> tuple[bool, str]:
    """Validate visitor permission to enter a specific zone (UC-023, BR-191, BR-192)."""
    now = timezone.now()
    pass_record = Pass.objects.select_related("visit_request").filter(pk=pass_id).first()
    if not pass_record:
        return False, "Pass not found."

    visit = pass_record.visit_request
    if visit.status != "CHECKED_IN":
        return False, f"Visitor is not on-site (status: {visit.status})."

    # 1. Base access zones on visit request
    allowed_zones = set(visit.access_zones or [])

    # 2. Check active temporary zone elevations (BR-096)
    has_elevation = ZoneElevation.objects.filter(
        pass_record=pass_record,
        zone_name=zone_name,
        valid_from__lte=now,
        valid_to__gte=now,
    ).exists()

    if zone_name in allowed_zones or has_elevation:
        GateCheckLog.objects.create(
            pass_record=pass_record,
            gate_name=f"Zone Gate: {zone_name}",
            checkpoint_type="ZONE_CHECK",
            action="CHECK_IN",
            operator_id=operator_id,
            timestamp=now,
        )
        return True, f"Access granted to zone '{zone_name}'."

    # Denied: Log zone violation alert (BR-192, UC-025)
    GateCheckLog.objects.create(
        pass_record=pass_record,
        gate_name=f"Zone Gate: {zone_name}",
        checkpoint_type="ZONE_CHECK",
        action="DENIED",
        operator_id=operator_id,
        timestamp=now,
    )
    return (
        False,
        f"Zone violation: Pass #{pass_record.pass_number} is not authorized for '{zone_name}'.",
    )


@transaction.atomic
def grant_zone_elevation(
    pass_id: int,
    zone_name: str,
    hours: int,
    admin_id: int,
    reason: str,
) -> ZoneElevation:
    """Admin grants temporary time-boxed zone elevation (UC-024, BR-096)."""
    if hours <= 0 or hours > 12:
        raise ValueError("Elevation hours must be between 1 and 12.")

    now = timezone.now()
    valid_to = now + timezone.timedelta(hours=hours)

    pass_record = Pass.objects.get(pk=pass_id)
    return ZoneElevation.objects.create(
        pass_record=pass_record,
        zone_name=zone_name,
        valid_from=now,
        valid_to=valid_to,
        elevated_by_id=admin_id,
        reason=reason,
    )
