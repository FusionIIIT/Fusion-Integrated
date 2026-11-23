import re
from pathlib import Path

from modules.phc.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3]
          / "client" / "src" / "modules" / "phc" / "routes.tsx")


def guarded_routes() -> dict[str, str]:
    return dict(re.findall(
        r'\{\s*path:\s*"([^"]+)",\s*element:\s*guarded\("([^"]+)"',
        ROUTES.read_text(),
    ))


def nav_by_path() -> dict[str, str]:
    base = MODULE["base_path"].rstrip("/")
    return {item["to"][len(base):].lstrip("/"): item["required_permission"]
            for item in NAV_ITEMS}


def test_phc_br_03_every_route_is_guarded_and_matches_a_nav_permission():
    guards = guarded_routes()
    nav = nav_by_path()
    declared = {code for code, _ in PERMISSIONS}

    assert set(guards) == set(nav)
    assert guards == nav
    assert set(guards.values()) <= declared
