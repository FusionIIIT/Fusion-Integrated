"""The identity boundary: this service trusts IAM and nothing else."""
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from fusion_auth.client import IamUnavailable

#: Read, not pinned: the name is configurable and must not
#: collide with the console's.
COOKIE = settings.IAM_AUTH_COOKIE_NAME

pytestmark = pytest.mark.django_db


def test_no_credentials_is_401():
    r = APIClient().get("/api/v1/me")
    assert r.status_code == 401


def test_valid_token_resolves_a_principal(stub_iam):
    stub_iam(make_session(user_id=42, modules=("placement_cell",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    r = c.get("/api/v1/me")
    assert r.status_code == 200
    assert r.json()["user"]["id"] == 42


def test_iam_rejecting_the_token_is_401(stub_iam):
    stub_iam(None)                      # IAM says: not a valid session
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token nope")
    assert c.get("/api/v1/me").status_code == 401


def test_iam_being_down_is_not_a_silent_allow(stub_iam, monkeypatch):
    fake = stub_iam(make_session())

    def boom(**kw):
        raise IamUnavailable("connection refused")

    monkeypatch.setattr(fake, "resolve_session", boom)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    r = c.get("/api/v1/me")
    assert r.status_code == 401                       # fail closed
    assert "unavailable" in r.json()["error"]["message"].lower()


def test_error_envelope_carries_a_request_id():
    r = APIClient().get("/api/v1/me")
    body = r.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details", "request_id"}
    assert body["error"]["request_id"] == r["X-Request-ID"]


def test_module_grant_gates_the_endpoint(stub_iam):
    """A module the caller was not granted is refused even with the permission."""
    stub_iam(make_session(permissions=("placement_cell.job_posting.view",),
                          modules=()))                      # no module grant
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert c.get("/api/v1/placement/postings").status_code == 403


def test_module_grant_plus_permission_passes(stub_iam):
    stub_iam(make_session(permissions=("placement_cell.job_posting.view",),
                          modules=("placement_cell",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    assert c.get("/api/v1/placement/postings").status_code == 200


def test_login_forwards_to_iam_and_sets_an_httponly_cookie(stub_iam):
    stub_iam(make_session())
    r = APIClient().post("/api/v1/auth/login",
                         {"username": "asha", "password": "x"}, format="json")
    assert r.status_code == 200
    c = r.cookies[COOKIE]
    assert c.value == "tok-123"
    assert c["httponly"] is True          # never readable from JavaScript
    assert c["samesite"] == "Lax"


def test_bad_credentials_do_not_reveal_whether_the_user_exists(stub_iam):
    fake = stub_iam(None)
    fake.login_result = None
    a = APIClient().post("/api/v1/auth/login",
                         {"username": "asha", "password": "wrong"}, format="json")
    b = APIClient().post("/api/v1/auth/login",
                         {"username": "nobody-at-all", "password": "wrong"},
                         format="json")
    # 401, not 422: 422 would say the request was malformed and hide auth outages.
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["message"] == b.json()["error"]["message"]
    assert a.json()["error"]["code"] == "invalid_credentials"


def test_login_when_iam_is_down_is_503_not_401(stub_iam):
    fake = stub_iam(None)
    fake.login_error = IamUnavailable("connection refused")
    r = APIClient().post("/api/v1/auth/login",
                         {"username": "a", "password": "b"}, format="json")
    # 503, not 401: the credentials may be fine and the problem is ours.
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "iam_unavailable"


def test_logout_clears_the_cookie(stub_iam):
    stub_iam(make_session())
    c = APIClient()
    c.cookies[COOKIE] = "tok-123"
    r = c.post("/api/v1/auth/logout",
               HTTP_X_CSRF_TOKEN=csrf.token_for("tok-123"))
    assert r.status_code == 200
    assert r.cookies[COOKIE].value == ""


def test_cookie_session_is_forwarded_as_a_header_not_a_replayed_cookie(stub_iam):
    """Regression: the platform's cookie name and the IAM's cookie name are
    different. Replaying the cookie meant the IAM never saw a credential and
    every request after login 401'd."""
    fake = stub_iam(make_session(user_id=7))
    c = APIClient()
    c.cookies[COOKIE] = "tok-from-cookie"
    r = c.get("/api/v1/me")
    assert r.status_code == 200
    assert ("resolve_session", "tok-from-cookie") in fake.calls
