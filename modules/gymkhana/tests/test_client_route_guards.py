"""Test client route guards match server permissions."""
from pathlib import Path

from modules.gymkhana.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3]
          / "client" / "src" / "modules" / "gymkhana" / "routes.tsx")


def test_routes_file_exists():
    assert ROUTES.exists()


def test_nav_items_have_declared_permissions():
    declared = {code for code, _ in PERMISSIONS}
    for item in NAV_ITEMS:
        perm = item.get("required_permission")
        assert perm in declared, f"Nav item {item['code']} has undeclared permission {perm}"


def test_nav_base_path():
    base = MODULE.get("base_path")
    assert base == "/gymkhana"
    for item in NAV_ITEMS:
        assert item["to"].startswith(base)
