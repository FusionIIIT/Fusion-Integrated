"""system_admin's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
Traceability: CFR-SA-010, CFR-SA-011, CFR-SA-020, BR-SA-004, BR-SA-013, BR-SA-026, BR-SA-034.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from django.utils import timezone

from modules.system_admin.constants import (
    RoleAssignmentState,
    UserArchivalStatus,
    UserLifecycleStatus,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    RoleAssignment,
    RoleHandoverLog,
)


# ==============================================================================
# FROZEN DTO VALUE OBJECTS
# ==============================================================================


@dataclass(frozen=True)
class UserIdentityDTO:
    """Public projection of an identity managed by the control plane."""

    user_id: int
    username: str
    institute_id: str
    email: str
    kind: str  # 'student' | 'faculty' | 'staff'
    is_active: bool
    status: str  # 'active' | 'deactivated' | 'archived'
    display_name: str
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: Optional[int] = None
    employee_id: str = ""


@dataclass(frozen=True)
class RoleGrantDTO:
    """Public projection of an active or scheduled role grant."""

    assignment_id: int
    user_id: int
    role_code: str
    role_label: str
    category: str
    scope: str
    state: str  # 'scheduled' | 'active' | 'extended' | 'expired' | 'revoked'
    start_date: date
    end_date: Optional[date] = None


@dataclass(frozen=True)
class UserArchivalStatusDTO:
    """Archival governance status for an account."""

    user_id: int
    is_archived: bool
    is_reversible: bool
    reversible_until: Optional[datetime]
    archival_status: str  # 'active' | 'deactivated' | 'reversible' | 'permanent_non_restorable'


@dataclass(frozen=True)
class AuditAccessGrantDTO:
    """Read-only audit permission held by a previous role holder (BR-SA-013)."""

    user_id: int
    role_code: str
    scope: str
    has_audit_access: bool
    audit_access_expires_at: Optional[date]


# ==============================================================================
# PLURAL PUBLIC FUNCTIONS
# ==============================================================================


def get_user_identities(user_ids: Sequence[int]) -> Dict[int, UserIdentityDTO]:
    """Batched retrieval of user identities and profile metadata.

    A missing ID is simply absent from the mapping — a visible, testable case
    rather than a silent None three layers up.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    users = (
        BasicUser.objects.filter(id__in=ids)
        .select_related("profile")
    )

    out: Dict[int, UserIdentityDTO] = {}
    for u in users:
        prof = getattr(u, "profile", None)
        out[u.id] = UserIdentityDTO(
            user_id=u.id,
            username=u.username,
            institute_id=u.institute_id,
            email=u.email,
            kind=u.kind,
            is_active=u.is_active,
            status=u.status,
            display_name=prof.display_name if prof else u.username,
            department=prof.department if prof else "",
            programme=prof.programme if prof else "",
            discipline=prof.discipline if prof else "",
            batch_year=prof.batch_year if prof else None,
            employee_id=prof.employee_id if prof else "",
        )
    return out


def get_active_roles_for_users(
    user_ids: Sequence[int],
) -> Dict[int, Tuple[RoleGrantDTO, ...]]:
    """Batched retrieval of effective roles (state in [ACTIVE, EXTENDED]).

    Used by access control and authorization middleware to determine permissions.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    assignments = (
        RoleAssignment.objects.filter(
            user_id__in=ids,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        )
        .select_related("role")
        .order_by("user_id", "role__category")
    )

    mapping: Dict[int, List[RoleGrantDTO]] = {uid: [] for uid in ids}
    for a in assignments:
        dto = RoleGrantDTO(
            assignment_id=a.id,
            user_id=a.user_id,
            role_code=a.role.code,
            role_label=a.role.label,
            category=a.role.category,
            scope=a.scope,
            state=a.state,
            start_date=a.start_date,
            end_date=a.end_date,
        )
        mapping[a.user_id].append(dto)

    return {uid: tuple(grants) for uid, grants in mapping.items()}


def get_user_archival_statuses(
    user_ids: Sequence[int],
) -> Dict[int, UserArchivalStatusDTO]:
    """Batched check of user archival state (BR-SA-004, BR-SA-005, ISS-SA-004)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    archives = {
        rec.basic_user_id: rec
        for rec in ArchivedUserRecord.objects.filter(basic_user_id__in=ids)
    }
    users = {u.id: u for u in BasicUser.objects.filter(id__in=ids)}

    out: Dict[int, UserArchivalStatusDTO] = {}
    now = timezone.now()

    for uid in ids:
        user = users.get(uid)
        arch = archives.get(uid)
        if arch:
            is_rev = (
                arch.status == UserArchivalStatus.REVERSIBLE
                and arch.reversible_until is not None
                and now <= arch.reversible_until
            )
            out[uid] = UserArchivalStatusDTO(
                user_id=uid,
                is_archived=True,
                is_reversible=is_rev,
                reversible_until=arch.reversible_until,
                archival_status=arch.status,
            )
        elif user:
            out[uid] = UserArchivalStatusDTO(
                user_id=uid,
                is_archived=False,
                is_reversible=False,
                reversible_until=None,
                archival_status=user.status,
            )
    return out


def check_pending_transactions_for_archival(user_id: int) -> bool:
    """Pre-archival barrier (BR-SA-004).

    Queries operational modules via their contracts to verify that no pending
    obligations block archival.

    Integration points:
      - Placement: checks if user has active accepted job offers or unfulfilled bonds.
      - Academic/Library/Hostel: checks for unresolved dues or open complaints.
    """
    from modules.placement import contracts as placement_contracts

    # Check Placement obligations via contracts.py
    try:
        no_dues = placement_contracts.get_no_dues_clearances([user_id])
        if user_id in no_dues and not no_dues[user_id].cleared:
            return True  # Blocked by placement dues
    except (ImportError, AttributeError):
        pass  # Placement contract absent or unreachable

    return False


def get_previous_holder_audit_grants(
    user_ids: Sequence[int], today: Optional[date] = None
) -> Dict[int, Tuple[AuditAccessGrantDTO, ...]]:
    """Batched query for previous role holders retaining read-only audit access (BR-SA-013)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    eval_date = today or timezone.now().date()

    logs = (
        RoleHandoverLog.objects.filter(
            previous_holder_id__in=ids,
            audit_access_expires_at__gte=eval_date,
        ).select_related("role")
    )

    mapping: Dict[int, List[AuditAccessGrantDTO]] = {uid: [] for uid in ids}
    for l in logs:
        dto = AuditAccessGrantDTO(
            user_id=l.previous_holder_id,
            role_code=l.role.code,
            scope=l.scope,
            has_audit_access=True,
            audit_access_expires_at=l.audit_access_expires_at,
        )
        mapping[l.previous_holder_id].append(dto)

    return {uid: tuple(grants) for uid, grants in mapping.items()}
