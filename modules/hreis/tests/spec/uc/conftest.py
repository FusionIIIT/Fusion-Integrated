import pytest
from rest_framework.test import APIClient

from fusion_auth.client import IamSession
from modules.hreis.registry import ROLE_GRANTS


def make_session(user_id=1001, permissions=(), modules=(), kind="faculty",
                 roles=("faculty",), active_role="faculty"):
    return IamSession(
        user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
        kind=kind, active_role=active_role, roles=tuple(roles),
        permissions=frozenset(permissions), modules=tuple(modules),
    )


@pytest.fixture
def auth_client_factory(stub_iam):
    def _create(user_id=101, role="faculty", extra_permissions=None):
        permissions = list(ROLE_GRANTS.get(role, []))
        if extra_permissions:
            permissions.extend(extra_permissions)
        session = make_session(
            user_id=user_id,
            kind="faculty" if role in ("faculty", "hod", "director") else "staff",
            active_role=role,
            roles=(role,),
            permissions=tuple(permissions),
            modules=("hr_eis",),
        )
        stub_iam(session)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token tok-{user_id}")
        return client, session

    return _create
