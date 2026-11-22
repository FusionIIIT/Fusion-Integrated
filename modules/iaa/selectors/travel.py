from django.db.models import QuerySet

from modules.iaa.models import TAClaim
from modules.iaa.selectors.scoping import scope_travel_claims


def get_travel_claims(principal, status: str | None = None) -> QuerySet[TAClaim]:
    qs = scope_travel_claims(TAClaim.objects.prefetch_related("items"), principal)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_travel_claim_by_id(principal, claim_id: int) -> TAClaim | None:
    return get_travel_claims(principal).filter(id=claim_id).first()


def get_pending_travel_approvals(principal) -> QuerySet[TAClaim]:
    qs = scope_travel_claims(TAClaim.objects.all(), principal)
    return qs.filter(
        status__in=["approval_pending", "escalated"],
        assigned_approver_id=principal.user_id,
    )
