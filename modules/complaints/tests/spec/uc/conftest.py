import pytest
from rest_framework.test import APIClient
from fusion_auth.client import IamSession
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.fixture
def api_client(stub_iam):
    """Provide a DRF APIClient instance configured with IAM token authentication."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-123")
    return client

@pytest.fixture
def make_session():
    """Return an IamSession factory function with complaints module enabled by default."""
    def _factory(
        user_id=1001,
        permissions=(),
        modules=("complaints",),
        kind="student",
        roles=("student",),
        active_role="student",
    ):
        if "complaints" not in modules:
            modules = tuple(modules) + ("complaints",)
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
    return _factory

__all__ = [
    "api_client",
    "make_session",
    "complaint_factory",
]
