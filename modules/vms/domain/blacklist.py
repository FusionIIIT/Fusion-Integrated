"""Pure python blacklist and watchlist matching rules.

ZERO framework imports allowed here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BlacklistMatchCandidate:
    id_document_type: str
    id_document_number: str
    name: str
    phone: str
    status: str
    safe_list_until: datetime | None = None


def normalize_string(s: str | None) -> str:
    """Normalize string for robust, case-insensitive comparison."""
    if not s:
        return ""
    return "".join(s.strip().upper().split())


def is_blacklisted(
    name: str,
    id_document_number: str,
    phone: str,
    entries: Sequence[BlacklistMatchCandidate],
    now: datetime,
) -> tuple[bool, str]:
    """Check if person matches an active, non-safe-listed blacklist entry.

    Returns (is_blocked, match_reason).
    """
    norm_name = normalize_string(name)
    norm_doc = normalize_string(id_document_number)
    norm_phone = normalize_string(phone)

    for entry in entries:
        if entry.status == "INACTIVE":
            continue

        # Check if safe-listed
        if entry.status == "SAFE_LISTED" and entry.safe_list_until and entry.safe_list_until > now:
            continue

        # Document number match (strongest signal)
        entry_doc = normalize_string(entry.id_document_number)
        if norm_doc and entry_doc and norm_doc == entry_doc:
            return True, f"ID document match: {entry.id_document_number}"

        # Phone match
        entry_phone = normalize_string(entry.phone)
        if norm_phone and entry_phone and norm_phone == entry_phone:
            return True, f"Phone number match: {entry.phone}"

        # Exact normalized name match
        entry_name = normalize_string(entry.name)
        if norm_name and entry_name and norm_name == entry_name:
            return True, f"Name match: {entry.name}"

    return False, ""
