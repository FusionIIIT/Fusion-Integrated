"""Access-policy resolution: durations, windows, the nominal machine.

The PUBLISHED policy is the only one runtime code may read; a draft or a
retired version is invisible to validation. With no published policy the
baseline defaults from the frozen statement apply, so the system is never
unconfigured.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from modules.vms.models import AccessPolicy
from modules.vms.services.errors import MachineNotNominalError

#: Built-in fallbacks — the same numbers the published baseline states.
DEFAULTS = {
    "max_visit_duration_hours": 8,
    "walk_in_pass_duration_hours": 4,      # VMS-BR-032
    "registered_pass_duration_hours": 4,   # VMS-BR-033
    "default_pass_duration_hours": 8,      # VMS-BR-034
    "approval_timeout_hours": 24,
    "approval_reminder_hours": 6,
    "advance_registration_hours": 2,
    "nominal_machine_id": "GATE-NOMINAL",  # VMS-BR-029
    "muster_eviction_grace_minutes": 15,   # VMS-BR-045
}


def active_policy() -> AccessPolicy | None:
    """The published policy runtime validation consumes. Never a draft."""
    return (AccessPolicy.objects
            .filter(status="PUBLISHED")
            .order_by("-is_default", "-version", "-published_at")
            .first())


def _fallback() -> AccessPolicy:
    """An unsaved policy carrying the baseline defaults."""
    return AccessPolicy(name="baseline", status="PUBLISHED", **DEFAULTS)


def effective() -> AccessPolicy:
    return active_policy() or _fallback()


def pass_duration_hours(policy: AccessPolicy, pass_type: str) -> int | None:
    """Hours a fresh pass of this type lasts (VMS-BR-032/033/034).

    VMS-BR-016: a zero-clock duration means real-time recording, which is
    expressed as None — the pass has no end until checkout.
    """
    if pass_type == "WALK_IN":
        hours = policy.walk_in_pass_duration_hours
    elif pass_type == "PRE_REGISTERED":
        hours = policy.registered_pass_duration_hours
    elif pass_type == "VIP":
        hours = policy.default_pass_duration_hours
    else:
        hours = policy.default_pass_duration_hours
    return None if hours == 0 else hours


def valid_until(valid_from: datetime, hours: int | None) -> datetime | None:
    if hours is None:
        return None                      # VMS-BR-016 real-time
    return valid_from + timedelta(hours=hours)


def require_nominal_machine(policy: AccessPolicy, machine_id: str) -> str:
    """VMS-BR-029: a badge read for guest operations must name the nominal
    machine id. Anything else is refused before the pass is touched."""
    if not machine_id or machine_id != policy.nominal_machine_id:
        raise MachineNotNominalError(
            f"Machine id {machine_id!r} is not the nominal gate machine.")
    return machine_id


def approval_deadline(now: datetime | None = None) -> datetime:
    policy = effective()
    now = now or timezone.now()
    return now + timedelta(hours=policy.approval_timeout_hours)


def reminder_at(submitted_at: datetime) -> datetime:
    policy = effective()
    return submitted_at + timedelta(
        hours=max(policy.approval_timeout_hours - policy.approval_reminder_hours,
                  0))


def is_within_visiting_hours(policy: AccessPolicy, at: datetime) -> bool:
    local = timezone.localtime(at)
    return policy.visiting_hours_start <= local.time() <= policy.visiting_hours_end


def restricted_zone_codes(policy: AccessPolicy) -> set[str]:
    return set(policy.restricted_zones or [])
