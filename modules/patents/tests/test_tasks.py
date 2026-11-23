"""Tests for patents Celery tasks (Step 4.7)."""
from __future__ import annotations

import datetime

import pytest
from django.utils import timezone

from modules.patents.domain import state_machine as sm
from modules.patents.models import OfficeActionRecord, PatentApplication, PatentPolicy
from modules.patents.tasks import pms_sweep_deadlines

pytestmark = pytest.mark.django_db


def test_pms_sweep_deadlines_expires_applications():
    PatentPolicy.objects.create(
        revision_resubmission_days=60,
        director_review_days=15,
        is_active=True,
    )

    now = timezone.now()

    # Expired app: decision date was 65 days ago
    app_expired = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0401",
        title="Expired Revision",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.NEEDS_REVISION,
        decision_date=now - datetime.timedelta(days=65),
    )

    # Active app: decision date was 20 days ago
    app_active = PatentApplication.objects.create(
        user_id=101,
        application_number="PMS-2026-0402",
        title="Active Revision",
        abstract="Abs",
        description="Desc",
        claims="Claims",
        status=sm.NEEDS_REVISION,
        decision_date=now - datetime.timedelta(days=20),
    )

    # Office action matching 5-day alert
    OfficeActionRecord.objects.create(
        application=app_active,
        action_code="FER-1",
        issuing_authority="IPO",
        issued_date=now.date() - datetime.timedelta(days=25),
        response_deadline=now.date() + datetime.timedelta(days=5),
        status="RECORDED",
    )

    summary = pms_sweep_deadlines()

    assert summary["expired"] == 1
    assert summary["alerts"] == 1

    app_expired.refresh_from_db()
    app_active.refresh_from_db()

    assert app_expired.status == sm.EXPIRED
    assert app_active.status == sm.NEEDS_REVISION

    # R1-11: Second run proves scheduled task idempotence
    summary2 = pms_sweep_deadlines()
    assert summary2["expired"] == 0
    app_expired.refresh_from_db()
    assert app_expired.status == sm.EXPIRED


def test_schedule_declarations():
    # R1-01 & R1-11: Verify task routes and beat schedule
    from modules.patents import schedule
    assert "patents.pms_sweep_deadlines" in schedule.TASK_ROUTES
    assert "patents.pms-sweep-deadlines" in schedule.BEAT_SCHEDULE

