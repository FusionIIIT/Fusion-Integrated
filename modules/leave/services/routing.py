"""Resolve per-category approver assignments from the current admin configuration."""
from core.api.exceptions import BadRequestError
from fusion_auth.client import IamUnavailable
from modules.leave.models import LeavePolicyConfig


def resolve_application_route(*, category: str, applicant_id: int, roles: tuple[str, ...], active_role: str | None = None) -> dict:
    normalized_roles = {role.lower() for role in roles}
    if "director" in normalized_roles:
        return {"unit_head_user_id": None, "establishment_user_id": None, "sanctioning_authority_user_id": applicant_id}

    department = ""
    try:
        from modules.directory import contracts as directory
        person = directory.get_users([applicant_id]).get(applicant_id)
        department = getattr(person, "department", "") if person else ""
    except IamUnavailable:
        department = ""
    config = None
    route_roles = [active_role] if active_role else sorted(normalized_roles)
    for role in route_roles:
        if not role:
            continue
        role_key = role.strip().lower().replace(" ", "_")
        if role_key in {"faculty", "staff", "employee"}:
            continue
        if department:
            config = LeavePolicyConfig.objects.filter(key=f"route.{category}.{department}.{role_key}").first()
        config = config or LeavePolicyConfig.objects.filter(key=f"route.{category}.{role_key}").first()
        if config:
            break
    config = config or (LeavePolicyConfig.objects.filter(key=f"route.{category}.{department}").first() if department else None)
    config = config or LeavePolicyConfig.objects.filter(key=f"route.{category}").first()
    route = config.value if config and isinstance(config.value, dict) else {}
    try:
        unit_head = int(route["unit_head_user_id"])
        authority = int(route["sanctioning_authority_user_id"]) if category not in {"CL", "RH"} else None
        establishment = int(route["establishment_user_id"]) if route.get("establishment_user_id") else None
    except (KeyError, TypeError, ValueError):
        raise BadRequestError(f"No valid approver route is configured for {category}.", code="leave_route_not_configured")
    if unit_head < 1 or (authority is not None and authority < 1) or (establishment is not None and establishment < 1):
        raise BadRequestError("Configured approver user IDs must be positive.", code="invalid_leave_route")
    return {"unit_head_user_id": unit_head, "establishment_user_id": establishment, "sanctioning_authority_user_id": authority}
