"""Test factories and test helpers for RSPC tests."""

from fusion_auth.principal import Principal


def make_principal(
    user_id: int = 101,
    username: str = "faculty_user",
    roles: tuple[str, ...] = ("faculty",),
    active_role: str = "faculty",
    permissions: set[str] | None = None,
) -> Principal:
    perms = set(permissions or set())
    # grant basic faculty permissions by default if faculty
    if "faculty" in roles and not perms:
        perms = {
            "rspc.proposal.create",
            "rspc.proposal.view_self",
            "rspc.consultancy.create",
            "rspc.consultancy.view_self",
            "rspc.project.view_self",
            "rspc.project.update",
            "rspc.staff.request",
            "rspc.staff.recommend",
            "rspc.finance.request",
            "rspc.procurement.request",
            "rspc.report.submit",
            "rspc.closure.submit",
            "rspc.notification.view_self",
        }
    return Principal(
        user_id=user_id,
        username=username,
        display_name=username.replace("_", " ").title(),
        kind="institute",
        active_role=active_role,
        roles=roles,
        permissions=frozenset(perms),
        modules=("rspc",),
        email=f"{username}@iiitdmj.ac.in",
    )
