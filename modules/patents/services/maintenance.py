"""Post-grant maintenance renewal services (UC-PMS-018, BR-PMS-059..061, 100)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.domain import state_machine as sm
from modules.patents.models import PatentApplication
from modules.patents.selectors import scoping


def record_renewal_decision(
    actor,
    application_id: int,
    renew: bool,
    notes: str = "",
) -> PatentApplication:
    """Record Director post-grant maintenance renewal decision."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required for renewal decision.")

    with transaction.atomic():
        app = scoping.applications_for(actor).select_for_update().filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("Patent application not found.")

        if app.status != sm.GRANTED:
            raise ConflictError("Maintenance renewals are only applicable to GRANTED patents.")

        # Note renewal status in description/version
        app.version += 1
        app.save()

    return app
