"""Application submission, revision and withdrawal services (BW-PMS-01, 02, 16)."""

from __future__ import annotations

import decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_APPLICANT,
    STATUS_DRAFT,
    STATUS_RESUBMITTED,
    STATUS_SUBMITTED,
    STATUS_WITHDRAWN,
)
from modules.pms.domain.exceptions import DeadlineExpiredError, ValidationError
from modules.pms.domain.rules import (
    check_withdrawal_eligibility,
    validate_application_submission_fields,
    validate_inventor_shares,
)
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    ApplicationWithdrawal,
    Inventor,
    InventorAgreement,
    PatentApplication,
)
from modules.pms.services.audit import record_audit_event


def generate_application_number() -> str:
    """Generate next sequential institutional application number (e.g., PMS-2026-0001)."""
    year = timezone.now().year
    prefix = f"PMS-{year}-"
    last_app = (
        PatentApplication.objects.filter(application_no__startswith=prefix).order_by("-id").first()
    )
    if not last_app:
        seq = 1
    else:
        try:
            seq = int(last_app.application_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = last_app.id + 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def submit_patent_application(
    user_id: int,
    title: str,
    abstract: str,
    description: str,
    claims: str,
    domain: str,
    filing_type: str = "provisional",
    keywords: str = "",
    inventors_data: list[dict[str, Any]] | None = None,
    preferred_attorney_id: int | None = None,
) -> PatentApplication:
    """Submit a new patent application (UC-PMS-001, BW-PMS-01)."""
    # 1. Validate required fields
    validate_application_submission_fields(title, abstract, description, claims, domain)

    # 2. Validate inventors & percentage shares
    if not inventors_data:
        # Default lead inventor is the applicant
        inventors_data = [
            {
                "name": f"User {user_id}",
                "email": f"user{user_id}@institute.ac.in",
                "department": domain,
                "is_lead": True,
                "share_percentage": decimal.Decimal("100.00"),
                "user_id": user_id,
            }
        ]

    shares = [
        inv.get("share_percentage") or inv.get("percentage_share")
        for inv in inventors_data
    ]
    validate_inventor_shares(shares)

    # 3. State transition validation: Draft -> Submitted
    validate_transition(STATUS_DRAFT, STATUS_SUBMITTED, ACTOR_APPLICANT)

    # 4. Create application
    app_no = generate_application_number()
    app = PatentApplication.objects.create(
        user_id=user_id,
        application_no=app_no,
        title=title.strip(),
        abstract=abstract.strip(),
        description=description.strip(),
        claims=claims.strip(),
        domain=domain.strip(),
        filing_type=filing_type,
        status=STATUS_SUBMITTED,
        preferred_attorney_id=preferred_attorney_id,
        submitted_at=timezone.now(),
    )

    # 5. Create inventors
    for inv in inventors_data:
        share = inv.get("share_percentage") or inv.get("percentage_share")
        is_lead = inv.get("is_lead") if "is_lead" in inv else inv.get("is_primary", False)
        Inventor.objects.create(
            application=app,
            user_id=inv.get("user_id"),
            name=inv["name"].strip(),
            email=inv["email"].strip(),
            department=inv.get("department", "").strip(),
            is_lead=is_lead,
            share_percentage=decimal.Decimal(str(share)),
            consent_status="granted" if inv.get("user_id") == user_id else "pending",
            consent_date=timezone.now() if inv.get("user_id") == user_id else None,
        )

    # 6. Initialize default institutional inventor agreement draft
    InventorAgreement.objects.create(
        application=app,
        agreement_type="institutional_declaration",
        status="circulated",
    )

    # 7. Audit log
    record_audit_event(
        application=app,
        user_id=user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="submit_application",
        previous_state=STATUS_DRAFT,
        new_state=STATUS_SUBMITTED,
        details={"application_no": app.application_no, "domain": app.domain},
    )

    return app


@transaction.atomic
def revise_and_resubmit_application(
    application: PatentApplication,
    user_id: int,
    title: str | None = None,
    abstract: str | None = None,
    description: str | None = None,
    claims: str | None = None,
    revision_notes: str = "",
) -> PatentApplication:
    """Revise and resubmit an application under revision/rejection (UC-PMS-005, BW-PMS-02)."""
    # Verify revision deadline
    if application.revision_deadline and timezone.now() > application.revision_deadline:
        raise DeadlineExpiredError(
            "60-day revision period has expired. Application cannot be resubmitted.",
            rule_id="BR-PMS-035",
        )

    validate_transition(application.status, STATUS_RESUBMITTED, ACTOR_APPLICANT)

    prev_status = application.status
    if title:
        application.title = title.strip()
    if abstract:
        application.abstract = abstract.strip()
    if description:
        application.description = description.strip()
    if claims:
        application.claims = claims.strip()

    application.status = STATUS_RESUBMITTED
    application.save()

    record_audit_event(
        application=application,
        user_id=user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="resubmit_revision",
        previous_state=prev_status,
        new_state=STATUS_RESUBMITTED,
        details={"notes": revision_notes},
    )

    return application


@transaction.atomic
def withdraw_patent_application(
    application: PatentApplication,
    user_id: int,
    reason: str,
) -> PatentApplication:
    """Withdraw a patent application before filing (UC-PMS-006, BW-PMS-16, BR-PMS-067..070)."""
    check_withdrawal_eligibility(application.status)
    validate_transition(application.status, STATUS_WITHDRAWN, ACTOR_APPLICANT)

    if not reason or not reason.strip():
        raise ValidationError("Withdrawal reason must be provided.", rule_id="BR-PMS-069")

    prev_status = application.status
    application.status = STATUS_WITHDRAWN
    application.save()

    ApplicationWithdrawal.objects.create(
        application=application,
        user_id=user_id,
        reason=reason.strip(),
        co_inventors_notified=True,
    )

    record_audit_event(
        application=application,
        user_id=user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="withdraw_application",
        previous_state=prev_status,
        new_state=STATUS_WITHDRAWN,
        details={"reason": reason.strip()},
    )

    return application
