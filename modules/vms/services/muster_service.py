"""Emergency muster and evacuation accountability service (BR-045, VMS-UC-026)."""
from datetime import timedelta

from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.models.muster import EmergencyMuster, MusterRollCall
from modules.vms.models.visits import VisitPass
from modules.vms.services.exceptions import VMSDomainException


def start_emergency_muster(initiated_by_user_id: int, reason: str = "Campus Emergency Evacuation") -> EmergencyMuster:
    """Initiates an emergency muster roll-call and freezes the on-site roster."""
    muster = EmergencyMuster.objects.create(
        initiated_by_user_id=initiated_by_user_id,
        reason=reason,
        status="in_progress",
    )

    # Snapshot all currently on-site visitors
    active_passes = VisitPass.objects.filter(
        status="active",
        visit__status="on_site",
    ).select_related("visitor", "visit")

    count = 0
    for p in active_passes:
        MusterRollCall.objects.create(
            muster=muster,
            visitor=p.visitor,
            pass_record=p,
            status="unaccounted",
            last_known_zone=p.visit.current_zone or "Main Gate",
        )
        count += 1

    muster.total_on_site_at_start = count
    muster.total_unaccounted = count
    muster.save(update_fields=["total_on_site_at_start", "total_unaccounted"])
    return muster


def update_muster_roll_call(
    muster: EmergencyMuster,
    visitor_id: int,
    status: str,  # "safe", "evacuated", "hospitalized"
    checked_by_user_id: int,
    notes: str = "",
) -> MusterRollCall:
    """Updates accountability roll-call status for an individual visitor."""
    entry = MusterRollCall.objects.filter(muster=muster, visitor_id=visitor_id).first()
    if not entry:
        raise VMSDomainException(f"Visitor #{visitor_id} is not present in muster {muster.muster_code} roster.")

    entry.status = status
    entry.checked_by_user_id = checked_by_user_id
    entry.checked_at = timezone.now()
    entry.notes = notes
    entry.save()

    # Recalculate totals
    total_accounted = muster.roll_calls.exclude(status="unaccounted").count()
    total_unaccounted = muster.roll_calls.filter(status="unaccounted").count()
    muster.total_accounted = total_accounted
    muster.total_unaccounted = total_unaccounted
    muster.save(update_fields=["total_accounted", "total_unaccounted"])
    return entry


def audit_muster_overstay_evictions(muster: EmergencyMuster) -> int:
    """Enforces BR-045: Muster roster extra time > 15 minutes triggers eviction alert."""
    now = timezone.now()
    cutoff_time = muster.started_at + timedelta(minutes=15)

    eviction_alerts_created = 0
    if now > cutoff_time:
        unaccounted_entries = muster.roll_calls.filter(status="unaccounted")
        for entry in unaccounted_entries:
            # Check if alert already raised
            exists = GateAlert.objects.filter(
                alert_type="muster_eviction",
                visitor=entry.visitor,
                status="open",
            ).exists()
            if not exists:
                GateAlert.objects.create(
                    alert_type="muster_eviction",
                    severity="critical",
                    status="open",
                    visitor=entry.visitor,
                    pass_record=entry.pass_record,
                    details=(
                        f"CRITICAL: Visitor {entry.visitor.full_name} unaccounted for >15 mins "
                        f"in muster {muster.muster_code}. Immediate security search required (BR-045)."
                    ),
                )
                eviction_alerts_created += 1
    return eviction_alerts_created


def complete_emergency_muster(muster: EmergencyMuster) -> EmergencyMuster:
    """Finalizes muster event and produces a post-event audit summary."""
    now = timezone.now()
    muster.status = "completed"
    muster.completed_at = now

    total = muster.total_on_site_at_start
    accounted = muster.roll_calls.exclude(status="unaccounted").count()
    unaccounted = muster.roll_calls.filter(status="unaccounted").count()
    safe = muster.roll_calls.filter(status="safe").count()
    evacuated = muster.roll_calls.filter(status="evacuated").count()
    hospitalized = muster.roll_calls.filter(status="hospitalized").count()

    muster.total_accounted = accounted
    muster.total_unaccounted = unaccounted
    muster.summary_report = (
        f"Muster {muster.muster_code} concluded at {now.isoformat()}.\n"
        f"Total On-site: {total} | Safe: {safe} | Evacuated: {evacuated} | "
        f"Hospitalized: {hospitalized} | Remaining Unaccounted: {unaccounted}."
    )
    muster.save()
    return muster
