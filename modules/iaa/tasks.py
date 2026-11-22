"""Scheduled Celery tasks for IAA (IAA-BR-401, IAA-UC-203)."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

log = logging.getLogger("fusion.iaa.tasks")


@shared_task(
    name="iaa.escalate_overdue_approvals",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def escalate_overdue_approvals() -> int:
    """Escalate pending approvals exceeding configured timeout."""
    from modules.iaa.models import ExpenseVoucherRequest, IAAConfiguration, TAClaim
    from modules.iaa.services.approvals import escalate_overdue_approval

    config = IAAConfiguration.objects.filter(is_active=True).first()
    timeout_days = config.approval_timeout_days if config else 3
    cutoff = timezone.now() - timedelta(days=timeout_days)

    overdue_reqs = ExpenseVoucherRequest.objects.filter(
        status__in=["finance_validated", "approval_pending"],
        approval_assigned_at__lt=cutoff,
    ).values_list("id", flat=True)

    overdue_claims = TAClaim.objects.filter(
        status="approval_pending",
        approval_assigned_at__lt=cutoff,
    ).values_list("id", flat=True)

    count = 0
    for req_id in overdue_reqs:
        escalate_overdue_approval("request", req_id, higher_authority_role="Director")
        count += 1

    for claim_id in overdue_claims:
        escalate_overdue_approval("travel", claim_id, higher_authority_role="Director")
        count += 1

    log.info("iaa.escalate_overdue_approvals: Escalated %d items", count)
    return count
