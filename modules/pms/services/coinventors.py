"""PMS Co-Inventor and Agreement Management service (CFR-PMS-016)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.entities import validate_coinventor_shares
from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.models import CoInventor, PatentApplication
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def update_coinventors(
    *,
    application_id: int,
    actor_user_id: int,
    coinventors_data: list[dict[str, Any]],
) -> list[CoInventor]:
    """Update co-inventors and ownership percentages (BR-PMS-073, BR-PMS-074)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Pre-filing check: cannot edit co-inventors after filing
        if app.status in ("filed", "granted", "withdrawn", "expired"):
            raise PreconditionNotMetError("Cannot modify co-inventors after application is filed.")

        shares = [Decimal(str(c.get("ownership_percentage", "0"))) for c in coinventors_data]
        validate_coinventor_shares(shares)

        # Clear existing co-inventors and re-create
        app.coinventors.all().delete()
        created = []
        for c in coinventors_data:
            inv = CoInventor.objects.create(
                application=app,
                user_id=c.get("user_id"),
                name=c.get("name", "").strip(),
                email=c.get("email", "").strip(),
                department=c.get("department", "").strip(),
                ownership_percentage=Decimal(str(c.get("ownership_percentage", "0"))),
                consent_given=c.get("consent_given", False),
                agreement_signed=c.get("agreement_signed", False),
                electronic_signature=c.get("electronic_signature", ""),
            )
            created.append(inv)

        log_audit(
            application=app,
            actor_user_id=actor_user_id,
            action_type="coinventors_updated",
            details={"coinventor_count": len(created)},
        )

        enqueue_notification(
            topic="inventor.changed",
            dedupe_key=f"pms:coinv:updated:{app.id}:{timezone.now().timestamp()}",
            subject=f"PMS: Inventor Details Updated for {app.application_no}",
            body=f"Co-inventor and ownership details for '{app.title}' have been updated.",
            recipient_user_id=app.applicant_user_id,
        )

    return created


def record_consent_and_agreement(
    *,
    coinventor_id: int,
    user_id: int,
    consent_given: bool = True,
    agreement_signed: bool = True,
    electronic_signature: str = "",
) -> CoInventor:
    """Record inventor agreement and electronic signature (BR-PMS-075, 076, 077, 078)."""
    with transaction.atomic():
        coinv = CoInventor.objects.select_for_update().get(pk=coinventor_id)
        if coinv.user_id and coinv.user_id != user_id:
            raise PreconditionNotMetError("You are not authorized to sign for this co-inventor.")

        coinv.consent_given = consent_given
        coinv.agreement_signed = agreement_signed
        coinv.electronic_signature = electronic_signature.strip()
        coinv.signed_at = timezone.now() if agreement_signed else None
        coinv.save()

        log_audit(
            application=coinv.application,
            actor_user_id=user_id,
            action_type="coinventor_consent_recorded",
            details={
                "coinventor_id": coinv.id,
                "name": coinv.name,
                "consent": consent_given,
                "signed": agreement_signed,
            },
        )

    return coinv


def record_withdrawal_consent(
    *,
    coinventor_id: int,
    user_id: int,
    consent_given: bool = True,
) -> CoInventor:
    """Record co-inventor consent for withdrawal (BR-PMS-070)."""
    with transaction.atomic():
        coinv = CoInventor.objects.select_for_update().get(pk=coinventor_id)
        if coinv.user_id and coinv.user_id != user_id:
            raise PreconditionNotMetError("You are not authorized to consent for this co-inventor.")

        coinv.withdrawal_consent_given = consent_given
        coinv.save(update_fields=["withdrawal_consent_given", "updated_at"])

        log_audit(
            application=coinv.application,
            actor_user_id=user_id,
            action_type="coinventor_withdrawal_consent_recorded",
            details={"coinventor_id": coinv.id, "consent": consent_given},
        )

    return coinv
