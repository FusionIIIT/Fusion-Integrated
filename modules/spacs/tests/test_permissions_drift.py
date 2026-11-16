"""Checks that registered permissions match closed vocabulary and role grants."""

from modules.spacs.registry import PERMISSIONS, ROLE_GRANTS


def test_permission_vocabulary():
    """Verify all permissions follow lowercase snake_case with 3 segments and closed verbs."""
    allowed_verbs = {
        "view",
        "create",
        "update",
        "delete",
        "approve",
        "publish",
        "review",
        "assign",
        "revoke",
        "export",
        "import",
        "restore",
        "manage",
    }
    for code, _desc in PERMISSIONS:
        parts = code.split(".")
        assert len(parts) == 3, f"{code} does not have exactly 3 segments"
        assert parts[0] == "spacs", f"{code} prefix is not spacs"
        assert parts[2] in allowed_verbs, f"{code} verb '{parts[2]}' not in closed vocabulary"


def test_role_grants_use_declared_permissions():
    """Verify every permission granted to a role is declared in PERMISSIONS."""
    declared = {code for code, _ in PERMISSIONS}
    for role, perms in ROLE_GRANTS.items():
        for p in perms:
            assert p in declared, f"Role {role} granted undeclared permission {p}"
