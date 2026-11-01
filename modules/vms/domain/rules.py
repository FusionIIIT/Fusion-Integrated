"""Business rules and validations for VMS (BW-VMS-01).

Guards:
- VMS-BR-037: Mandatory pre-registration attributes.
- VMS-BR-051 / VMS-BR-112: Disqualifying blacklist checks.
- VMS-BR-052: Host authorization constraints.
- VMS-BR-077 / VMS-BR-190: Gate validity and time-bound credential checks.
- VMS-BR-105: Checkout session completion.
"""
from datetime import datetime
from typing import List, Optional
from .errors import (
    BlacklistedVisitorError,
    InvalidTimeWindowError,
    PassNotActiveError,
    GateAccessDeniedError,
    InvalidStateTransitionError,
)


def validate_time_window(start: datetime, end: datetime, max_hours: int = 12) -> None:
    if end <= start:
        raise InvalidTimeWindowError("Scheduled end time must be strictly after start time.")
    duration_hours = (end - start).total_seconds() / 3600.0
    if duration_hours > max_hours:
        raise InvalidTimeWindowError(f"Visit duration cannot exceed maximum allowed limit of {max_hours} hours.")


def check_blacklist_guard(is_blacklisted: bool, reason: str = "") -> None:
    if is_blacklisted:
        raise BlacklistedVisitorError(f"Visitor is blacklisted: {reason or 'Security flag active'}")


def validate_pass_gate_access(
    pass_status: str,
    valid_from: datetime,
    valid_until: datetime,
    permitted_zones: List[str],
    gate_zone: str,
    now: datetime,
) -> None:
    if pass_status != "ACTIVE":
        raise PassNotActiveError(f"Visitor pass status is '{pass_status}', expected 'ACTIVE'.")
    if now < valid_from or now > valid_until:
        raise PassNotActiveError("Current timestamp is outside the approved pass validity window.")
    if permitted_zones and gate_zone not in permitted_zones:
        raise GateAccessDeniedError(f"Gate zone '{gate_zone}' is not in permitted zones: {permitted_zones}.")


def validate_checkout_transition(current_status: str) -> None:
    if current_status != "ON_SITE":
        raise InvalidStateTransitionError(f"Cannot checkout visit with status '{current_status}'. Must be 'ON_SITE'.")
