"""Role Selectors for System Admin Control Plane."""
from datetime import date, timedelta
from django.db.models import Count, Q
from modules.systemadmin.models.role_mgmt import (
    RoleDefinition,
    RoleConflict,
    RoleAssignment,
    RoleAssignmentHistory,
)


def list_roles():
    """List role definitions annotated with active holder count and availability (UC-SA-012)."""
    roles = RoleDefinition.objects.all().order_by("module_or_dept", "name")
    result = []
    today = date.today()

    for r in roles:
        active_assignments = RoleAssignment.objects.filter(
            role=r,
            status__in=["active", "extended"]
        ).select_related("user")
        active_count = active_assignments.count()

        is_vacant = False
        if r.is_singular and active_count == 0:
            is_vacant = True

        current_holders = [
            {
                "user_id": a.user.id,
                "institute_id": a.user.institute_id,
                "full_name": a.user.full_name,
                "scope": a.scope,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "status": a.status,
            }
            for a in active_assignments
        ]

        result.append({
            "id": r.id,
            "code": r.code,
            "name": r.name,
            "description": r.description,
            "module_or_dept": r.module_or_dept,
            "allowed_user_types": r.allowed_user_types,
            "is_singular": r.is_singular,
            "is_time_bound": r.is_time_bound,
            "default_validity_days": r.default_validity_days,
            "permissions": r.permissions,
            "status": r.status,
            "active_holders_count": active_count,
            "is_vacant": is_vacant,
            "current_holders": current_holders,
        })
    return result


def get_role_detail(role_identifier: int | str):
    """Get complete metadata, current holders, past holders, and conflict rules for a role."""
    qs = RoleDefinition.objects.all()
    if isinstance(role_identifier, int) or (isinstance(role_identifier, str) and role_identifier.isdigit()):
        role = qs.filter(id=int(role_identifier)).first()
    else:
        role = qs.filter(code=str(role_identifier)).first()
    if not role:
        return None

    active_assignments = RoleAssignment.objects.filter(
        role=role,
        status__in=["active", "extended"]
    ).select_related("user")

    past_assignments = RoleAssignment.objects.filter(
        role=role,
        status__in=["expired", "reassigned", "revoked"]
    ).select_related("user").order_by("-updated_at")

    conflicts = RoleConflict.objects.filter(
        Q(role_a=role) | Q(role_b=role)
    ).select_related("role_a", "role_b")

    conflict_list = []
    for c in conflicts:
        other = c.role_b if c.role_a == role else c.role_a
        conflict_list.append({"code": other.code, "name": other.name, "reason": c.reason})

    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "module_or_dept": role.module_or_dept,
        "allowed_user_types": role.allowed_user_types,
        "is_singular": role.is_singular,
        "is_time_bound": role.is_time_bound,
        "default_validity_days": role.default_validity_days,
        "permissions": role.permissions,
        "status": role.status,
        "current_holders": [
            {
                "id": a.id,
                "user_id": a.user.id,
                "institute_id": a.user.institute_id,
                "full_name": a.user.full_name,
                "scope": a.scope,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "status": a.status,
            }
            for a in active_assignments
        ],
        "past_holders": [
            {
                "id": a.id,
                "user_id": a.user.id,
                "institute_id": a.user.institute_id,
                "full_name": a.user.full_name,
                "scope": a.scope,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "status": a.status,
            }
            for a in past_assignments
        ],
        "conflicts": conflict_list,
    }


def list_role_assignments(
    user_id: int | None = None,
    role_code: str | None = None,
    status: str | None = None,
    scope: str | None = None,
):
    qs = RoleAssignment.objects.select_related("role", "user", "reassigned_to_user").all().order_by("-start_date")
    if user_id:
        qs = qs.filter(user_id=user_id)
    if role_code:
        qs = qs.filter(role__code=role_code)
    if status:
        qs = qs.filter(status=status)
    if scope:
        qs = qs.filter(scope__icontains=scope)
    return qs


def get_assignment_history(assignment_id: int):
    return RoleAssignmentHistory.objects.filter(assignment_id=assignment_id).order_by("-timestamp")


def get_upcoming_expiries(within_days: int = 30):
    today = date.today()
    limit = today + timedelta(days=within_days)
    return RoleAssignment.objects.filter(
        status__in=["active", "extended"],
        end_date__gte=today,
        end_date__lte=limit
    ).select_related("role", "user").order_by("end_date")
