"""Visitor login endpoints."""
import re

import pytest

from modules.vms import auth
from modules.vms.models import Notification
from modules.vms.tests.a_registration.conftest import BASE

pytestmark = pytest.mark.django_db


def test_api_login_sets_httponly_cookie_and_csrf():
    from rest_framework.test import APIClient
    c = APIClient()
    assert c.post(BASE + "visitor/session/otp", {"email": "ravi@example.com"},
                  format="json").status_code == 202
    n = Notification.objects.get(topic="visitor.login_otp", channel="email")
    code = re.search(r"\b(\d{6})\b", n.body).group(1)
    r = c.post(BASE + "visitor/session/verify",
               {"email": "ravi@example.com", "otp": code}, format="json")
    assert r.status_code == 200 and r.json()["csrf_token"]
    assert r.cookies[auth.COOKIE_NAME]["httponly"]


def test_api_otp_endpoint_rejects_bad_email_and_is_throttled():
    from rest_framework.test import APIClient
    c = APIClient()
    assert c.post(BASE + "visitor/session/otp", {"email": "nope"},
                  format="json").status_code == 400
    codes = {c.post(BASE + "visitor/session/otp", {"email": f"a{i}@example.com"},
                    format="json").status_code for i in range(15)}
    assert 429 in codes
