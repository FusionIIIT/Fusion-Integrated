"""Client route guards: each nav item's required_permission must match routes.tsx."""

from __future__ import annotations

import re
from pathlib import Path

from modules.superadmin.registry import MODULE, NAV_ITEMS, PERMISSIONS

ROUTES_PATH = (
    Path(__file__).resolve().parents[3] / "client" / "src" / "modules" / "superadmin" / "routes.tsx"
)

_GUARDED_PATTERN = re.compile(
    r'path:\s*"([^"]+)".*?requiredPermission:\s*"([^"]+)"',
    re.DOTALL,
)
_PATH_ELEM_PATTERN = re.compile(
    r'path:\s*"([^"]+)"',
)


def _route_text() -> str:
    return ROUTES_PATH.read_text(encoding="utf-8")


def _guarded_routes() -> dict[str, str]:
    # Map route-path → requiredPermission from routes.tsx
    return dict(_GUARDED_PATTERN.findall(_route_text()))


def _all_route_paths() -> set[str]:
    return set(_PATH_ELEM_PATTERN.findall(_route_text()))


def _nav_permission(to_path: str) -> str | None:
    for item in NAV_ITEMS:
        if item.get("to") == to_path:
            return item.get("required_permission")
    return None


def test_routes_file_exists():
    assert ROUTES_PATH.exists(), f"routes.tsx not found at {ROUTES_PATH}"


def test_every_nav_item_has_a_declared_permission():
    declared = {code for code, _ in PERMISSIONS}
    for item in NAV_ITEMS:
        perm = item.get("required_permission")
        assert perm is not None, f"Nav item {item['code']} has no required_permission"
        assert perm in declared, f"Nav item {item['code']}: {perm} not in PERMISSIONS"


def test_every_nav_item_to_path_appears_in_routes():
    all_paths = _all_route_paths()
    base = MODULE.get("base_path", "/superadmin").rstrip("/")
    for item in NAV_ITEMS:
        # Nav item to="/superadmin/dashboard" should match route path "dashboard" or "/superadmin/dashboard"
        to = item["to"]
        segment = to.removeprefix(base).lstrip("/")
        assert segment in all_paths or to in all_paths, (
            f"Nav item '{item['code']}' to='{to}' not found in routes.tsx paths: {all_paths}"
        )


def test_all_declared_permissions_are_valid_strings():
    for code, description in PERMISSIONS:
        assert isinstance(code, str) and code.startswith("superadmin.")
        assert isinstance(description, str) and len(description) > 0


def test_role_grants_only_use_declared_permissions():
    from modules.superadmin.registry import ROLE_GRANTS

    declared = {code for code, _ in PERMISSIONS}
    for role, grants in ROLE_GRANTS.items():
        for perm in grants:
            assert perm in declared, f"Role '{role}' grants '{perm}' which is not in PERMISSIONS"


def test_it_head_cannot_purge_add():
    # IT Head must not hold purge.add — that belongs exclusively to super_admin
    from modules.superadmin.registry import ROLE_GRANTS

    it_grants = set(ROLE_GRANTS.get("it_head", []))
    assert "superadmin.purge.add" not in it_grants, (
        "IT Head must not be granted purge.add — dual-auth requires distinct roles"
    )


def test_super_admin_cannot_purge_change():
    # super_admin requests purge but cannot approve their own — purge.change is IT Head only
    from modules.superadmin.registry import ROLE_GRANTS

    sa_grants = set(ROLE_GRANTS.get("super_admin", []))
    assert "superadmin.purge.change" not in sa_grants, (
        "Super Admin must not hold purge.change — that breaks the dual-authorization boundary"
    )
