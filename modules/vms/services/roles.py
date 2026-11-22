"""Role assignment and pending work handoff services."""

from __future__ import annotations

from django.db import transaction

from modules.vms.models import VisitRequest


@transaction.atomic
def reassign_vms_work(
    from_user_id: int,
    to_user_id: int,
) -> int:
    """Hand off pending visit requests when operational roles change (CFR-002, AFR-003, BR-183)."""
    return VisitRequest.objects.filter(
        host_id=from_user_id,
        status="PENDING_APPROVAL",
    ).update(host_id=to_user_id)
