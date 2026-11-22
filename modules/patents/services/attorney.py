"""Attorney panel management services (UC-PMS-026, BR-PMS-040..045)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import AttorneyPanelMember
from modules.patents.selectors import scoping


def register_panel_member(
    actor,
    user_id: int,
    firm_name: str,
    expertise_domains: list[str] | None = None,
    is_approved: bool = True,
) -> AttorneyPanelMember:
    """PCC_ADMIN registers or updates an attorney on the panel."""
    if not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("PCC_ADMIN authority required to manage attorney panel.")

    if not firm_name.strip():
        raise ConflictError("Firm name cannot be empty.")

    with transaction.atomic():
        member, _ = AttorneyPanelMember.objects.update_or_create(
            user_id=user_id,
            defaults={
                "firm_name": firm_name,
                "expertise_domains": expertise_domains or [],
                "is_approved_panel": is_approved,
            },
        )
    return member


def update_attorney_workload(user_id: int, delta: int) -> AttorneyPanelMember:
    """Adjust active workload count for an attorney."""
    with transaction.atomic():
        member = AttorneyPanelMember.objects.select_for_update().filter(user_id=user_id).first()
        if member is None:
            raise NotFoundError("Attorney panel member not found.")
        new_workload = max(0, member.active_workload + delta)
        member.active_workload = new_workload
        member.save()
    return member
