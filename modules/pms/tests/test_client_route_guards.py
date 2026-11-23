"""Every PMS page is guarded by exactly its nav item's permission (Step 6.4)."""
import re
from pathlib import Path

from modules.pms.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES = (Path(__file__).resolve().parents[3]
          / "client" / "src" / "modules" / "pms" / "routes.tsx")


def guarded_routes() -> dict[str, str]:
    pattern = r'\{\s*path:\s*"([^"]+)",\s*element:\s*guard\(\s*"([^"]+)"'
    return dict(re.findall(pattern, ROUTES.read_text()))


def nav_permission(path: str) -> str | None:
    base = MODULE["base_path"].rstrip("/")
    return next((i["required_permission"] for i in NAV_ITEMS if i["to"] == f"{base}/{path}"),
                None)


def test_every_page_is_guarded():
    routed = set(re.findall(r'\{\s*path:\s*"([^"]+)"', ROUTES.read_text()))
    assert routed == set(guarded_routes())
    assert len(routed) == len(NAV_ITEMS)


# BR-PMS-126 PMS-AFR-216
def test_each_guard_is_its_nav_items_own_permission():
    declared = {code for code, _ in PERMISSIONS}
    for path, permission in guarded_routes().items():
        assert permission in declared, f"{path}: {permission} is not declared"
        assert permission == nav_permission(path), f"{path}: guard and nav item disagree"
