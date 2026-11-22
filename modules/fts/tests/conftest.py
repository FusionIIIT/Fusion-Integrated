"""Test fixtures and helpers for FTS test suite."""
import pytest
from rest_framework.test import APIClient

from fusion_auth.client import IamSession
from fusion_auth.principal import Principal


def make_session(
    user_id=1001,
    permissions=(),
    modules=(),
    kind="student",
    roles=("student",),
    active_role="student",
):
    return IamSession(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"User {user_id}",
        kind=kind,
        active_role=active_role,
        roles=tuple(roles),
        permissions=frozenset(permissions),
        modules=tuple(modules),
    )


def make_principal(**kw):
    return Principal.from_session(make_session(**kw))


def make_fts_session(
    user_id=1001,
    permissions=(),
    modules=("fts",),
    kind="faculty",
    roles=("faculty",),
    active_role="Assistant Professor",
):
    return IamSession(
        user_id=user_id,
        username=f"u{user_id}",
        display_name=f"User {user_id}",
        kind=kind,
        active_role=active_role,
        roles=tuple(roles),
        permissions=frozenset(permissions),
        modules=tuple(modules),
    )


@pytest.fixture
def fts_client(stub_iam):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fts-test-token")

    def _as_user(
        user_id=101,
        kind="faculty",
        roles=("faculty",),
        active_role="Assistant Professor",
        permissions=None,
    ):
        perms = (
            permissions
            if permissions is not None
            else (
                "fts.file.create",
                "fts.file.forward",
                "fts.file.return",
                "fts.file.archive",
                "fts.file.view",
            )
        )
        stub_iam(
            make_fts_session(
                user_id=user_id,
                kind=kind,
                roles=roles,
                active_role=active_role,
                modules=("fts",),
                permissions=perms,
            )
        )
        return c

    return _as_user


@pytest.fixture
def admin_client(stub_iam):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token admin-token")

    def _as_admin(user_id=999):
        stub_iam(
            make_fts_session(
                user_id=user_id,
                kind="staff",
                roles=("admin", "System Administrator"),
                active_role="System Administrator",
                modules=("fts",),
                permissions=("fts.governance.view", "fts.governance.manage"),
            )
        )
        return c

    return _as_admin
