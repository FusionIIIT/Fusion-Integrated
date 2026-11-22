from datetime import datetime
from typing import Any
from django.db import transaction

from modules.pms.domain.state_machine import PatentStateMachine
from modules.pms.domain.validation import (
    validate_application_data,
    validate_coinventor_shares,
)
from modules.pms.models.application import ApplicationStatus, FilingType, PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.models.budget import PatentBudget
from modules.pms.models.inventors import CoInventor


def generate_application_no() -> str:
    """Generate human-readable institutional tracking number (e.g. PMS-2026-0042)."""
    year = datetime.now().year
    count = PatentApplication.objects.count() + 1
    return f"PMS-{year}-{count:04d}"


@transaction.atomic
def create_draft(
    applicant_user_id: int,
    title: str,
    abstract: str = "",
    detailed_description: str = "",
    claims: str = "",
    field_of_invention: str = "",
    filing_type: str = FilingType.PROVISIONAL,
    inventors: list[dict[str, Any]] | None = None,
) -> PatentApplication:
    """Create a new patent application in Draft status."""
    app_no = generate_application_no()
    app = PatentApplication.objects.create(
        application_no=app_no,
        title=title,
        abstract=abstract,
        detailed_description=detailed_description,
        claims=claims,
        field_of_invention=field_of_invention,
        applicant_user_id=applicant_user_id,
        status=ApplicationStatus.DRAFT,
        filing_type=filing_type,
    )

    # Initial budget shell
    PatentBudget.objects.create(application=app)

    # Attach primary inventor
    CoInventor.objects.create(
        application=app,
        user_id=applicant_user_id,
        inventor_name=f"User #{applicant_user_id}",
        contribution_percentage=100.00 if not inventors else 0.00,
        agreement_signed=True,
        agreement_signed_at=datetime.now(),
    )

    # Process additional co-inventors if supplied
    if inventors:
        validate_coinventor_shares(inventors)
        # Clear default and recreate
        app.inventors.all().delete()
        for inv in inventors:
            CoInventor.objects.create(
                application=app,
                user_id=inv["user_id"],
                inventor_name=inv.get("inventor_name", f"User #{inv['user_id']}"),
                affiliation=inv.get("affiliation", ""),
                contribution_percentage=inv["contribution_percentage"],
                agreement_signed=inv["user_id"] == applicant_user_id,
            )

    PatentAuditEvent.objects.create(
        application=app,
        event_name="CREATE_DRAFT",
        from_status="",
        to_status=ApplicationStatus.DRAFT,
        actor_user_id=applicant_user_id,
        payload={"title": title, "filing_type": filing_type},
    )

    return app


@transaction.atomic
def submit_application(
    app_id: int,
    actor_user_id: int,
    actor_roles: list[str],
) -> PatentApplication:
    """Submit application for institutional scrutiny and review."""
    from modules.pms.selectors.scoping import get_application_scoped

    app = get_application_scoped(app_id, actor_user_id, actor_roles)

    # Validate mandatory submission data (BR-PMS-017)
    validate_application_data({
        "title": app.title,
        "abstract": app.abstract,
        "claims": app.claims,
    })

    # Validate state transition
    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="SUBMIT",
        actor_roles=actor_roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="SUBMIT",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=actor_user_id,
        payload={"submitted_at": str(datetime.now())},
    )

    return app


@transaction.atomic
def withdraw_application(
    app_id: int,
    actor_user_id: int,
    actor_roles: list[str],
    reason: str = "",
) -> PatentApplication:
    """Withdraw patent application prior to external filing (BW-PMS-16)."""
    from modules.pms.selectors.scoping import get_application_scoped

    app = get_application_scoped(app_id, actor_user_id, actor_roles)

    next_state = PatentStateMachine.get_next_state(
        app.status,
        event="WITHDRAW",
        actor_roles=actor_roles,
    )

    old_status = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    PatentAuditEvent.objects.create(
        application=app,
        event_name="WITHDRAW",
        from_status=old_status,
        to_status=next_state,
        actor_user_id=actor_user_id,
        payload={"reason": reason},
    )

    return app
