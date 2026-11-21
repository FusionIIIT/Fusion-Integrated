"""Tests for FTS registry declarations and RBAC mapping."""
from modules.fts import registry


def test_fts_registry_module_metadata():
    assert registry.MODULE["code"] == "fts"
    assert registry.MODULE["label"] == "File Tracking"
    assert len(registry.NAV_ITEMS) == 4


def test_fts_permissions_and_role_grants():
    perm_codes = {code for code, _ in registry.PERMISSIONS}
    assert "fts.file.view" in perm_codes
    assert "fts.file.create" in perm_codes
    assert "fts.file.update" in perm_codes
    assert "fts.file.delete" in perm_codes
    assert "fts.file.manage" in perm_codes
    assert "fts.audit.view" in perm_codes

    for role, grants in registry.ROLE_GRANTS.items():
        for grant in grants:
            assert grant in perm_codes, f"Unknown permission {grant} granted to {role}"
