"""Scheduled Celery tasks for the patents module (Step 4.7).

Enforces BR-PMS-031, BR-PMS-035, BR-PMS-038, BR-PMS-101..104.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from modules.patents.domain import deadlines as dl
from modules.patents.domain import state_machine as sm
from modules.patents.models import OfficeActionRecord, PatentApplication, PatentPolicy
from modules.patents.services import applications as app_service

log = logging.getLogger("fusion.patents.tasks")


@shared_task(
    name="patents.pms_sweep_deadlines",
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=270,
    time_limit=300,
)
def pms_sweep_deadlines() -> dict[str, int]:
    """Daily deadline sweep: expire resubmissions, flag overdue reviews, dispatch alerts."""
    now = timezone.now()
    today = now.date()

    policy = PatentPolicy.objects.filter(is_active=True).first()
    rev_limit = policy.revision_resubmission_days if policy else dl.DEFAULT_REVISION_DAYS
    review_limit = policy.director_review_days if policy else dl.DEFAULT_REVIEW_DAYS

    # 1. Sweep revision deadlines (BR-PMS-035, BR-PMS-038)
    expired_count = 0
    pending_revision = PatentApplication.objects.filter(
        status__in=(sm.NEEDS_REVISION, sm.REJECTED),
        decision_date__isnull=False,
    )
    for app in pending_revision:
        if dl.is_revision_expired(app.decision_date, now, limit_days=rev_limit):
            try:
                app_service.transition_application(
                    application_id=app.id,
                    event="expire",
                    actor=None,
                    scope=PatentApplication.objects.all(),
                )
                expired_count += 1
                log.info("pms.deadline.expired application=%s", app.application_number)
            except Exception:
                log.exception("Failed to expire application %s", app.id)

    # 2. Sweep overdue director reviews (BR-PMS-031, BR-PMS-104)
    overdue_reviews_count = 0
    under_review = PatentApplication.objects.filter(status=sm.UNDER_REVIEW)
    for app in under_review:
        ref_time = app.updated_at
        if dl.is_review_overdue(ref_time, now, limit_days=review_limit):
            overdue_reviews_count += 1
            log.warning("pms.review.overdue application=%s", app.application_number)

    # 3. Sweep office action response deadlines (BR-PMS-101..103)
    alerts_count = 0
    active_oas = OfficeActionRecord.objects.filter(
        status__in=("RECORDED", "DRAFTING", "AWAITING_APPLICANT")
    )
    for oa in active_oas:
        interval = dl.match_alert_interval(oa.response_deadline, today)
        if interval is not None:
            alerts_count += 1
            log.info("pms.alert.deadline office_action=%s interval=%d_days", oa.id, interval)

    return {
        "expired": expired_count,
        "overdue_reviews": overdue_reviews_count,
        "alerts": alerts_count,
    }
