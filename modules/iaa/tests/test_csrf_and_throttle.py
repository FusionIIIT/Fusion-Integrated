"""A cookie-authenticated write needs the CSRF token; writes and exports are throttled (HTTP 429)."""
import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from modules.iaa import registry
from modules.iaa.domain import roles
from modules.iaa.tests.helpers import FACULTY, USERS, api_client

pytestmark = pytest.mark.django_db

B = "/api/v1/iaa"
COOKIE = settings.IAM_AUTH_COOKIE_NAME


def _cookie_client(stub_iam, token="tok-iaa"):
    stub_iam(make_session(user_id=101, kind="employee", roles=(FACULTY,), active_role=FACULTY,
                          permissions=registry.ROLE_GRANTS[FACULTY], modules=("iaa",)),
             users=USERS)
    client = APIClient()
    client.cookies[COOKIE] = token
    return client


def test_a_cookie_write_without_the_token_is_refused_and_changes_nothing(
        stub_iam, people, configured):
    client = _cookie_client(stub_iam)
    assert client.post(f"{B}/records", {"kind": "expense"}, format="json").status_code == 403
    assert client.get(f"{B}/records").json()["results"] == []


def test_a_cookie_write_with_the_sessions_token_is_allowed(stub_iam, people, configured):
    client = _cookie_client(stub_iam)
    made = client.post(f"{B}/records", {"kind": "expense"}, format="json",
                       HTTP_X_CSRF_TOKEN=csrf.token_for("tok-iaa"))
    assert made.status_code == 201


def test_another_sessions_token_is_refused_on_a_write(stub_iam, people, configured):
    client = _cookie_client(stub_iam, token="victim")
    response = client.post(f"{B}/records", {"kind": "expense"}, format="json",
                           HTTP_X_CSRF_TOKEN=csrf.token_for("attacker"))
    assert response.status_code == 403


def test_a_cookie_read_needs_no_token(stub_iam, people, configured):
    assert _cookie_client(stub_iam).get(f"{B}/records").status_code == 200


def test_the_sixth_export_in_an_hour_is_throttled(stub_iam, people, configured):
    cache.clear()
    finance = api_client(stub_iam, 201, roles.FINANCE)
    codes = [finance.get(f"{B}/reports/export").status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429
    cache.clear()


def test_the_sixty_first_write_in_a_minute_is_throttled_and_reads_are_not(
        stub_iam, people, configured):
    client = api_client(stub_iam, 101, FACULTY)
    codes = [client.post(f"{B}/records", {}, format="json").status_code for _ in range(61)]
    assert codes[:60] == [400] * 60 and codes[60] == 429
    assert client.get(f"{B}/records").status_code == 200
    assert api_client(stub_iam, 102, FACULTY).post(
        f"{B}/records", {}, format="json").status_code == 400      # another caller, own allowance
