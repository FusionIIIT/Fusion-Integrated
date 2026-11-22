"""Fixtures shared by every vms test directory."""
import pytest
from rest_framework.test import APIClient

from fusion_auth.client import IamSession
from modules.directory.contracts import UserDTO


@pytest.fixture(autouse=True)
def _directory_hosts(monkeypatch):
    """Any user id below 100000 is a staff member; larger ids do not exist.

    Directories with their own roster (gaps/registration) override this fixture.
    """
    def fake_get_users(ids):
        return {i: UserDTO(user_id=i, username=f"u{i}", display_name=f"User {i}",
                           kind="staff") for i in ids if i < 100000}
    monkeypatch.setattr("modules.directory.contracts.get_users", fake_get_users)


@pytest.fixture
def api_as(stub_iam):
    """`api_as(user_id=..., permissions=(...), kind=..., email=..., modules=("vms",))` returns an
    APIClient authenticated as that IAM principal. `api_as()` with no
    arguments yields an anonymous client."""
    def _make(anonymous=False, user_id=2001, permissions=(), kind="staff", email="",
              modules=("vms",)):
        if anonymous:
            stub_iam(None)
            return APIClient()
        stub_iam(IamSession(
            user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
            kind=kind, active_role=kind, roles=(kind,),
            permissions=frozenset(permissions), modules=tuple(modules), email=email))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client
    return _make
