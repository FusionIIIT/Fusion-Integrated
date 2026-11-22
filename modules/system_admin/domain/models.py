"""Domain value objects and dataclasses for System Admin."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class UserIdentity:
    institute_id: str
    username: str
    email: str
    user_type: str
    name: str = ""
    contact_number: str = ""
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None
    joining_date: date | None = None


@dataclass(frozen=True)
class RoleAssignmentSpec:
    role_code: str
    user_id: int
    start_date: date
    reason: str
    end_date: date | None = None
    scope: str = ""
    is_singular: bool = False


@dataclass(frozen=True)
class ArchivalSpec:
    user_id: int
    reason: str
    retention_option: str
    archival_date: date
    reversible_window_days: int = 90


@dataclass(frozen=True)
class PurgeRequestSpec:
    dataset_identifier: str
    requested_by_id: int
    retention_period_years: int
    archived_at: datetime


@dataclass(frozen=True)
class SystemConfigSpec:
    session_timeout_minutes: int
    password_rotation_days: int
    archival_retention_years: int
    bulk_operation_limit: int = 1000
