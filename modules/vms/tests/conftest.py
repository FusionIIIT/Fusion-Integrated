import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.vms.registry import _ADMIN, _HOST, _SECURITY


class SessionSwitchingClient(APIClient):
    """APIClient that sets stub IAM session on each request."""

    def __init__(self, stub_iam_setter, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setter = stub_iam_setter
        self._session = session
        self.credentials(HTTP_AUTHORIZATION="Token dev-test-token")

    def generic(self, *args, **kwargs):
        self._setter(self._session)
        return super().generic(*args, **kwargs)


@pytest.fixture
def vms_client(stub_iam):
    """Helper to mint APIClient with specific user, module grant, and permissions."""

    def _make(user_id=1, perms=_ADMIN, modules=("vms",), kind="staff"):
        sess = make_session(user_id=user_id, permissions=perms, modules=modules, kind=kind)
        return SessionSwitchingClient(stub_iam, sess)

    return _make


@pytest.fixture
def admin_client(vms_client):
    return vms_client(user_id=1, perms=_ADMIN, kind="staff")


@pytest.fixture
def security_client(vms_client):
    return vms_client(user_id=2, perms=_SECURITY, kind="staff")


@pytest.fixture
def host_client(vms_client):
    return vms_client(user_id=3, perms=_HOST, kind="faculty")
