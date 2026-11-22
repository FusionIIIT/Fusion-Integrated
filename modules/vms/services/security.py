"""VMS Security, Blacklist, Alerts, and Emergency Muster Services."""

from __future__ import annotations

import hashlib
import uuid

from django.db import transaction
from django.utils import timezone

from modules.vms.models.access import GateAlert
from modules.vms.models.muster import EmergencyMuster
from modules.vms.models.visitors import BlacklistEntry
from modules.vms.selectors.visits import list_active_onsite_visits


def add_to_blacklist(
    id_type: str,
    id_number: str,
    full_name: str,
    phone: str,
    reason: str,
    severity: str = "critical",
    added_by: int | None = None,
) -> BlacklistEntry:
    id_hash = hashlib.sha256(id_number.strip().upper().encode("utf-8")).hexdigest()
    entry, _ = BlacklistEntry.objects.get_or_create(
        id_number_hash=id_hash,
        defaults={
            "id_type": id_type,
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "reason": reason.strip(),
            "severity": severity,
            "is_active": True,
            "added_by": added_by,
        },
    )
    return entry


def resolve_gate_alert(alert_id: int, resolver_user_id: int) -> GateAlert:
    alert = GateAlert.objects.get(id=alert_id)
    alert.status = "resolved"
    alert.resolved_by = resolver_user_id
    alert.save()
    return alert


@transaction.atomic
def trigger_emergency_muster(admin_user_id: int) -> EmergencyMuster:
    """Enforces BR-045 and Emergency Muster protocol.
    Freezes count of all visitors currently on campus.
    """
    onsite = list_active_onsite_visits()
    total = onsite.count()
    muster_code = f"MUSTER-{timezone.now().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:6].upper()}"

    muster = EmergencyMuster.objects.create(
        muster_code=muster_code,
        status="active",
        triggered_by=admin_user_id,
        headcount_total=total,
        headcount_accounted=0,
    )

    GateAlert.objects.create(
        alert_type="emergency_muster_active",
        severity="critical",
        message=(
            f"Campus Emergency Muster initiated ({muster_code}). "
            f"Total on-site visitors to account for: {total}."
        ),
    )
    return muster


def resolve_emergency_muster(muster_id: int, admin_user_id: int) -> EmergencyMuster:
    muster = EmergencyMuster.objects.get(id=muster_id)
    muster.status = "resolved"
    muster.ended_at = timezone.now()
    muster.save()

    GateAlert.objects.create(
        alert_type="emergency_muster_resolved",
        severity="info",
        message=f"Emergency Muster {muster.muster_code} resolved by Admin {admin_user_id}.",
    )
    return muster
