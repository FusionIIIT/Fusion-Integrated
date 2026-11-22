"""VMS Domain Dataclasses and Value Objects.
Pure Python representations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class VisitorIdentity:
    first_name: str
    last_name: str
    phone: str
    email: str
    id_type: str
    id_number_hash: str
    organization: str = ""


@dataclass(frozen=True)
class PassScope:
    valid_from: datetime
    valid_to: datetime
    allowed_zones: tuple[str, ...] = field(default_factory=tuple)
    is_multi_entry: bool = False


@dataclass(frozen=True)
class VisitDecision:
    allowed: bool
    reason: str
    rule_id: str = ""


@dataclass(frozen=True)
class BlacklistMatchResult:
    is_blacklisted: bool
    reason: str = ""
    severity: str = ""
    matched_rule: str = ""


@dataclass(frozen=True)
class PassAllowanceResult:
    allowed: bool
    reason: str = ""
    rule_id: str = ""


@dataclass(frozen=True)
class ZoneAccessResult:
    allowed: bool
    zone_code: str
    reason: str = ""
    rule_id: str = ""
