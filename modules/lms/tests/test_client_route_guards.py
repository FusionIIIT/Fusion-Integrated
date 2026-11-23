import re
from pathlib import Path

from modules.lms.registry import NAV_ITEMS


def test_client_route_guards_match_the_navigation_permissions():
    root = Path(__file__).resolve().parents[3]
    routes = (root / "client/src/modules/lms/routes.tsx").read_text()
    for item in NAV_ITEMS:
        path = item["to"].removeprefix("/lms/")
        fragment = re.search(r'path:\s*"' + path + r'".*?permission="([^"]+)"', routes, re.S)
        assert fragment and fragment[1] == item["required_permission"]
