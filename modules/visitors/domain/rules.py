"""VMS policy and validation rules. Pure Python — no Django in here.

Ref: 04_VMS_Business_Rule_Specifications_v1.3

    BR-VMS-037       mandatory pre-registration validation
    BR-VMS-038       duplicate visit request check
    BR-VMS-051       blacklist registration rejection
    BR-VMS-052       host approval requirement
    BR-VMS-053       walk-in pass duration
    BR-VMS-062       pending approval timeout
    BR-VMS-073       early pass/visit termination authorization
    BR-VMS-077       active pass gate rule
    BR-VMS-082       gate validation failure rule
    BR-VMS-096       temporary zone elevation time box
    BR-VMS-101       automatic checkout trigger
    BR-VMS-105       visit completion rule
    BR-VMS-186       valid identity document requirement
    BR-VMS-190       pass validity window
    BR-VMS-193       maximum visit duration
    BR-VMS-195       pre-authorization approval bypass
    BR-VMS-196       VIP override authorization
    BR-VMS-202       advance pre-registration window
    BR-VMS-203       same-day urgent visit exception
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta


class RuleViolation(Exception):
    def __init__(self, message: str, rule: str = ""):
        super().__init__(message)
        self.message = message
        self.rule = rule


# --- defaults (overridden by the published AccessPolicy at runtime) ----------

DEFAULT_VISITING_HOURS = (time(8, 0), time(18, 0))
DEFAULT_MAX_VISIT_HOURS = 8
DEFAULT_WALKIN_MINUTES = 120
DEFAULT_ADVANCE_DAYS = 30
DEFAULT_APPROVAL_TIMEOUT_HOURS = 48

REQUIRED_VISITOR_FIELDS = [
    "visitor_name", "visitor_phone", "visitor_id_type",
    "visitor_id_number", "host_user_id", "purpose", "expected_date",
]

VALID_ID_TYPES = {"AADHAAR", "PAN", "PASSPORT", "DRIVING", "VOTER", "INSTITUTE"}


def validate_pre_registration(data: dict) -> None:
    """BR-VMS-037: all mandatory fields must be present."""
    missing = [f for f in REQUIRED_VISITOR_FIELDS if not data.get(f)]
    if missing:
        raise RuleViolation(
            f"Missing required fields: {', '.join(missing)}",
            rule="BR-VMS-037",
        )


def validate_id_document(id_type: str, id_number: str) -> None:
    """BR-VMS-186, BR-VMS-187: valid identity document required."""
    if id_type not in VALID_ID_TYPES:
        raise RuleViolation(
            f"Unsupported identity document type: {id_type}",
            rule="BR-VMS-187",
        )
    if not id_number or len(id_number.strip()) < 4:
        raise RuleViolation(
            "Identity document number is required and must be at least 4 characters.",
            rule="BR-VMS-186",
        )


def check_advance_window(expected_date: date, today: date,
                         max_advance_days: int = DEFAULT_ADVANCE_DAYS) -> None:
    """BR-VMS-202: pre-registration must be within the advance window."""
    if expected_date < today:
        raise RuleViolation(
            "Visit date cannot be in the past.", rule="BR-VMS-202")
    delta = (expected_date - today).days
    if delta > max_advance_days:
        raise RuleViolation(
            f"Pre-registration must be within {max_advance_days} days "
            f"(requested {delta} days ahead).",
            rule="BR-VMS-202",
        )


def check_visiting_hours(visit_time: time | None,
                         hours_start: time = DEFAULT_VISITING_HOURS[0],
                         hours_end: time = DEFAULT_VISITING_HOURS[1]) -> None:
    """BR-VMS-127: visit must fall within configured visiting hours."""
    if visit_time is None:
        return
    if visit_time < hours_start or visit_time > hours_end:
        raise RuleViolation(
            f"Visiting hours are {hours_start} to {hours_end}.",
            rule="BR-VMS-127",
        )


def check_max_duration(expected_from: time | None, expected_until: time | None,
                       max_hours: int = DEFAULT_MAX_VISIT_HOURS) -> None:
    """BR-VMS-193: visit duration must not exceed the configured maximum."""
    if expected_from is None or expected_until is None:
        return
    dt_from = datetime.combine(date.today(), expected_from)
    dt_until = datetime.combine(date.today(), expected_until)
    if dt_until <= dt_from:
        raise RuleViolation("End time must be after start time.", rule="BR-VMS-193")
    hours = (dt_until - dt_from).total_seconds() / 3600
    if hours > max_hours:
        raise RuleViolation(
            f"Visit duration ({hours:.1f}h) exceeds the maximum "
            f"of {max_hours}h.",
            rule="BR-VMS-193",
        )


def is_blacklisted(id_number: str, blacklist_numbers: set[str]) -> bool:
    """BR-VMS-051, BR-VMS-112: check against published blacklist."""
    return id_number.strip().upper() in blacklist_numbers


def check_not_blacklisted(id_number: str, blacklist_numbers: set[str]) -> None:
    """BR-VMS-051: blacklisted visitors cannot register."""
    if is_blacklisted(id_number, blacklist_numbers):
        raise RuleViolation(
            "Visitor is on the blacklist and cannot be registered.",
            rule="BR-VMS-051",
        )


def is_approval_timed_out(requested_at: datetime, now: datetime,
                          timeout_hours: int = DEFAULT_APPROVAL_TIMEOUT_HOURS
                          ) -> bool:
    """BR-VMS-062: pending approval timeout."""
    return (now - requested_at).total_seconds() > timeout_hours * 3600


def pass_is_valid(valid_from: datetime | None, valid_until: datetime | None,
                  now: datetime) -> bool:
    """BR-VMS-077, BR-VMS-190: pass must be within its validity window."""
    if valid_from is None or valid_until is None:
        return False
    return valid_from <= now <= valid_until


def walkin_pass_expiry(issued_at: datetime,
                       duration_minutes: int = DEFAULT_WALKIN_MINUTES
                       ) -> datetime:
    """BR-VMS-053: walk-in pass duration."""
    return issued_at + timedelta(minutes=duration_minutes)


def can_terminate(status: str, actor_role: str) -> bool:
    """BR-VMS-073: who may terminate a visit early."""
    terminable = {"approved", "pass_active", "on_site"}
    if status not in terminable:
        return False
    return actor_role in ("host", "admin", "super_admin")


def zone_elevation_valid(valid_until: datetime, now: datetime) -> bool:
    """BR-VMS-096: temporary zone elevation time box."""
    return now <= valid_until


def should_auto_checkout(pass_valid_until: datetime | None,
                         now: datetime) -> bool:
    """BR-VMS-101: automatic checkout trigger when pass expires."""
    if pass_valid_until is None:
        return False
    return now > pass_valid_until
