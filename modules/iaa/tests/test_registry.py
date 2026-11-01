"""Guards against the one-line-off typo that would fail silently at runtime:
a permission code referenced anywhere in views.py must actually exist in
registry.PERMISSIONS. Scans for the code pattern directly rather than just
HasPermission(...) calls, since get_permissions() builds the code in a
variable first (see ExpenseRequestsView/TAClaimsView)."""
import pathlib
import re

from modules.iaa.registry import PERMISSIONS, ROLE_GRANTS

VIEWS_PATH = pathlib.Path(__file__).resolve().parent.parent / "api" / "views.py"
CODE_PATTERN = re.compile(r'"(iaa\.\w+\.\w+)"')


def _codes_used_in_views():
    return set(CODE_PATTERN.findall(VIEWS_PATH.read_text()))


def test_every_permission_code_used_by_a_view_is_registered():
    registered = {code for code, _ in PERMISSIONS}
    used = _codes_used_in_views()
    assert used, "no iaa.*.* permission codes found — did views.py move?"
    missing = used - registered
    assert not missing, f"views.py references unregistered codes: {missing}"


def test_every_registered_permission_is_used_by_some_view():
    registered = {code for code, _ in PERMISSIONS}
    used = _codes_used_in_views()
    unused = registered - used
    assert not unused, f"registered but never checked by any view: {unused}"


def test_every_role_grant_only_uses_registered_codes():
    registered = {code for code, _ in PERMISSIONS}
    for role, codes in ROLE_GRANTS.items():
        unknown = set(codes) - registered
        assert not unknown, f"role '{role}' grants unregistered codes: {unknown}"


def test_permissions_list_has_no_duplicate_codes():
    codes = [code for code, _ in PERMISSIONS]
    assert len(codes) == len(set(codes))
