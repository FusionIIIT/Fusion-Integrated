"""CSRF applies to ambient credentials only.

A cookie is attached by the browser whether or not the page meant to send it.
An `Authorization` header cannot be set cross-site, so it needs no token.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf

pytestmark = pytest.mark.django_db

PERMS = ("placement_cell.application.view_self",
         "placement_cell.application.create")


def _cookie_client(stub_iam, token="tok-123"):
    stub_iam(make_session(modules=("placement_cell",), permissions=PERMS))
    client = APIClient()
    client.cookies["auth_token"] = token
    return client


def test_a_cookie_write_without_the_token_is_refused(stub_iam):
    client = _cookie_client(stub_iam)
    assert client.post("/api/v1/auth/logout").status_code == 403


def test_a_cookie_write_with_the_token_is_allowed(stub_iam):
    client = _cookie_client(stub_iam)
    response = client.post("/api/v1/auth/logout",
                           HTTP_X_CSRF_TOKEN=csrf.token_for("tok-123"))
    assert response.status_code == 200


def test_a_cookie_read_needs_no_token(stub_iam):
    """Safe methods are not the attack."""
    client = _cookie_client(stub_iam)
    assert client.get("/api/v1/me").status_code == 200


def test_a_header_credential_needs_no_token(stub_iam):
    """No ambient credential, so nothing to forge."""
    stub_iam(make_session(modules=("placement_cell",), permissions=PERMS))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-123")
    assert client.post("/api/v1/auth/logout").status_code == 200


def test_another_sessions_token_does_not_work(stub_iam):
    """Bound to one session, so a token from another account is useless."""
    client = _cookie_client(stub_iam, token="victim-session")
    response = client.post("/api/v1/auth/logout",
                           HTTP_X_CSRF_TOKEN=csrf.token_for("attacker-session"))
    assert response.status_code == 403


def test_the_token_is_handed_over_on_login_and_on_me(stub_iam):
    """A reloaded tab has to recover it without a second round trip."""
    fake = _cookie_client(stub_iam)
    fake.cookies.clear()
    stub_iam(make_session(modules=("placement_cell",), permissions=PERMS))

    login = APIClient().post("/api/v1/auth/login",
                             {"username": "u", "password": "p"}, format="json")
    assert login.json()["csrf_token"] == csrf.token_for("tok-123")

    client = _cookie_client(stub_iam)
    assert client.get("/api/v1/me").json()["csrf_token"] == csrf.token_for("tok-123")
