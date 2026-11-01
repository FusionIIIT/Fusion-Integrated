"""PMS Licensing and Technology Transfer Tracking service.

Enforces business rules BR-PMS-088, BR-PMS-091, and CFR-PMS-019.
"""

from __future__ import annotations

from django.db import transaction

from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.models import LicensingRequest, PatentApplication
from modules.pms.services.audit import log_audit


def submit_licensing_request(
    *,
    application_id: int,
    applicant_user_id: int,
    licensee_name: str,
    request_type: str,
    commercial_terms: str,
) -> LicensingRequest:
    """Submit a patent licensing or technology-transfer request (UC-PMS-020, CFR-PMS-019)."""
    if not licensee_name or not licensee_name.strip():
        raise PreconditionNotMetError("Licensee name is required.")
    if not commercial_terms or not commercial_terms.strip():
        raise PreconditionNotMetError("Commercial terms are required.")

    with transaction.atomic():
        app = PatentApplication.objects.get(pk=application_id)
        req = LicensingRequest.objects.create(
            application=app,
            requested_by_user_id=applicant_user_id,
            licensee_name=licensee_name.strip(),
            request_type=request_type.strip(),
            commercial_terms=commercial_terms.strip(),
            status="submitted",
            is_confidential=True,
        )

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="licensing_request_submitted",
            details={
                "request_id": req.id,
                "licensee": licensee_name,
                "request_type": request_type,
            },
        )

    return req


def review_licensing_request(
    *,
    request_id: int,
    director_user_id: int,
    status: str,  # "under_review", "negotiating", "agreement_recorded", "rejected"
    negotiation_notes: str = "",
    agreement_reference: str = "",
) -> LicensingRequest:
    """Director reviews and tracks licensing negotiations (UC-PMS-021, CFR-PMS-019)."""
    valid_statuses = ("under_review", "negotiating", "agreement_recorded", "rejected")
    if status not in valid_statuses:
        raise PreconditionNotMetError(
            f"Invalid licensing status '{status}'. Must be one of: {valid_statuses}"
        )

    with transaction.atomic():
        req = LicensingRequest.objects.select_for_update().get(pk=request_id)
        req.status = status
        if negotiation_notes:
            req.negotiation_notes = negotiation_notes.strip()
        if agreement_reference:
            req.agreement_reference = agreement_reference.strip()
        req.save()

        log_audit(
            application=req.application,
            actor_user_id=director_user_id,
            action_type=f"licensing_{status}",
            details={
                "request_id": req.id,
                "status": status,
                "agreement_ref": agreement_reference,
            },
        )

    return req
