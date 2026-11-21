"""Shared fixtures for Assignment #8 automated specification test suites."""
import pytest
from rest_framework.test import APIRequestFactory

from fusion_auth.principal import Principal


@pytest.fixture
def super_admin_principal() -> Principal:
    return Principal(
        user_id=1,
        username="admin_master",
        display_name="Master Super Admin",
        kind="staff",
        active_role="super_admin",
        roles=("super_admin",),
        permissions=frozenset({"super_admin", "admin:access", "system_admin.access", "system_admin:full_control"}),
        modules=("system_admin",),
        email="superadmin@iiitdmj.ac.in",
    )


@pytest.fixture
def it_head_principal() -> Principal:
    return Principal(
        user_id=2,
        username="it_head",
        display_name="Head of IT Services",
        kind="faculty",
        active_role="it_head",
        roles=("it_head",),
        permissions=frozenset({"it_head", "purge:authorize", "it_head:access", "system_admin:purge_authorize"}),
        modules=("system_admin",),
        email="ithead@iiitdmj.ac.in",
    )


@pytest.fixture
def standard_student_principal() -> Principal:
    return Principal(
        user_id=10,
        username="student1",
        display_name="Student One",
        kind="student",
        active_role="student",
        roles=("student",),
        permissions=frozenset(),
        modules=(),
        email="student1@iiitdmj.ac.in",
    )


@pytest.fixture
def rf() -> APIRequestFactory:
    return APIRequestFactory()

# Attach id property to Principal so existing principal fixtures work seamlessly
if not hasattr(Principal, 'id'):
    Principal.id = property(lambda self: self.user_id)
