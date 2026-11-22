"""The client guards each IAA page with its nav item's own permission.

routes.tsx and registry.py name the same permission twice; a typo would lock a role out of its
own page, or let the wrong role in, with every other test still green.
"""
import re
from pathlib import Path

from modules.iaa.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3]
          / "client" / "src" / "modules" / "iaa" / "routes.tsx")
PAGES = {"my-requests", "finance", "approvals", "anomalies", "observations", "reports",
         "notifications", "configuration"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guard\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE["base_path"].rstrip("/")
    for item in NAV_ITEMS:
        if item["to"] == f"{base}/{path}":
            return item["required_permission"]
    return None


def test_every_page_is_guarded():
    assert set(guarded_routes()) == PAGES


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"


def test_every_nav_item_leads_to_a_guarded_page():
    base = MODULE["base_path"].rstrip("/")
    for item in NAV_ITEMS:
        assert item["to"].removeprefix(f"{base}/") in guarded_routes(), item["code"]
