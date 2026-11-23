"""Permission catalog drift tests for BADMS.
"""
import json
from pathlib import Path

from modules.badms.registry import PERMISSIONS, ROLE_GRANTS


def test_permission_catalog_has_all_badms_permissions():
    catalog_path = Path("registry/permissions.json")
    assert catalog_path.exists(), "registry/permissions.json must exist"
    catalog = json.loads(catalog_path.read_text())

    catalog_perms = {p["code"] for p in catalog["modules"]["badms"]["permissions"]}
    registry_perms = {p[0] for p in PERMISSIONS}

    missing_in_catalog = registry_perms - catalog_perms
    assert not missing_in_catalog, f"Permissions in registry but missing from catalog: {missing_in_catalog}"


def test_registry_roles_have_valid_permissions():
    reg_perms = {p[0] for p in PERMISSIONS}
    for role_name, perms in ROLE_GRANTS.items():
        unknown_perms = set(perms) - reg_perms
        assert not unknown_perms, f"Role {role_name} has unknown permissions: {unknown_perms}"
