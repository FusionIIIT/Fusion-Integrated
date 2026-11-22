"""Consent tokens for external co-inventors who have no institute account (R1 decision).

The applicant asks for a token. The system emails it to the co-inventor, who confirms once.
The applicant never sees the raw token, and only its SHA-256 hash is stored.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.patents.models import CoInventor, CoInventorConsentToken
from modules.patents.selectors import scoping

TOKEN_TTL = timedelta(days=14)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_consent_token(actor, application_id: int, co_inventor_id: int) -> None:
    """Email a one-time consent link to an external co-inventor. The applicant gets no token."""
    app = scoping.applications_for(actor).filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")

    with transaction.atomic():
        ci = CoInventor.objects.select_for_update().filter(
            pk=co_inventor_id, application=app,
        ).first()
        if ci is None:
            raise NotFoundError("Co-inventor not found.")
        if ci.user_id is not None:
            raise ConflictError(
                "This co-inventor has an institute account; consent is recorded in the application."
            )

        now = timezone.now()
        # Revoke any earlier unused token, so only the newest link works.
        CoInventorConsentToken.objects.filter(
            co_inventor=ci, used_at__isnull=True,
        ).update(used_at=now)

        raw = secrets.token_urlsafe(32)
        CoInventorConsentToken.objects.create(
            co_inventor=ci,
            token_hash=_hash(raw),
            expires_at=now + TOKEN_TTL,
        )

    send_mail(
        subject="Consent requested for a patent application",
        message=(
            "You have been named as a co-inventor on patent application "
            f"{app.application_number}.\n"
            f"To record your consent, use this one-time code within 14 days: {raw}\n"
            "If you did not expect this message, do not use the code."
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[ci.email],
        fail_silently=False,
    )


def confirm_consent_token(raw: str) -> CoInventor:
    """Record consent for the co-inventor who holds this token. A token works once."""
    with transaction.atomic():
        token = (
            CoInventorConsentToken.objects.select_for_update()
            .select_related("co_inventor")
            .filter(token_hash=_hash(raw))
            .first()
        )
        now = timezone.now()
        if token is None or token.used_at is not None or token.expires_at < now:
            raise ConflictError("This consent link is invalid or has expired.")

        token.used_at = now
        token.save(update_fields=["used_at", "updated_at"])

        ci = token.co_inventor
        ci.consent_granted = True
        ci.consent_timestamp = now
        ci.save(update_fields=["consent_granted", "consent_timestamp", "updated_at"])
    return ci
