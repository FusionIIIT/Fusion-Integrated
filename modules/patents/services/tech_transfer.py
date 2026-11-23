"""Technology transfer services (UC-PMS-020, UC-PMS-021, BR-PMS-088..091)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import TechnologyTransferRecord
from modules.patents.selectors import scoping


def submit_tech_transfer_request(
    actor,
    application_id: int,
    request_type: str,
    partner_name: str,
    terms_summary: str = "",
) -> TechnologyTransferRecord:
    """Applicant submits technology transfer / licensing request."""
    scope = scoping.applications_for(actor)
    app = scope.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")

    with transaction.atomic():
        return TechnologyTransferRecord.objects.create(
            application=app,
            applicant_user_id=getattr(actor, "user_id", app.user_id),
            request_type=request_type,
            partner_name=partner_name,
            terms_summary=terms_summary,
            status="SUBMITTED",
        )


def review_tech_transfer_request(
    actor,
    record_id: int,
    status: str,  # "APPROVED", "REJECTED", "NEGOTIATING"
    terms_summary: str = "",
) -> TechnologyTransferRecord:
    """Director reviews technology transfer / licensing request."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required to review tech transfer.")

    with transaction.atomic():
        rec = TechnologyTransferRecord.objects.select_for_update().filter(pk=record_id).first()
        if rec is None:
            raise NotFoundError("Technology transfer record not found.")

        if status not in ("APPROVED", "REJECTED", "NEGOTIATING"):
            raise ConflictError(f"Invalid technology transfer status: {status}")

        rec.status = status
        if terms_summary:
            rec.terms_summary = terms_summary
        rec.save()
    return rec
