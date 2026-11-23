from modules.oap import registry


def test_every_granted_permission_is_declared():
    declared = {code for code, _ in registry.PERMISSIONS}
    granted = {c for codes in registry.ROLE_GRANTS.values() for c in codes}
    assert granted <= declared


def test_every_nav_item_requires_a_declared_permission():
    declared = {code for code, _ in registry.PERMISSIONS}
    for item in registry.NAV_ITEMS:
        assert item["required_permission"] in declared
        assert item["to"].startswith("/oap/")


def test_no_retired_spec_id_is_cited_in_code():
    import pathlib

    root = pathlib.Path(registry.__file__).parent
    for path in root.rglob("*.py"):
        if "tests" in path.parts or "migrations" in path.parts:
            continue
        text = path.read_text()
        for retired in ("FR-OAP-003", "FR-OAP-050", "FR-OAP-051"):
            assert retired not in text, f"{retired} cited in {path}"
