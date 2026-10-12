"""Permission codes used anywhere must be the ones the registry declares."""
from modules.elm import registry
from modules.elm.domain import routing
from modules.elm.tests import conftest as fx

DECLARED = {code for code, _ in registry.PERMISSIONS}


def test_fixture_grants_are_declared():
    for perms in (fx.EMPLOYEE, fx.UNIT_HEAD, fx.ESTT, fx.SANCTION, fx.ADMIN):
        assert set(perms) <= DECLARED


def test_every_nav_item_is_guarded_by_a_declared_permission():
    for item in registry.NAV_ITEMS:
        assert item["required_permission"] in DECLARED


def test_every_role_in_the_default_hierarchy_can_decide():
    deciders = {d for d, codes in registry.ROLE_GRANTS.items()
                if {"elm.leave_request.review", "elm.leave_request.approve"} & set(codes)}
    assert routing.roles_in(registry.DEFAULT_HIERARCHY) <= deciders


def test_students_are_not_granted_elm():
    assert "student" not in registry.ROLE_GRANTS
