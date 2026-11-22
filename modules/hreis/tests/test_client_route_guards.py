"""Static route checks cover every nav entry independently of browser mounting."""

import re
from pathlib import Path

from modules.hreis.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "hreis" / "routes.tsx"


def guarded_routes() -> dict[str, str]:
    expression = (
        r'\{\s*path:\s*"([^"]+)"\s*,?\s*'
        r'element:\s*protectedPage\(\s*"([^"]+)"'
    )
    return dict(re.findall(expression, ROUTES.read_text(encoding="utf-8")))


def test_each_navigation_destination_has_an_actual_protected_route():
    expected = {item["to"].removeprefix(MODULE["base_path"] + "/") for item in NAV_ITEMS}
    assert set(guarded_routes()) == expected


def test_every_guard_uses_exact_navigation_permission():
    declared = {code for code, _description in PERMISSIONS}
    nav_permissions = {
        item["to"].removeprefix(MODULE["base_path"] + "/"): item["required_permission"]
        for item in NAV_ITEMS
    }
    for path, permission in guarded_routes().items():
        assert permission in declared, f"Undeclared {permission} on route {path}"
        assert permission == nav_permissions[path], (
            f"{path}: guard {permission} differs from nav {nav_permissions[path]}"
        )
