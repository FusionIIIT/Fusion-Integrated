"""Visitor email-OTP login (decision D-1, VMS-CFR-019).

`request_otp` mails a 6-digit code (through the notification outbox, topic
``visitor.login_otp``); `verify` swaps a correct code for the opaque session
token that `auth.VisitorSessionAuthentication` resolves. Only hashes are stored.
A code allows `MAX_OTP_ATTEMPTS` guesses, then the row is dead.
"""
from __future__ import annotations

import hmac
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import AuthenticationFailedError, BadRequestError, DomainError
from modules.vms.auth import (
    MAX_OTP_ATTEMPTS,
    SESSION_TTL_HOURS,
    hash_token,
    make_session_token,
)
from modules.vms.models import Visitor, VisitorSession
from modules.vms.services.common import audit, notify

OTP_TTL_MINUTES = 10
#: At most this many codes per visitor per hour, on top of the per-IP throttle.
MAX_OTP_REQUESTS_PER_HOUR = 5


class TooManyAttempts(DomainError):
    code = "too_many_attempts"
    status_code = 429


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_otp(otp: str) -> str:
    return hash_token(f"otp:{otp}")


def request_otp(*, email: str) -> None:
    """Issue a code for `email`. Always succeeds from the caller's side, so the
    response never reveals whether the address was known."""
    email = normalise_email(email)
    if not email or "@" not in email:
        raise BadRequestError("A valid email address is required.", code="invalid_email")
    now = timezone.now()
    with transaction.atomic():
        visitor = (Visitor.objects.select_for_update()
                   .filter(email__iexact=email, is_anonymized=False)
                   .order_by("id").first())
        if visitor is None:
            visitor = Visitor.objects.create(email=email, full_name="")
        recent = VisitorSession.objects.filter(
            visitor=visitor, created_at__gte=now - timedelta(hours=1)).count()
        if recent >= MAX_OTP_REQUESTS_PER_HOUR:
            raise TooManyAttempts("Too many codes requested. Try again later.")
        otp = f"{secrets.randbelow(10**6):06d}"
        session = VisitorSession.objects.create(
            visitor=visitor,
            token_hash=hash_token(make_session_token()),   # placeholder until verified
            otp_hash=_hash_otp(otp),
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES))
        audit.record(actor=None, action="vms.visitor_session.otp_requested",
                     entity=session)
        notify.enqueue(
            topic="visitor.login_otp", dedupe_key=f"visitor-otp:{session.pk}",
            subject="Your campus visit verification code",
            body=f"Your verification code is {otp}. It expires in "
                 f"{OTP_TTL_MINUTES} minutes.",
            visitor=visitor, channels=("email",))


def verify(*, email: str, otp: str) -> tuple[str, VisitorSession]:
    """Exchange a correct code for a session token. Returns (raw_token, session)."""
    email = normalise_email(email)
    now = timezone.now()
    with transaction.atomic():
        session = (VisitorSession.objects.select_for_update()
                   .filter(visitor__email__iexact=email, verified_at__isnull=True,
                           expires_at__gt=now)
                   .exclude(otp_hash="").order_by("-id").first())
        if session is None:
            raise AuthenticationFailedError("Invalid or expired code.")
        if session.attempts >= MAX_OTP_ATTEMPTS:
            raise TooManyAttempts("Too many wrong codes. Request a new one.")
        session.attempts += 1
        if hmac.compare_digest(session.otp_hash, _hash_otp(str(otp or "").strip())):
            raw = make_session_token()
            session.token_hash = hash_token(raw)
            session.otp_hash = ""
            session.verified_at = now
            session.expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
            session.save(update_fields=["token_hash", "otp_hash", "verified_at",
                                        "expires_at", "attempts"])
            audit.record(actor=None, action="vms.visitor_session.verified",
                         entity=session)
            return raw, session
        session.save(update_fields=["attempts"])
    # The attempt counter has committed; now refuse.
    raise AuthenticationFailedError("Invalid or expired code.")
