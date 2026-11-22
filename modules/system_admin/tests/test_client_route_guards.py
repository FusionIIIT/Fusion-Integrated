"""Client routes are guarded by exactly their nav items' required permissions."""
import re
from pathlib import Path

from modules.system_admin.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "system_admin"
    / "routes.tsx"
)


def guarded_routes() -> dict[str, str]:
    pattern = r'path:\s*"([^"]*)",\s*element:\s*guarded\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/system_admin").rstrip("/")
    target = f"{base}/{path}".rstrip("/")
    for item in NAV_ITEMS:
        item_to = item.get("to", "").rstrip("/")
        if item_to == target:
            return item.get("required_permission")
    return None


def test_every_page_is_guarded():
    routes = guarded_routes()
    assert len(routes) == 6
    assert "" in routes
    assert "users" in routes
    assert "roles" in routes
    assert "archives" in routes
    assert "audit" in routes
    assert "config" in routes


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared in registry"
        expected = nav_permission(path)
        assert permission == expected, f"{path}: guard {permission} != nav item {expected}"
