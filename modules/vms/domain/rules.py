"""VMS Pure Business Rules.
Encapsulates BR-001, BR-004, BR-017, BR-020, BR-032, BR-041, BR-045.
No database, no framework.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from modules.vms.domain.models import (
    BlacklistMatchResult,
    PassAllowanceResult,
    ZoneAccessResult,
)


def validate_blacklist_match(
    visitor_id_hash: str,
    visitor_phone: str,
    visitor_name: str,
    blacklist_entries: list[dict],
) -> BlacklistMatchResult:
    """Enforce BR-001 and BR-004: Exact match on ID hash or Quorum Match on Phone + Name."""
    cleaned_phone = "".join(filter(str.isdigit, visitor_phone))
    cleaned_name = visitor_name.strip().lower()

    for entry in blacklist_entries:
        if not entry.get("is_active", True):
            continue

        # 1. Exact ID hash match (BR-001)
        entry_id_hash = entry.get("id_number_hash")
        if entry_id_hash and entry_id_hash == visitor_id_hash:
            reason_str = entry.get("reason", "Security Alert")
            msg = f"Identity matches active blacklist record: {reason_str}"
            return BlacklistMatchResult(
                is_blacklisted=True,
                reason=msg,
                severity=entry.get("severity", "critical"),
                matched_rule="BR-001",
            )

        # 2. Quorum / Combined match on Phone and Name (BR-004)
        entry_phone = "".join(filter(str.isdigit, entry.get("phone", "")))
        entry_name = entry.get("full_name", "").strip().lower()

        name_match = (
            cleaned_name
            and entry_name
            and (cleaned_name in entry_name or entry_name in cleaned_name)
        )
        if cleaned_phone and entry_phone and cleaned_phone == entry_phone and name_match:
            msg = f"Phone and name match blacklist record: {entry.get('reason', 'Watchlist match')}"
            return BlacklistMatchResult(
                is_blacklisted=True,
                reason=msg,
                severity=entry.get("severity", "warning"),
                matched_rule="BR-004",
            )

    return BlacklistMatchResult(is_blacklisted=False)


def validate_same_day_pass(
    requested_date_str: str,
    existing_active_pass_dates: list[str],
) -> PassAllowanceResult:
    """Enforce BR-017 & BR-020: Visitor cannot hold multiple active passes on the same day."""
    if requested_date_str in existing_active_pass_dates:
        return PassAllowanceResult(
            allowed=False,
            reason=f"Visitor already holds an active pass for date {requested_date_str}.",
            rule_id="BR-020",
        )
    return PassAllowanceResult(allowed=True)


def calculate_walk_in_duration(check_in_time: datetime) -> tuple[datetime, datetime]:
    """Enforce BR-032: Walk-in visitor pass default duration is strictly 4 hours."""
    valid_from = check_in_time
    valid_to = check_in_time + timedelta(hours=4)
    return valid_from, valid_to


def validate_zone_access(
    allowed_zones: list[str] | tuple[str, ...],
    requested_zone: str,
) -> ZoneAccessResult:
    """Enforce BR-041: Visitor is only authorized for zones explicitly assigned to their pass."""
    norm_allowed = {z.strip().upper() for z in allowed_zones}
    norm_requested = requested_zone.strip().upper()

    if norm_requested not in norm_allowed:
        zones_str = ", ".join(sorted(norm_allowed))
        return ZoneAccessResult(
            allowed=False,
            zone_code=requested_zone,
            reason=f"Zone '{requested_zone}' is not in approved pass zones: [{zones_str}].",
            rule_id="BR-041",
        )
    return ZoneAccessResult(allowed=True, zone_code=requested_zone)


def check_overstay(valid_to: datetime, current_time: datetime) -> bool:
    """Enforce BR-045: Check whether visitor has exceeded approved pass validity."""
    return current_time > valid_to
