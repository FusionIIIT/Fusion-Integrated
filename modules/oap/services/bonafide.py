from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.oap.domain import roles
from modules.oap.domain import state_machines as sm
from modules.oap.models import BonafideRequest
from modules.oap.selectors import scoping
from modules.oap.services import notifications
from modules.oap.services.common import (
    bad_request,
    domain_guard,
    locked,
    need,
    need_role,
    record,
)


def request(principal, *, purpose: str = "") -> BonafideRequest:
    need(principal, "oap.bonafide_request.create")
    with transaction.atomic():
        req = BonafideRequest.objects.create(user_id=principal.user_id, purpose=purpose)
        record("bonafide", req.pk, "", sm.BONAFIDE_SUBMITTED, principal.user_id)
        notifications.notify(
            [principal.user_id],
            "Bonafide request submitted",
            f"Your bonafide request #{req.pk} is with the Academic Administrator.",
        )
    return req


def verify(principal, pk: int) -> BonafideRequest:
    need(principal, "oap.bonafide_request.review")
    need_role(principal, roles.ACADEMIC_ADMIN)
    with transaction.atomic():
        req = locked(scoping.bonafide_for(principal), pk, "Bonafide request not found.")
        if req.status != sm.BONAFIDE_SUBMITTED:
            raise ConflictError(
                "Only a submitted request can be verified.", code="not_allowed_in_current_state"
            )
        if req.verified_at is not None:
            raise ConflictError("This request has already been verified.", code="already_verified")
        req.verified_by_user_id = principal.user_id
        req.verified_at = timezone.now()
        req.save(update_fields=["verified_by_user_id", "verified_at", "updated_at"])
    return req


def decide(principal, pk: int, outcome: str) -> BonafideRequest:
    need(principal, "oap.bonafide_request.approve")
    need_role(principal, roles.ACADEMIC_ADMIN)
    if outcome not in ("approve", "reject"):
        raise bad_request("Outcome must be 'approve' or 'reject'.", "invalid_outcome")
    with transaction.atomic(), domain_guard():
        req = locked(scoping.bonafide_for(principal), pk, "Bonafide request not found.")
        if req.verified_at is None:
            raise ConflictError(
                "Verify the request before deciding on it.", code="verification_required"
            )
        new_state = sm.next_state("bonafide", req.status, outcome, "academic_admin")
        previous = req.status
        req.status = new_state
        req.decided_by_user_id = principal.user_id
        req.decided_at = timezone.now()
        req.save(update_fields=["status", "decided_by_user_id", "decided_at", "updated_at"])
        record("bonafide", req.pk, previous, new_state, principal.user_id)
        text = (
            "Your bonafide certificate is available for download."
            if new_state == sm.BONAFIDE_APPROVED
            else "Your bonafide request was rejected."
        )
        notifications.notify([req.user_id], "Bonafide request decided", text)
    return req
