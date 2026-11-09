from modules.elm import registry


def test_module_manifest_matches_module_route_identity():
    assert registry.MODULE["code"] == "elm"
    assert registry.MODULE["base_path"] == "/elm"
    assert registry.MODULE["status"] == "active"
    assert registry.MODULE["label"]
    assert registry.MODULE["icon"]


def test_navigation_codes_and_paths_are_unique():
    codes = [item["code"] for item in registry.NAV_ITEMS]
    paths = [item["to"] for item in registry.NAV_ITEMS]
    assert len(codes) == len(set(codes))
    assert len(paths) == len(set(paths))


def test_navigation_items_stay_under_module_base_path():
    for item in registry.NAV_ITEMS:
        assert item["to"].startswith(registry.MODULE["base_path"] + "/")
        assert item["code"].startswith(registry.MODULE["code"] + ".")


def test_navigation_items_reference_declared_permissions():
    known = {permission for permission, _ in registry.PERMISSIONS}
    assert all(item["required_permission"] in known for item in registry.NAV_ITEMS)


def test_permissions_are_unique_and_have_descriptions():
    codes = [code for code, _ in registry.PERMISSIONS]
    assert len(codes) == len(set(codes))
    assert all(code.startswith("elm.") and description.strip() for code, description in registry.PERMISSIONS)


def test_role_grants_only_reference_declared_permissions():
    known = {code for code, _ in registry.PERMISSIONS}
    for role, grants in registry.ROLE_GRANTS.items():
        assert set(grants) <= known, role
        assert len(grants) == len(set(grants)), role


def test_faculty_and_staff_get_self_service_but_not_review():
    for role in ("faculty", "staff"):
        grants = registry.ROLE_GRANTS[role]
        assert {"elm.leave.view_self", "elm.leave.apply"} <= set(grants)
        assert "elm.leave.review" not in grants
        assert "elm.policy.manage" not in grants


def test_unit_head_has_review_access_but_not_policy_management():
    grants = registry.ROLE_GRANTS["Unit Head"]
    assert "elm.leave.review" in grants
    assert "elm.policy.manage" not in grants


def test_leave_administrator_can_manage_policy_and_review():
    assert {"elm.leave.review", "elm.policy.manage"} <= set(registry.ROLE_GRANTS["Leave Administrator"])


def test_every_permission_has_an_explicit_role_grant():
    all_grants = {permission for grants in registry.ROLE_GRANTS.values() for permission in grants}
    assert {permission for permission, _ in registry.PERMISSIONS} <= all_grants
