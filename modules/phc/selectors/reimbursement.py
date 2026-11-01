"""Reimbursement claim selectors (CFR-PHC-004, CFR-PHC-005)."""
from modules.phc.domain.entities import ReimbursementStatus
from modules.phc.models.reimbursement import ReimbursementClaim


def get_user_reimbursement_claims(claimant_user_id: int) -> list[ReimbursementClaim]:
    """Employee claim tracking (AFR-PHC-022; UC-PHC-05)."""
    return list(
        ReimbursementClaim.objects.filter(claimant_user_id=claimant_user_id)
        .select_related("prescription")
        .prefetch_related("history")
        .order_by("-created_at")
    )


def get_reimbursement_claim_detail(
    claim_id: int,
    requesting_user_id: int,
    is_staff: bool = False,
) -> ReimbursementClaim:
    claim = (
        ReimbursementClaim.objects.select_related("prescription", "prescription__visit", "prescription__visit__doctor")
        .prefetch_related("history")
        .get(id=claim_id)
    )
    if not is_staff and claim.claimant_user_id != requesting_user_id:
        raise PermissionError("You can only access reimbursement claims you submitted.")
    return claim


def get_review_queue_for_stage(stage: str | None = None) -> list[ReimbursementClaim]:
    """Queue of claims pending action at each workflow stage (AFR-PHC-017, 018, 019, 020, 021)."""
    qs = (
        ReimbursementClaim.objects.select_related("prescription")
        .prefetch_related("history")
        .all()
    )
    if stage:
        qs = qs.filter(status=stage)
    else:
        # By default exclude terminal states from active queue
        qs = qs.exclude(status__in=[ReimbursementStatus.REJECTED.value, ReimbursementStatus.REIMBURSED.value])
    return list(qs.order_by("created_at"))
