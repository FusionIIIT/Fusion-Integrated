"""The client guards each administrative page with its nav item's own permission.
routes.tsx and registry.py name the same permission twice; this test verifies they stay in sync.
"""

import re
from pathlib import Path

from modules.vms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "vms" / "routes.tsx"
GUARDED_PAGES = {"approvals", "gate", "security", "muster"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guard\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/vms").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_guarded_page_is_guarded():
    assert set(guarded_routes()) >= GUARDED_PAGES


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
