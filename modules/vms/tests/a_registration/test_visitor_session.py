"""Visitor email-OTP login (decision D-1)."""
import re
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms import auth
from modules.vms.models import Notification, Visitor, VisitorSession
from modules.vms.services import visitor_session as vs

pytestmark = pytest.mark.django_db


def _code(email="ravi@example.com"):
    vs.request_otp(email=email)
    n = Notification.objects.filter(topic="visitor.login_otp").latest("id")
    return re.search(r"\b(\d{6})\b", n.body).group(1)


def test_otp_is_queued_hashed_and_creates_the_visitor():
    code = _code()
    s = VisitorSession.objects.get()
    assert Visitor.objects.get().email == "ravi@example.com"
    assert code not in s.otp_hash and s.verified_at is None


def test_verify_returns_a_token_that_authenticates():
    code = _code()
    raw, session = vs.verify(email="Ravi@Example.com", otp=code)
    session.refresh_from_db()
    assert session.token_hash == auth.hash_token(raw) and session.verified_at
    assert session.otp_hash == ""
    assert session.expires_at > timezone.now() + timedelta(hours=11)


def test_wrong_code_is_401_and_counts_an_attempt():
    _code()
    from core.api.exceptions import AuthenticationFailedError
    with pytest.raises(AuthenticationFailedError):
        vs.verify(email="ravi@example.com", otp="000000")
    assert VisitorSession.objects.get().attempts == 1


def test_otp_attempt_lockout():
    code = _code()
    for _ in range(auth.MAX_OTP_ATTEMPTS):
        with pytest.raises(Exception):  # noqa: B017
            vs.verify(email="ravi@example.com", otp="000000" if code != "000000" else "111111")
    with pytest.raises(vs.TooManyAttempts):
        vs.verify(email="ravi@example.com", otp=code)   # even the right code is dead
    assert not VisitorSession.objects.filter(verified_at__isnull=False).exists()


def test_expired_code_is_rejected():
    code = _code()
    VisitorSession.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(Exception):  # noqa: B017
        vs.verify(email="ravi@example.com", otp=code)


def test_code_requests_are_limited_per_visitor():
    for _ in range(vs.MAX_OTP_REQUESTS_PER_HOUR):
        vs.request_otp(email="ravi@example.com")
    with pytest.raises(vs.TooManyAttempts):
        vs.request_otp(email="ravi@example.com")
