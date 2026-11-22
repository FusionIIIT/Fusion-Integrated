from datetime import datetime
from typing import Any
from django.db import transaction

from modules.pms.domain.validation import (
    ValidationError,
    validate_coinventor_shares,
)
from modules.pms.models.application import ApplicationStatus
from modules.pms.models.inventors import CoInventor, PriorArtReference
from modules.pms.selectors.scoping import get_application_scoped


@transaction.atomic
def update_inventors(
    app_id: int,
    applicant_user_id: int,
    inventors_data: list[dict[str, Any]],
    roles: list[str],
) -> list[CoInventor]:
    """Replace and validate co-inventor roster and ownership shares."""
    app = get_application_scoped(app_id, applicant_user_id, roles)

    if app.status != ApplicationStatus.DRAFT and app.status != ApplicationStatus.NEEDS_REVISION:
        raise ValidationError("Inventors can only be modified in Draft or Needs Revision status.")

    validate_coinventor_shares(inventors_data)

    app.inventors.all().delete()
    created = []
    for inv in inventors_data:
        obj = CoInventor.objects.create(
            application=app,
            user_id=inv["user_id"],
            inventor_name=inv.get("inventor_name", f"User #{inv['user_id']}"),
            affiliation=inv.get("affiliation", ""),
            contribution_percentage=inv["contribution_percentage"],
            agreement_signed=inv.get("agreement_signed", False),
        )
        created.append(obj)

    return created


@transaction.atomic
def sign_agreement(app_id: int, user_id: int, roles: list[str]) -> CoInventor:
    """Sign the co-inventor agreement for a patent application (BR-PMS-020)."""
    app = get_application_scoped(app_id, user_id, roles)
    try:
        inventor = app.inventors.get(user_id=user_id)
    except CoInventor.DoesNotExist as err:
        raise ValidationError(f"User #{user_id} is not listed as an inventor on application #{app_id}.") from err

    inventor.agreement_signed = True
    inventor.agreement_signed_at = datetime.now()
    inventor.signature_hash = f"sig_{app_id}_{user_id}_{int(datetime.now().timestamp())}"
    inventor.save(update_fields=["agreement_signed", "agreement_signed_at", "signature_hash", "updated_at"])
    return inventor


def add_prior_art(
    app_id: int,
    user_id: int,
    roles: list[str],
    title: str,
    citation_type: str,
    relevance_summary: str,
    publication_number: str = "",
    drive_link: str = "",
) -> PriorArtReference:
    """Attach prior art reference (UC-PMS-004)."""
    app = get_application_scoped(app_id, user_id, roles)
    return PriorArtReference.objects.create(
        application=app,
        title=title,
        citation_type=citation_type,
        relevance_summary=relevance_summary,
        publication_number_or_doi=publication_number,
        attached_file_drive_link=drive_link,
    )
