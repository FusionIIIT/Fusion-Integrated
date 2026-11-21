"""Pytest fixtures and test helpers for modules.system_admin test suite.

Traceability: CFR-SA-001..023, BR-SA-001..035.
"""
from __future__ import annotations

import datetime
import pytest
from rest_framework.test import APIRequestFactory

from fusion_auth.principal import Principal
from modules.system_admin.constants import (
    RoleCategory,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.models import (
    BasicUser,
    RoleDefinition,
    UserProfile,
)


@pytest.fixture
def super_admin_principal() -> Principal:
    return Principal(
        user_id=1,
        username="admin_master",
        display_name="Master Super Admin",
        kind="staff",
        active_role="super_admin",
        roles=("super_admin",),
        permissions=frozenset({"super_admin", "admin:access", "system_admin.access"}),
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
        permissions=frozenset({"it_head", "purge:authorize", "it_head:access"}),
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


@pytest.fixture
def mock_basic_student() -> BasicUser:
    user = BasicUser(
        id=10,
        username="2026bcs001",
        institute_id="2026BCS001",
        email="2026bcs001@iiitdmj.ac.in",
        kind=UserKind.STUDENT,
        is_active=True,
        status=UserLifecycleStatus.ACTIVE,
    )
    user.profile = UserProfile(
        user=user,
        display_name="Alice Smith",
        contact_number="9876543210",
        programme="B.Tech",
        discipline="CSE",
        batch_year=2026,
    )
    return user


@pytest.fixture
def mock_singular_role() -> RoleDefinition:
    return RoleDefinition(
        code="dean_academic",
        label="Dean Academic",
        category=RoleCategory.OFFICE,
        allowed_kinds="faculty",
        is_singular=True,
        is_time_bound=True,
        is_active=True,
    )
