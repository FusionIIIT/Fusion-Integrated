"""The registry and the tests speak the same permission codes (Step 5.1).

A typo'd code is granted by the fake IAM and denied in production — the test
passes and the feature is broken. This suite fails when the two drift apart.
"""
import pathlib
import re

from modules.elm import registry
from modules.elm.domain import state_machine as sm

HERE = pathlib.Path(__file__).parent


def declared() -> set[str]:
    return {code for code, _ in registry.PERMISSIONS}


def test_every_nav_item_requires_a_declared_permission():
    for item in registry.NAV_ITEMS:
        assert item["required_permission"] in declared(), item["code"]


def test_scope_and_system_permissions_are_declared():
    assert set(registry.SCOPE_PERMISSIONS) <= declared()
    assert set(registry.SYSTEM_PERMISSIONS) <= declared()


def test_every_declared_permission_is_granted_or_system():
    granted = {code for codes in registry.ROLE_GRANTS.values() for code in codes}
    orphaned = declared() - granted - set(registry.SYSTEM_PERMISSIONS)
    assert not orphaned, f"declared but unreachable: {sorted(orphaned)}"


def test_every_grant_is_declared():
    granted = {code for codes in registry.ROLE_GRANTS.values() for code in codes}
    assert granted <= declared()


def test_every_permission_carries_the_module_prefix():
    assert all(code.startswith("elm.") for code in declared())


def test_every_permission_used_in_the_tests_is_declared():
    # Quoted on purpose: an unquoted match also catches dotted module paths.
    used: set[str] = set()
    for path in HERE.glob("test_*.py"):
        used.update(re.findall(r'"(elm\.[a-z_]+\.[a-z_]+)"', path.read_text()))
    assert used <= declared(), f"not declared: {sorted(used - declared())}"


def test_every_transition_permission_is_declared():
    for transition in sm.TRANSITIONS:
        assert transition.permission in declared()


def test_the_module_is_grantable_to_someone():
    assert registry.ROLE_GRANTS
    assert all(codes for codes in registry.ROLE_GRANTS.values())
