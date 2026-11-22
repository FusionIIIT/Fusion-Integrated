"""The client guards each page with its nav item's own permission.

routes.tsx and registry.py name the same permission twice; a typo would lock users
out of their own page, or let the wrong role in, with every test still green.
"""
from __future__ import annotations

import re
from pathlib import Path

from modules.fts.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (
    Path(__file__).resolve().parents[3]
    / "client"
    / "src"
    / "modules"
    / "fts"
    / "routes.tsx"
)
GUARDED_PAGES = {"inbox", "outbox", "drafts", "create", "governance"}


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guarded\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE.get("base_path", "/fts").rstrip("/")
    for item in NAV_ITEMS:
        if item.get("to") == f"{base}/{path}":
            return item.get("required_permission")
    return None


def test_every_fts_page_is_guarded():
    """BR-FTS-010: Verify every FTS page in client routes is protected by a guard."""
    assert set(guarded_routes()) >= GUARDED_PAGES


def test_each_guard_is_its_nav_items_own_permission():
    """Verify each route guard matches the exact required_permission from registry."""
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared in registry"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
