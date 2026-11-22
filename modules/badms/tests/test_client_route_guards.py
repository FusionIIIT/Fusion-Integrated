"""The client guards each BADMS page with its nav item's own permission."""

from pathlib import Path
import re

from modules.badms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "badms"
    / "routes.tsx"
)
GUARDED_PAGES = {"archives", "operations"}


def guarded_routes() -> dict[str, str]:
    pattern = r'path:\s*"([^"]+)",\s*element:\s*office\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/badms").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_office_page_is_guarded():
    assert set(guarded_routes()) >= GUARDED_PAGES


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), (
            f"{path}: guard and nav item disagree"
        )
