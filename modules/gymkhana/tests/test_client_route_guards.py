"""Each client route is closed with exactly its nav item's permission (Step 6.4)."""
import re
from pathlib import Path

from modules.gymkhana.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "gymkhana"
          / "routes.tsx")


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*only\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def all_routes() -> set[str]:
    return set(re.findall(r'\{\s*path:\s*"([^"]+)"', ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE["base_path"].rstrip("/")
    for item in NAV_ITEMS:
        if item["to"] == f"{base}/{path}":
            return item["required_permission"]
    return None


def test_every_route_is_guarded():
    assert set(guarded_routes()) == all_routes()
    assert len(all_routes()) == len(NAV_ITEMS)


def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"


def test_every_nav_item_carries_a_required_permission():
    assert all(item.get("required_permission") for item in NAV_ITEMS)
