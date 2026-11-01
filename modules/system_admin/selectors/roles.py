"""Role selectors for System Admin module.

Enforces read-only inspection of role metadata, assignments, holder status,
and singularity checks (CFR-SA-005, BR-SA-007, BR-SA-016).
"""
from collections.abc import Sequence
from datetime import date, timedelta
from django.db.models import Q, QuerySet

from modules.system_admin.models import RoleAssignment, RoleDefinition


def list_role_definitions(module: str | None = None) -> QuerySet[RoleDefinition]:
    qs = RoleDefinition.objects.all().order_by("module_association", "name")
    if module:
        qs = qs.filter(module_association__iexact=module)
    return qs


def get_role_definition(code: str) -> RoleDefinition | None:
    return RoleDefinition.objects.filter(code=code).first()


def list_role_assignments(
    *,
    user_id: int | None = None,
    role_code: str | None = None,
    status: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> QuerySet[RoleAssignment]:
    qs = RoleAssignment.objects.select_related("role").order_by("-created_at")

    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    if role_code:
        qs = qs.filter(role__code=role_code)
    if status:
        qs = qs.filter(status=status)
    if scope_type:
        qs = qs.filter(scope_type=scope_type)
    if scope_id is not None:
        qs = qs.filter(scope_id=scope_id)

    return qs


def get_active_role_holders(
    role_code: str,
    scope_type: str = "institute",
    scope_id: str = "",
) -> list[int]:
    """Returns user_ids of currently active holders of the role within given scope."""
    return list(
        RoleAssignment.objects.filter(
            role__code=role_code,
            scope_type=scope_type,
            scope_id=scope_id,
            status="active",
        ).values_list("user_id", flat=True)
    )


def list_vacant_singular_roles(
    scope_type: str = "institute",
    scope_id: str = "",
) -> list[RoleDefinition]:
    """Finds singular roles that currently have NO active holder for the given scope (AFR-SA-067)."""
    singular_roles = RoleDefinition.objects.filter(is_singular=True)
    active_role_ids = RoleAssignment.objects.filter(
        role__is_singular=True,
        scope_type=scope_type,
        scope_id=scope_id,
        status="active",
    ).values_list("role_id", flat=True)

    return [r for r in singular_roles if r.id not in active_role_ids]


def list_roles_approaching_expiry(lead_days: int = 30, today: date | None = None) -> QuerySet[RoleAssignment]:
    """Identifies active time-bound roles within lead_days of expiration (AFR-SA-041, BR-SA-016)."""
    ref_date = today or date.today()
    cutoff_date = ref_date + timedelta(days=lead_days)
    return (
        RoleAssignment.objects.filter(
            status="active",
            end_date__isnull=False,
            end_date__gte=ref_date,
            end_date__lte=cutoff_date,
        )
        .select_related("role")
        .order_by("end_date")
    )


def get_user_active_role_codes(user_id: int) -> list[str]:
    """Returns active assigned role codes for a user (used by role switcher and permissions)."""
    return list(
        RoleAssignment.objects.filter(user_id=user_id, status="active")
        .values_list("role__code", flat=True)
        .distinct()
    )
