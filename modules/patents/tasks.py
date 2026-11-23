"""Scheduled Celery tasks for the patents module (Step 4.7)."""
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
    """Run the daily deadline sweep and return counts for each check."""
    now = timezone.now()
    policy = PatentPolicy.objects.filter(is_active=True).first()
    rev_limit = policy.revision_resubmission_days if policy else dl.DEFAULT_REVISION_DAYS
    review_limit = policy.director_review_days if policy else dl.DEFAULT_REVIEW_DAYS
    return {
        "expired": _sweep_revisions(now, rev_limit),
        "overdue_reviews": _sweep_reviews(now, review_limit),
        "overdue_renewals": _sweep_renewals(now.date()),
        "alerts": _sweep_office_actions(now.date()),
    }


def _sweep_revisions(now, rev_limit: int) -> int:
    """Expire revision windows that have lapsed (BR-PMS-035, BR-PMS-038)."""
    expired_count = 0
    pending_revision = PatentApplication.objects.filter(
        status__in=(sm.NEEDS_REVISION, sm.REJECTED),
        decision_date__isnull=False,
    )
    for app in pending_revision:
        if not dl.is_revision_expired(app.decision_date, now, limit_days=rev_limit):
            continue
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
    return expired_count


def _sweep_reviews(now, review_limit: int) -> int:
    """Flag Director reviews past their deadline (BR-PMS-031, BR-PMS-104)."""
    overdue = 0
    for app in PatentApplication.objects.filter(status=sm.UNDER_REVIEW):
        if dl.is_review_overdue(app.updated_at, now, limit_days=review_limit):
            overdue += 1
            log.warning("pms.review.overdue application=%s", app.application_number)
    return overdue


def _sweep_renewals(today) -> int:
    """Flag missed annuity renewals for Director confirmation; never changes status."""
    missed = PatentApplication.objects.filter(
        status__in=(sm.GRANTED, sm.MAINTENANCE_PENDING),
        renewal_due_date__lt=today,
        renewal_decided_at__isnull=True,
    )
    count = 0
    for app in missed:
        count += 1
        log.warning("pms.renewal.overdue application=%s", app.application_number)
    return count


def _sweep_office_actions(today) -> int:
    """Count office-action response deadlines that fall on an alert interval (BR-PMS-101..103)."""
    alerts = 0
    active_oas = OfficeActionRecord.objects.filter(
        status__in=("RECORDED", "DRAFTING", "AWAITING_APPLICANT")
    )
    for oa in active_oas:
        interval = dl.match_alert_interval(oa.response_deadline, today)
        if interval is not None:
            alerts += 1
            log.info("pms.alert.deadline office_action=%s interval=%d_days", oa.id, interval)
    return alerts
