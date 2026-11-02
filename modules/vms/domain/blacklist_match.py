"""Blacklist matching (pure Python). Decision D-2, BR-112.

Exact match on normalised id document, phone (digits, last 10) or email (case-insensitive).
Any one field is a hit; a name alone never matches; blank fields never match.
"""
from __future__ import annotations

import re

SEVERITIES = ("low", "medium", "high", "critical")
_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def severity_rank(severity: str) -> int:
    """Higher is worse. Unknown values raise ValueError."""
    try:
        return _RANK[(severity or "").lower()]
    except KeyError:
        raise ValueError(f"unknown severity {severity!r}") from None


def max_severity(severities) -> str | None:
    items = list(severities)
    return max(items, key=severity_rank) if items else None


def norm_id(value) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def norm_phone(value) -> str:
    return re.sub(r"\D", "", value or "")[-10:]


def norm_email(value) -> str:
    return (value or "").strip().lower()


def matched_fields(entry, probe) -> list[str]:
    fields = []
    for name, norm in (("id_doc_number", norm_id), ("phone", norm_phone), ("email", norm_email)):
        a, b = norm(getattr(entry, name, "")), norm(getattr(probe, name, ""))
        if a and a == b:
            fields.append(name)
    return fields


def matches(entry, probe) -> bool:
    return bool(matched_fields(entry, probe))
