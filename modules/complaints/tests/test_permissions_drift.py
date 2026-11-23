"""Tests verifying that CMS permission definitions and role grants do not drift."""
import json
import re
from pathlib import Path
import pytest

from modules.complaints import registry
from modules.complaints.domain.state_machine import TRANSITIONS


def _load_manifest_permissions():
    manifest_path = Path("registry/permissions.json")
    assert manifest_path.exists(), "registry/permissions.json must exist"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    complaints_data = data.get("modules", {}).get("complaints", {})
    return complaints_data


def test_registry_permissions_match_manifest():
    """Verify registry.py PERMISSIONS match registry/permissions.json."""
    manifest = _load_manifest_permissions()
    manifest_perm_codes = {p["code"] for p in manifest.get("permissions", [])}
    registry_perm_codes = {code for code, _ in registry.PERMISSIONS}

    assert registry_perm_codes == manifest_perm_codes, (
        f"Permission drift between registry.py and permissions.json: "
        f"diff={registry_perm_codes ^ manifest_perm_codes}"
    )


def test_registry_system_permissions_match_manifest():
    """Verify registry.py SYSTEM_PERMISSIONS match registry/permissions.json."""
    manifest = _load_manifest_permissions()
    manifest_system_perms = set(manifest.get("system_permissions", []))
    registry_system_perms = set(registry.SYSTEM_PERMISSIONS)

    assert registry_system_perms == manifest_system_perms


def test_registry_role_grants_match_manifest():
    """Verify registry.py ROLE_GRANTS are properly reflected in permissions.json."""
    manifest = _load_manifest_permissions()
    manifest_grants = manifest.get("grants", {})

    for role_name, perms in registry.ROLE_GRANTS.items():
        assert role_name in manifest_grants, f"Role '{role_name}' missing from manifest grants."
        expected_perms = set(perms)
        manifest_perms = set(manifest_grants[role_name])
        assert expected_perms == manifest_perms, (
            f"Grant drift for role '{role_name}': "
            f"diff={expected_perms ^ manifest_perms}"
        )


def test_nav_items_permissions_are_valid():
    """Verify every required_permission in NAV_ITEMS exists in PERMISSIONS."""
    valid_perms = {code for code, _ in registry.PERMISSIONS}
    for item in registry.NAV_ITEMS:
        perm = item.get("required_permission")
        assert perm in valid_perms, f"NAV item {item['code']} references unregistered permission {perm}"


def test_state_machine_permissions_are_registered():
    """Verify every permission required by the state machine exists in CMS permissions."""
    all_known_perms = {code for code, _ in registry.PERMISSIONS} | set(registry.SYSTEM_PERMISSIONS)
    for t in TRANSITIONS:
        assert t.permission in all_known_perms, (
            f"Transition {t.frm}->{t.to} requires '{t.permission}' which is not in registry.PERMISSIONS"
        )


def test_views_enforce_registered_permissions():
    """Verify permission strings referenced in views.py are declared in registry.py."""
    views_path = Path("modules/complaints/api/views.py")
    source = views_path.read_text(encoding="utf-8")

    # Find all complaints.* permission strings in views.py
    referenced_perms = set(re.findall(r"['\"](complaints\.[a-zA-Z0-9_.]+)['\"]", source))
    all_known_perms = {code for code, _ in registry.PERMISSIONS} | set(registry.SYSTEM_PERMISSIONS)

    for perm in referenced_perms:
        assert perm in all_known_perms, f"View references unregistered permission: {perm}"
