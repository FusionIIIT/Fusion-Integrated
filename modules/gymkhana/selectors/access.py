"""What the acting role may do; a session lists the permissions of every role held."""

from __future__ import annotations

from modules.gymkhana.registry import PERMISSIONS, ROLE_GRANTS


def acting_roles(principal) -> frozenset[str]:
    """The roles whose grants count right now."""
    active, held = principal.active_role, principal.roles
    if active not in held:
        return frozenset(held)
    if active in ROLE_GRANTS:
        return frozenset({active})
    # A designation this module does not know, such as ug_student, acts as the basic role.
    return frozenset({active, principal.kind})


def may(principal, code: str) -> bool:
    """Held, and not only through a role this person is not acting as."""
    if not principal.has_permission(code):
        return False
    granting = {r for r in principal.roles if code in ROLE_GRANTS.get(r, ())}
    return not granting or bool(granting & acting_roles(principal))


def acting_permissions(principal) -> list[str]:
    return sorted(code for code, _ in PERMISSIONS if may(principal, code))
