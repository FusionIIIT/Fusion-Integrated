# Pin every guarded PSM client route to its nav item's required_permission (Step 6.4).
import re
from pathlib import Path

from modules.psm.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "psm" / "routes.tsx"
OFFICE_PAGES = {
    "stock",
    "transfers",
    "vendors",
    "tenders",
    "purchase-orders",
    "invoices",
    "reports",
    "audit",
    "policy",
}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*office\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text(encoding="utf-8")))


def nav_permission(path: str) -> str | None:
    base = MODULE["base_path"].rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_office_page_is_guarded():
    assert set(guarded_routes()) >= OFFICE_PAGES


def test_each_guard_matches_its_nav_items_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
