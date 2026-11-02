"""Fixtures shared by every vms test directory."""
import pytest
from rest_framework.test import APIClient

from fusion_auth.client import IamSession


@pytest.fixture
def api_as(stub_iam):
    """`api_as(user_id=..., permissions=(...), kind=..., email=...)` returns an
    APIClient authenticated as that IAM principal. `api_as()` with no
    arguments yields an anonymous client."""
    def _make(anonymous=False, user_id=2001, permissions=(), kind="staff", email=""):
        if anonymous:
            stub_iam(None)
            return APIClient()
        stub_iam(IamSession(
            user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
            kind=kind, active_role=kind, roles=(kind,),
            permissions=frozenset(permissions), modules=("vms",), email=email))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client
    return _make
