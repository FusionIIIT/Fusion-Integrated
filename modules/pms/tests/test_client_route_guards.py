"""Client route guards must match the server-driven PMS navigation grants."""

import re
from pathlib import Path

from modules.pms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "pms"
    / "routes.tsx"
)


def guarded_routes() -> dict[str, str]:
    pattern = (
        r'\{\s*path:\s*"([^"]+)",\s*element:\s*'
        r'(?:office\(\s*"([^"]+)"|<RequirePermission\s+permission="([^"]+)")'
    )
    return {
        path: office_permission or direct_permission
        for path, office_permission, direct_permission in re.findall(pattern, ROUTES.read_text())
    }


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/pms").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_role_only_pms_route_has_its_nav_permission_guard():
    routes = guarded_routes()
    expected_paths = {item["to"].removeprefix("/pms/") for item in NAV_ITEMS}
    assert set(routes) == expected_paths

    declared_permissions = {code for code, _ in PERMISSIONS}
    for path, permission in routes.items():
        assert permission in declared_permissions, f"{path}: permission is not declared"
        assert permission == nav_permission(path), f"{path}: route and nav permissions differ"


def test_pms_nav_uses_phosphor_icon_names():
    assert all(not item["icon"].startswith("Fa") for item in NAV_ITEMS)
    assert all(item.get("required_permission") for item in NAV_ITEMS)
