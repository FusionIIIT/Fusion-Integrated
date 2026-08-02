"""Recruiter accounts: invitation, acceptance, sign-in (PC-UC-014, PC-BR-007).

The module's externally-reachable surface, so: invitation only with no
self-service signup; one identical failure message and comparable work on
every path, so nothing can be enumerated; progressive lockout per address; and
invitation tokens hashed at rest.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.placement.authentication import hash_token, make_session_key
from modules.placement.models import (
    Company,
    RecruiterAccount,
    RecruiterLoginAttempt,
    RecruiterSession,
)
from modules.placement.services import notifications

INVITE_TTL_HOURS = 72
SESSION_TTL_HOURS = 8
MIN_PASSWORD_LENGTH = 12

# (failures within the window, lockout minutes). None = needs an admin.
LOCKOUT_TIERS = ((15, None), (10, 30), (8, 5), (5, 1))
LOCKOUT_WINDOW_MINUTES = 60

# Equalises response time on an unknown address.
_DUMMY_HASH = make_password("dummy-password-for-timing-equalisation")

GENERIC_FAILURE = "Incorrect email or password."


class Locked(Exception):
    def __init__(self, minutes: int | None):
        self.minutes = minutes
        super().__init__("Account temporarily locked.")


# -- Invitation ----------------------------------------------------------------
@transaction.atomic
def invite(*, company_id: int, email: str, full_name: str = "",
           invited_by_user_id: int) -> tuple[RecruiterAccount, str]:
    """Returns (account, raw_token). The token is shown once; only its digest
    is stored."""
    email = email.strip().lower()
    company = Company.objects.filter(pk=company_id).first()
    if company is None:
        raise NotFoundError("No such company.")
    if not company.can_operate:
        raise ConflictError(
            "This company is not approved, so recruiters cannot be invited yet.",
            code="company_not_approved")

    existing = RecruiterAccount.objects.filter(email=email).first()
    if existing and existing.company_id != company_id:
        # One address, one company, or it becomes a cross-company data path.
        raise ConflictError("That address already belongs to another company.",
                            code="email_taken")

    raw = secrets.token_urlsafe(32)
    account = existing or RecruiterAccount(company=company, email=email)
    account.full_name = full_name or account.full_name
    account.invite_token_hash = hash_token(raw)
    account.invite_expires_at = timezone.now() + timedelta(hours=INVITE_TTL_HOURS)
    account.invited_by_user_id = invited_by_user_id
    account.is_active = True
    account.save()

    notifications.enqueue(
        topic="recruiter.invited",
        dedupe_key=f"recruiter.invited:{account.pk}:{account.invite_token_hash[:16]}",
        recipient_email=email,
        subject=f"You have been invited to the {company.name} recruiter portal",
        body=("An invitation has been created for you. It expires in "
              f"{INVITE_TTL_HOURS} hours."),
        payload={"company": company.name, "expires_hours": INVITE_TTL_HOURS},
    )
    return account, raw


@transaction.atomic
def accept_invite(*, token: str, password: str) -> RecruiterAccount:
    """Set the password and activate the account."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ConflictError(
            f"Choose a password of at least {MIN_PASSWORD_LENGTH} characters.",
            code="password_too_short")

    account = (RecruiterAccount.objects
               .select_for_update()
               .select_related("company")
               .filter(invite_token_hash=hash_token(token or ""),
                       is_active=True).first())
    # One message, so a guessed token is indistinguishable from an expired one.
    if account is None or not account.invite_expires_at \
            or account.invite_expires_at <= timezone.now():
        raise PermissionDeniedError("This invitation is not valid.",
                                    code="invite_invalid")
    if not account.company.can_operate:
        raise PermissionDeniedError("This invitation is not valid.",
                                    code="invite_invalid")

    account.password_hash = make_password(password)
    account.accepted_at = timezone.now()
    account.invite_token_hash = ""            # single use
    account.invite_expires_at = None
    account.save(update_fields=["password_hash", "accepted_at",
                                "invite_token_hash", "invite_expires_at",
                                "updated_at"])
    return account


# -- Sign-in -------------------------------------------------------------------
def _recent_failures(email: str) -> int:
    since = timezone.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    return (RecruiterLoginAttempt.objects
            .filter(email=email, at__gte=since)
            .exclude(outcome="success").count())


def check_lockout(email: str) -> None:
    fails = _recent_failures(email)
    for threshold, minutes in LOCKOUT_TIERS:
        if fails >= threshold:
            if minutes is None:
                raise Locked(None)
            last = (RecruiterLoginAttempt.objects.filter(email=email)
                    .exclude(outcome="success").order_by("-at").first())
            if last and timezone.now() < last.at + timedelta(minutes=minutes):
                raise Locked(minutes)
            return
    return


def sign_in(*, email: str, password: str, ip: str | None = None) -> RecruiterSession:
    """Verify credentials and open a session.

    Raises PermissionDeniedError with one identical message for every failure.
    """
    email = (email or "").strip().lower()
    check_lockout(email)

    account = (RecruiterAccount.objects.select_related("company")
               .filter(email=email).first())

    def _fail(outcome: str):
        RecruiterLoginAttempt.objects.create(email=email, ip=ip, outcome=outcome)
        raise PermissionDeniedError(GENERIC_FAILURE, code="invalid_credentials")

    if account is None:
        check_password(password, _DUMMY_HASH)       # equalise response time
        _fail("unknown_account")
    if not account.can_sign_in:
        check_password(password, _DUMMY_HASH)
        _fail("inactive")
    if not account.company.can_operate:
        check_password(password, _DUMMY_HASH)
        _fail("company_not_approved")
    if not check_password(password or "", account.password_hash):
        _fail("bad_password")

    RecruiterLoginAttempt.objects.create(email=email, ip=ip, outcome="success")

    # Only the digest is stored. The raw value goes out in the cookie and is
    # never recoverable from the table, so a dump yields no live session — the
    # lookup is by digest and costs one sha256.
    raw = make_session_key()
    session = RecruiterSession.objects.create(
        key=hash_token(raw), account=account, ip=ip,
        expires_at=timezone.now() + timedelta(hours=SESSION_TTL_HOURS),
    )
    session.raw_key = raw               # in memory only, for the caller
    RecruiterAccount.objects.filter(pk=account.pk).update(
        last_login_at=timezone.now())
    return session


def sign_out(*, session_key: str) -> None:
    RecruiterSession.objects.filter(key=hash_token(session_key),
                                    revoked_at__isnull=True) \
        .update(revoked_at=timezone.now())


def revoke_all(*, account_id: int) -> int:
    """For a deactivated account or an un-approved company."""
    return (RecruiterSession.objects
            .filter(account_id=account_id, revoked_at__isnull=True)
            .update(revoked_at=timezone.now()))
