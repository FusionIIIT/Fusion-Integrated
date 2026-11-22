"""Emergency muster and roll-call services."""

from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from modules.vms.models import EmergencyMusterRoster, VisitRequest


@transaction.atomic
def trigger_emergency_muster(
    initiated_by_id: int,
    assembly_point: str = "Central Ground",
) -> str:
    """Trigger emergency muster and snapshot all on-site visitors (UC-026, UC-032, BR-130)."""
    now = timezone.now()
    muster_id = f"MUSTER-{uuid.uuid4().hex[:8].upper()}"

    # Snapshot all currently on-site visitors (CHECKED_IN)
    onsite_visits = VisitRequest.objects.filter(status="CHECKED_IN").select_related(
        "visitor", "digital_pass"
    )

    roster_entries = [
        EmergencyMusterRoster(
            muster_id=muster_id,
            assembly_point=assembly_point,
            initiated_by_id=initiated_by_id,
            initiated_at=now,
            visitor=visit.visitor,
            pass_record=visit.digital_pass,
            check_in_time=visit.actual_check_in or now,
            accountability_status="UNACCOUNTED",
        )
        for visit in onsite_visits
        if hasattr(visit, "digital_pass")
    ]

    EmergencyMusterRoster.objects.bulk_create(roster_entries)
    return muster_id


@transaction.atomic
def record_roll_call(
    roster_id: int,
    accounted_by_id: int,
    status: str = "ACCOUNTED",
    notes: str = "",
) -> EmergencyMusterRoster:
    """Record roll-call verification for a visitor during muster (UC-027)."""
    entry = EmergencyMusterRoster.objects.select_for_update().get(pk=roster_id)
    entry.accountability_status = status
    entry.accounted_at = timezone.now()
    entry.accounted_by_id = accounted_by_id
    if notes:
        entry.notes = notes
    fields = ["accountability_status", "accounted_at", "accounted_by_id", "notes", "updated_at"]
    entry.save(update_fields=fields)
    return entry
