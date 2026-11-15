"""Shared BADMS test actors built from the same principal value object as production."""
import pytest

from fusion_auth.client import IamSession
from fusion_auth.principal import Principal


@pytest.fixture
def principal_factory():
    def make_principal(*, user_id=9001, permissions=(), active_role="staff", kind="staff"):
        session = IamSession(
            user_id=user_id,
            username=f"a8-user-{user_id}",
            display_name=f"A8 User {user_id}",
            kind=kind,
            active_role=active_role,
            roles=(active_role,) if active_role else (),
            permissions=frozenset(permissions),
            modules=("badms",),
        )
        return Principal.from_session(session)

    return make_principal


@pytest.fixture
def department_principal(principal_factory):
    """Principal-like wrapper carrying IAM directory department context for scoping tests."""
    def make(*, department, **kwargs):
        principal = principal_factory(**kwargs)
        return type("DepartmentPrincipal", (), {
            "user_id": principal.user_id,
            "department": department,
            "has_permission": principal.has_permission,
        })()
    return make
