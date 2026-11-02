"""Pure Python frozen dataclasses and value objects for modules.system_admin.

Free of external dependencies (strictly NO Django, DRF, or Celery).
Traceability: CFR-SA-001..016, BR-SA-001..035, CW-SA-01..03.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Tuple


@dataclass(frozen=True)
class UserCreationSpec:
    """Specification for creating a new institutional user (BR-SA-001..003)."""
    user_kind: str                       # 'student' | 'faculty' | 'staff'
    name: str
    institute_email: str
    institute_id: str                    # Immutable unique ID (Roll No or PF No)
    contact_number: str
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: Optional[int] = None
    employee_id: str = ""
    date_of_joining: Optional[date] = None
    expected_completion_date: Optional[date] = None


@dataclass(frozen=True)
class RoleAssignmentSpec:
    """Specification for assigning an institutional or functional role (BR-SA-006..010)."""
    role_code: str
    target_user_id: int
    target_user_kind: str
    start_date: date
    end_date: Optional[date] = None
    scope: str = "institute"
    reason: str = ""
    is_singular: bool = False
    is_time_bound: bool = False
    allowed_kinds: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoleReassignmentSpec:
    """Specification for reassigning a singular or functional role (BR-SA-011..013)."""
    role_assignment_id: int
    role_code: str
    previous_holder_id: int
    new_holder_id: int
    new_holder_kind: str
    effective_date: date
    handover_tasks: bool = True
    audit_access_days: int = 90
    reason: str = ""


@dataclass(frozen=True)
class RoleRevocationSpec:
    """Specification for standard or emergency role revocation (BR-SA-014..015)."""
    role_assignment_id: int
    is_emergency: bool
    notice_date: date
    effective_date: date
    reason: str
    pending_tasks_disposition: str       # 'transfer' | 'close'
    new_task_holder_id: Optional[int] = None


@dataclass(frozen=True)
class ArchivalEligibilityVerdict:
    """Result of user archival eligibility assessment (BR-SA-004)."""
    is_eligible: bool
    reason: str = ""
    has_pending_transactions: bool = False
    deactivation_days_elapsed: int = 0
    required_deactivation_days: int = 30


@dataclass(frozen=True)
class PurgeRequestSpec:
    """Specification for requesting a permanent historical data purge (BR-SA-021..023)."""
    dataset_category: str
    date_range_start: date
    date_range_end: date
    super_admin_id: int
    super_admin_username: str
    reason: str
    retention_period_years: int
