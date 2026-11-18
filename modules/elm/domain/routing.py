"""Approval-route resolution from current configured hierarchy."""

HIGHER_CATEGORIES = {"SCL", "EL", "COL", "VL"}


class RouteError(ValueError):
    pass


def resolve_route(*, category: str, applicant_role: str, department: str, hierarchy: dict | None) -> list[dict]:
    hierarchy = hierarchy or {}
    if applicant_role.lower() == "director":
        return [{"role": "Director", "kind": "self_sanction", "final": True}]
    unit_heads = hierarchy.get("unit_heads", {})
    unit_head = unit_heads.get(department)
    if not unit_head:
        raise RouteError(f"No Unit Head is configured for {department or 'the employee unit'}.")
    route = [{"role": unit_head, "kind": "review", "final": category in {"CL", "RH"}}]
    if category in HIGHER_CATEGORIES:
        steps = hierarchy.get("sanctioning", {}).get(category, [])
        if not steps:
            steps = hierarchy.get("default_sanctioning", [])
        if not steps:
            raise RouteError(f"No higher sanctioning hierarchy is configured for {category}.")
        route.extend({"role": role, "kind": "sanction", "final": index == len(steps) - 1} for index, role in enumerate(steps))
    return route
