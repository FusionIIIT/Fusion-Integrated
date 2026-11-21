"""Module-level fixtures shared across all superadmin tests."""

from __future__ import annotations

import pytest

from conftest import make_principal, make_session

SA_PERMS = (
    "superadmin.dashboard.view",
    "superadmin.archival.view",
    "superadmin.archival.add",
    "superadmin.archival.change",
    "superadmin.purge.view",
    "superadmin.purge.add",
    "superadmin.policy.view",
    "superadmin.policy.change",
    "superadmin.audit.view",
)

IT_PERMS = (
    "superadmin.dashboard.view",
    "superadmin.archival.view",
    "superadmin.purge.view",
    "superadmin.purge.change",
    "superadmin.policy.view",
    "superadmin.audit.view",
)


@pytest.fixture
def sa_principal():
    """Principal with all super_admin permissions (uid=100)."""
    return make_principal(
        user_id=100,
        kind="staff",
        roles=("super_admin",),
        active_role="super_admin",
        permissions=SA_PERMS,
        modules=("superadmin",),
    )


@pytest.fixture
def it_principal():
    """Principal with all it_head permissions (uid=200)."""
    return make_principal(
        user_id=200,
        kind="staff",
        roles=("it_head",),
        active_role="it_head",
        permissions=IT_PERMS,
        modules=("superadmin",),
    )


@pytest.fixture
def minimal_principal():
    """Principal with no superadmin permissions (uid=999)."""
    return make_principal(
        user_id=999,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=(),
        modules=(),
    )


def _sa_client(stub_iam, uid=100):
    from rest_framework.test import APIClient

    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            roles=("super_admin",),
            active_role="super_admin",
            permissions=SA_PERMS,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _it_client(stub_iam, uid=200):
    from rest_framework.test import APIClient

    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            roles=("it_head",),
            active_role="it_head",
            permissions=IT_PERMS,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _anon_client(stub_iam, uid=999):
    from rest_framework.test import APIClient

    stub_iam(
        make_session(
            user_id=uid,
            kind="student",
            roles=("student",),
            active_role="student",
            permissions=(),
            modules=(),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c
