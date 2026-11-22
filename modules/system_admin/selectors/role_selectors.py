"""Read selectors for RoleAssignment records and directory."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from modules.system_admin.domain.rules import FACULTY_STAFF_ONLY_ROLES, STUDENT_ONLY_ROLES
from modules.system_admin.models.role_assignment import RoleAssignment

# Standard singular roles defined in institutional governance
KNOWN_SINGULAR_ROLES = [
    ("director", "Director"),
    ("dean_academics", "Dean Academics"),
    ("dean_students", "Dean Students"),
    ("dean_rnd", "Dean R&D"),
    ("hod_cse", "Head of Department (CSE)"),
    ("hod_ece", "Head of Department (ECE)"),
    ("hod_me", "Head of Department (ME)"),
    ("registrar", "Registrar"),
    ("tpo", "Training and Placement Officer"),
    ("finance_officer", "Finance Officer"),
    ("internal_auditor", "Internal Auditor"),
]


def get_role_assignment(assignment_id: int) -> RoleAssignment | None:
    """Retrieve role assignment by primary key id."""
    return RoleAssignment.objects.filter(id=assignment_id).first()


def list_role_assignments(
    *,
    user_id: int | None = None,
    role_code: str | None = None,
    status: str | None = None,
) -> list[RoleAssignment]:
    """List role assignments with optional filtering (AFR-SA-021)."""
    qs = RoleAssignment.objects.all()
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if role_code:
        qs = qs.filter(role_code=role_code.strip().lower())
    if status:
        qs = qs.filter(status=status.strip().lower())
    return list(qs)


def get_role_directory() -> list[dict[str, Any]]:
    """Return institutional role directory with current holders and occupancy (AFR-SA-067)."""
    active_assignments = RoleAssignment.objects.filter(status="active")
    holders_by_role: dict[str, list[dict[str, Any]]] = {}
    for ra in active_assignments:
        holders_by_role.setdefault(ra.role_code, []).append({
            "assignment_id": ra.id,
            "user_id": ra.user_id,
            "start_date": str(ra.start_date),
            "end_date": str(ra.end_date) if ra.end_date else None,
            "scope": ra.scope,
        })

    directory: list[dict[str, Any]] = []
    # Include singular roles
    for code, name in KNOWN_SINGULAR_ROLES:
        holders = holders_by_role.get(code, [])
        directory.append({
            "role_code": code,
            "role_name": name,
            "is_singular": True,
            "category": "faculty_staff" if code in FACULTY_STAFF_ONLY_ROLES else "general",
            "active_holders_count": len(holders),
            "is_vacant": len(holders) == 0,
            "holders": holders,
        })

    # Include additional multi-holder roles
    for code in sorted(STUDENT_ONLY_ROLES):
        holders = holders_by_role.get(code, [])
        directory.append({
            "role_code": code,
            "role_name": code.replace("_", " ").title(),
            "is_singular": False,
            "category": "student",
            "active_holders_count": len(holders),
            "is_vacant": len(holders) == 0,
            "holders": holders,
        })

    return directory


def get_approaching_role_expiries(within_days: int = 30) -> list[RoleAssignment]:
    """Find active roles expiring within the specified window (AFR-SA-069)."""
    today = date.today()
    cutoff = today + timedelta(days=within_days)
    return list(
        RoleAssignment.objects.filter(
            status="active",
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=cutoff,
        )
    )
