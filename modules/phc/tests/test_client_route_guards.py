"""Each client route is guarded by its nav item's own permission (routes.tsx vs registry.py)."""
import re
from pathlib import Path

from modules.phc.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3]
          / "client" / "src" / "modules" / "phc" / "routes.tsx")
OFFICE_PAGES = {"inventory", "requisitions", "ambulance", "reports"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guard\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE["base_path"].rstrip("/")
    for item in NAV_ITEMS:
        if item["to"] == f"{base}/{path}":
            return item["required_permission"]
    return None


def test_every_office_page_is_guarded():
    assert set(guarded_routes()) >= OFFICE_PAGES


def test_every_route_has_a_guard():
    assert len(guarded_routes()) == len(NAV_ITEMS)


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
