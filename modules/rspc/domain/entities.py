"""RSPC domain entities, enums, and configurable policy constants.
Pure Python — no Django or DRF imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

# ---------------------------------------------------------------------------
# Configurable Policy Defaults (BR-RSPC-070, BR-RSPC-004, 005, 006, 032, 033, 036, 068, 069)
# ---------------------------------------------------------------------------
DEFAULT_DIRECTOR_FUNDING_THRESHOLD = Decimal(
    "5000000.00"
)  # 50 Lakhs (large funding proposal/request)
DEFAULT_DEAN_FINANCIAL_LIMIT = Decimal("500000.00")  # 5 Lakhs (Dean delegated financial power)
DEFAULT_DEAN_PROCUREMENT_LIMIT = Decimal("1000000.00")  # 10 Lakhs (Dean procurement limit)
DEFAULT_DIRECTOR_EXPENDITURE_THRESHOLD = Decimal("500000.00")  # 5 Lakhs (high-value expenditure)


# ---------------------------------------------------------------------------
# RSPC Roles (PS 2.1 - 2.5, BR-RSPC-048, BR-RSPC-049)
# ---------------------------------------------------------------------------
class RspcRole(StrEnum):
    FACULTY = "faculty"
    HOD = "hod"
    RSPC_ADMIN = "rspc_admin"
    DEAN_RSPC = "dean_rspc"
    DIRECTOR = "director"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Proposal Statuses (CW-RSPC-01, BW-RSPC-01, BW-RSPC-02)
# ---------------------------------------------------------------------------
class ProposalStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DEPT_RECOMMENDED = "dept_recommended"
    DEPT_NOT_RECOMMENDED = "dept_not_recommended"
    ADMIN_VERIFIED = "admin_verified"
    NOT_ELIGIBLE = "not_eligible"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    APPROVED = "approved"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Consultancy Statuses (CW-RSPC-02, BW-RSPC-03, BW-RSPC-04)
# ---------------------------------------------------------------------------
class ConsultancyStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DEPT_RECOMMENDED = "dept_recommended"
    DEPT_NOT_RECOMMENDED = "dept_not_recommended"
    ADMIN_VERIFIED = "admin_verified"
    NOT_ELIGIBLE = "not_eligible"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    APPROVED = "approved"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Project-Based Staff Appointment Statuses (CW-RSPC-03, BW-RSPC-05, BW-RSPC-06)
# ---------------------------------------------------------------------------
class StaffAppointmentStatus(StrEnum):
    DRAFT = "draft"
    REQUESTED = "requested"
    ADMIN_VERIFIED = "admin_verified"
    NOT_ELIGIBLE = "not_eligible"
    SELECTION_RECOMMENDED = "selection_recommended"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    APPROVED = "approved"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Financial & Fund Request Statuses (CW-RSPC-04, BW-RSPC-07, BW-RSPC-08)
# ---------------------------------------------------------------------------
class FinancialRequestStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    NOT_ELIGIBLE = "not_eligible"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    APPROVED = "approved"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Procurement Request Statuses (CW-RSPC-05, BW-RSPC-09, BW-RSPC-10)
# ---------------------------------------------------------------------------
class ProcurementStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    NOT_ELIGIBLE = "not_eligible"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    APPROVED = "approved"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Project Closure Statuses (CW-RSPC-06, BW-RSPC-11, BW-RSPC-12)
# ---------------------------------------------------------------------------
class ClosureStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    NOT_ELIGIBLE = "not_eligible"
    FORWARDED_TO_DIRECTOR = "forwarded_to_director"
    ARCHIVED = "archived"
    DEAN_NOT_APPROVED = "dean_not_approved"
    DIRECTOR_NOT_APPROVED = "director_not_approved"


# ---------------------------------------------------------------------------
# Active Project Lifecycle Statuses
# ---------------------------------------------------------------------------
class ProjectLifecycleStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Transition Descriptor
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkflowTransition:
    frm: str
    to: str
    actor_roles: frozenset[str]
    permission: str
    guards: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
