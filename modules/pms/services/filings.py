"""PMS External Filing and Patent Office Communication service.

Enforces business rules BR-PMS-020, 055, 056, 059, 060, 078, 128, 138, 142.
"""

from __future__ import annotations

import datetime
from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from modules.pms.domain.entities import validate_filing_preconditions
from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import (
    PatentApplication,
    PostGrantMaintenance,
)
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def record_external_filing(
    *,
    application_id: int,
    attorney_user_id: int,
    external_filing_id: str,
    external_filing_date: datetime.date,
    filing_confirmation: str,
    is_international: bool = False,
    international_justification: str = "",
) -> PatentApplication:
    """Record external domestic or international patent filing (UC-PMS-013, CFR-PMS-012)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        # Precondition verification (BR-PMS-020, 056, 078, 128)
        budget = getattr(app, "budget", None)
        budget_status = budget.status if budget else "draft"
        all_agreements = not app.coinventors.filter(agreement_signed=False).exists()

        validate_filing_preconditions(
            status=app.status,
            budget_status=budget_status,
            all_agreements_complete=all_agreements,
            is_international=is_international,
            international_justification=international_justification,
        )

        validate_transition(app.status, PatentApplicationStatus.FILED, actor_role="Attorney")
        prev_status = app.status

        app.external_filing_id = external_filing_id.strip()
        app.external_filing_date = external_filing_date
        app.filing_confirmation = filing_confirmation.strip()
        app.is_international = is_international
        if is_international:
            app.international_justification = international_justification.strip()
        app.format_validated = True
        app.status = PatentApplicationStatus.FILED.value
        app.save()

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="external_patent_filed",
            from_state=prev_status,
            to_state=app.status,
            details={
                "external_filing_id": external_filing_id,
                "external_filing_date": str(external_filing_date),
                "is_international": is_international,
            },
        )

        enqueue_notification(
            topic="patent.filed",
            dedupe_key=f"pms:patent:filed:{app.id}",
            subject=f"PMS: Patent Application Filed ({app.application_no})",
            body=f"Application '{app.title}' has been officially filed. Filing ID: {external_filing_id}.",
            recipient_user_id=app.applicant_user_id,
        )

    return app


def record_patent_grant(
    *,
    application_id: int,
    attorney_user_id: int,
    patent_number: str,
    grant_date: datetime.date,
) -> PatentApplication:
    """Record patent grant and initialize maintenance schedule (UC-PMS-014, CFR-PMS-013, BR-PMS-059, 060)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        if app.status not in (
            PatentApplicationStatus.FILED.value,
            PatentApplicationStatus.RESPONSE_SUBMITTED.value,
        ):
            raise PreconditionNotMetError(
                f"Cannot grant patent for application in status '{app.status}'. Must be Filed or Response Submitted."
            )

        validate_transition(app.status, PatentApplicationStatus.GRANTED, actor_role="Attorney")
        prev_status = app.status

        app.patent_number = patent_number.strip()
        app.grant_date = grant_date
        app.status = PatentApplicationStatus.GRANTED.value
        app.save()

        # Schedule first maintenance cycle (BR-PMS-060: 3rd year from grant/filing)
        first_fee_due = grant_date + timedelta(days=365 * 3)
        PostGrantMaintenance.objects.create(
            application=app,
            cycle_number=1,
            fee_due_date=first_fee_due,
            fee_amount=Decimal("5000.00"),
            maintenance_status="scheduled",
        )

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="patent_granted",
            from_state=prev_status,
            to_state=app.status,
            details={
                "patent_number": patent_number,
                "grant_date": str(grant_date),
                "first_maintenance_due": str(first_fee_due),
            },
        )

        enqueue_notification(
            topic="patent.granted",
            dedupe_key=f"pms:patent:granted:{app.id}",
            subject=f"PMS: Patent Granted! ({patent_number})",
            body=f"Congratulations! Patent '{app.title}' has been granted with Patent Number: {patent_number}.",
            recipient_user_id=app.applicant_user_id,
        )

    return app
