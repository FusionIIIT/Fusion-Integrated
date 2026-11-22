from django.db.models import Prefetch, Q, QuerySet

from modules.hr.models import Claim, ClaimIntegrationStatus


def visible_claims(principal) -> QuerySet[Claim]:
    claims = Claim.objects.prefetch_related(
        Prefetch(
            "integration_statuses",
            queryset=ClaimIntegrationStatus.objects.order_by("-received_at"),
        )
    )
    if principal.has_permission("hr.claim.view"):
        return claims

    scope = Q()
    if principal.has_permission("hr.claim.view_self"):
        scope |= Q(employee_user_id=principal.user_id)
    if principal.has_permission("hr.claim.approve"):
        scope |= Q(current_authority_user_id=principal.user_id)
    if principal.has_permission("hr.claim.verify"):
        scope |= Q(status="pending_verification")
    if principal.has_permission("hr.claim.manage"):
        scope |= Q(status__in=("approved", "financial_processing_recorded"))
    return claims.filter(scope) if scope else claims.none()


def claim_for_user(*, claim_id: int, principal) -> Claim | None:
    return visible_claims(principal).filter(pk=claim_id).first()
