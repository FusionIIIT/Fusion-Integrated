"""Verify that client routes guard office pages with nav item permissions.

Enforces that routes.tsx and registry.py agree on required_permission for all office routes:
- /complaints/queue -> complaints.complaint.assign
- /complaints/supervisor -> complaints.complaint.supervise
- /complaints/reports -> complaints.complaint.report
- /complaints/roles -> complaints.role.manage
"""
import re
from pathlib import Path

from modules.complaints.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "complaints"
    / "routes.tsx"
)
OFFICE_PAGES = {"queue", "supervisor", "reports", "roles"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*office\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text(encoding="utf-8")))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/complaints").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_office_page_is_guarded():
    """Verify that all office pages in routes.tsx are guarded by office()."""
    assert set(guarded_routes()) >= OFFICE_PAGES


def test_each_guard_is_its_nav_items_own_permission():
    """Verify that the guard permission matches the permission in registry.py."""
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
