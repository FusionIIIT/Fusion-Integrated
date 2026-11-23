"""Client route guard tests ensuring parity with registry.NAV_ITEMS (R1-15)."""

import re
from pathlib import Path

from modules.lms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "lms"
    / "routes.tsx"
)
LMS_PAGES = {"courses", "materials", "announcements", "assignments", "grades", "grading"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guarded\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/lms").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_lms_page_is_guarded():
    assert set(guarded_routes()) == LMS_PAGES


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
