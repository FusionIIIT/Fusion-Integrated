"""Business Rule tests for deadlines, alerts, escalations, notifications, audit, and system boundaries."""

from __future__ import annotations

import datetime
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain.errors import ExternalServiceUnavailableError
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyAssignment,
    OfficeAction,
    PmsAuditTrail,
    PmsNotificationOutbox,
    PostGrantMaintenance,
)
from modules.pms.services import (
    add_business_days,
    calculate_review_deadline,
    calculate_revision_deadline,
    enqueue_notification,
    log_audit,
    monitor_and_process_deadlines,
    record_external_filing,
    record_office_action,
    search_prior_art,
    submit_application,
)
from modules.pms.services.maintenance import schedule_cycle
from modules.pms.tests.support import configure, configure_maintenance_schedule

pytestmark = pytest.mark.django_db


def test_br_tc_104_pms_calculates_monitors_director_review_deadline():
    """BR-TC-104 | BR-PMS-097: PMS calculates/monitors the Director review deadline using the applicable review-deadline rule."""
    assigned_at = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=datetime.UTC)
    deadline = calculate_review_deadline(assigned_at)
    assert deadline == add_business_days(assigned_at, 15)


def test_br_tc_105_pms_calculates_monitors_revision_deadline():
    """BR-TC-105 | BR-PMS-098: PMS calculates/monitors the revision deadline using the applicable revision-deadline rule."""
    decided_at = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=datetime.UTC)
    deadline = calculate_revision_deadline(decided_at)
    assert deadline == decided_at + timedelta(days=60)


def test_br_tc_106_pms_calculates_monitors_office_action_response_deadlines():
    """BR-TC-106 | BR-PMS-099: PMS calculates/monitors office-action response deadlines when applicable deadline rules/data are available."""
    app = submit_application(
        applicant_user_id=1001,
        title="OA Monitor App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    now = timezone.now()
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=now.date(),
        due_date=(now + timedelta(days=5)).date(),
        details="Due in 5 days",
        requires_applicant_review=False,
    )
    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_5",
        dedupe_key__startswith=f"pms:oa:alert:{oa.id}:5:",
    ).exists()


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-107 | BR-PMS-099: OfficeAction requires an explicit due_date "
        "in the model schema and has no separate office-action deadline rule toggle."
    )
)
def test_br_tc_107_exception_when_office_action_deadline_rules_unavailable():
    """BR-TC-107 | BR-PMS-099: exception when office-action deadline rules/data are unavailable."""


def test_br_tc_108_pms_calculates_monitors_maintenance_fee_deadlines():
    """BR-TC-108 | BR-PMS-100: PMS calculates/monitors maintenance-fee deadlines when applicable jurisdictional schedule rules/data are available."""
    configure_maintenance_schedule()
    app = submit_application(
        applicant_user_id=1001,
        title="Maintenance Monitor App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        jurisdiction="IN",
    )
    app.status = PatentApplicationStatus.GRANTED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    now = timezone.now()
    cycle = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=(now + timedelta(days=30)).date(),
        maintenance_status="scheduled",
    )
    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_30",
        dedupe_key__startswith=f"pms:maintenance:alert:{cycle.id}:30:",
    ).exists()


def test_br_tc_109_exception_when_jurisdictional_maintenance_schedule_unavailable():
    """BR-TC-109 | BR-PMS-100: exception when jurisdictional maintenance-fee schedule rules/data are unavailable."""
    app = submit_application(
        applicant_user_id=1001,
        title="Unconfigured Schedule App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        jurisdiction="XX",
    )
    app.grant_date = datetime.date(2026, 1, 1)
    app.save(update_fields=["grant_date", "updated_at"])
    assert schedule_cycle(app, 1) is None


def test_br_tc_110_alert_generated_30_days_before_tracked_deadline():
    """BR-TC-110 | BR-PMS-101: alert generated at 30 days before a tracked deadline where applicable."""
    configure(alert_offsets=[30, 15, 5])
    app = submit_application(
        applicant_user_id=1001,
        title="30 Day Alert App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    now = timezone.now()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 3001
    app.review_deadline = now + timedelta(days=30)
    app.save(update_fields=["status", "assigned_director_user_id", "review_deadline", "updated_at"])
    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_30",
        recipient_user_id=3001,
    ).exists()


def test_br_tc_111_alert_generated_15_days_before_tracked_deadline():
    """BR-TC-111 | BR-PMS-102: alert generated at 15 days before a tracked deadline where applicable."""
    configure(alert_offsets=[30, 15, 5])
    app = submit_application(
        applicant_user_id=1001,
        title="15 Day Alert App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    now = timezone.now()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 3001
    app.review_deadline = now + timedelta(days=15)
    app.save(update_fields=["status", "assigned_director_user_id", "review_deadline", "updated_at"])
    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_15",
        recipient_user_id=3001,
    ).exists()


def test_br_tc_112_alert_generated_5_days_before_tracked_deadline():
    """BR-TC-112 | BR-PMS-103: alert generated at 5 days before a tracked deadline where applicable."""
    configure(alert_offsets=[30, 15, 5])
    app = submit_application(
        applicant_user_id=1001,
        title="5 Day Alert App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    now = timezone.now()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 3001
    app.review_deadline = now + timedelta(days=5)
    app.save(update_fields=["status", "assigned_director_user_id", "review_deadline", "updated_at"])
    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_5",
        recipient_user_id=3001,
    ).exists()


def test_br_tc_113_escalation_triggered_when_tracked_deadline_is_missed():
    """BR-TC-113 | BR-PMS-104: escalation triggered when tracked deadline is missed."""
    app = submit_application(
        applicant_user_id=1001,
        title="Missed Deadline App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    now = timezone.now()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 3001
    app.review_deadline = now - timedelta(days=2)
    app.save(update_fields=["status", "assigned_director_user_id", "review_deadline", "updated_at"])
    stats = monitor_and_process_deadlines(now=now)
    assert stats["escalations"] >= 1
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.escalated",
        recipient_user_id=3001,
    ).exists()


def test_br_tc_114_pms_triggers_system_generated_email_notifications_within_scope():
    """BR-TC-114 | BR-PMS-116: PMS triggers system-generated email notifications while external email delivery infrastructure remains outside PMS scope."""
    notif = enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:br-tc-114:test",
        subject="Test Notification",
        body="Body text",
        recipient_user_id=1001,
    )
    assert notif is not None
    assert notif.status == "pending"


def test_br_tc_121_audit_record_includes_required_fields_where_applicable():
    """BR-TC-121 | BR-PMS-121: audit record includes user ID, action type, timestamp, application ID, previous state, and new state where applicable."""
    app = submit_application(
        applicant_user_id=1001,
        title="Audit Fields App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    entry = log_audit(
        application=app,
        actor_user_id=1001,
        action_type="state_changed",
        from_state="submitted",
        to_state="under_review",
        details={"note": "transition"},
    )
    assert entry.actor_user_id == 1001
    assert entry.action_type == "state_changed"
    assert entry.timestamp is not None
    assert entry.application_id == app.id
    assert entry.from_state == "submitted"
    assert entry.to_state == "under_review"


def test_br_tc_122_critical_pms_operations_create_immutable_audit_records():
    """BR-TC-122 | BR-PMS-122: critical PMS operations create audit records that are immutable."""
    app = submit_application(
        applicant_user_id=1001,
        title="Immutable Audit App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    entry = PmsAuditTrail.objects.filter(application=app).first()
    assert entry is not None
    assert entry.is_immutable is True


def test_br_tc_138_external_patent_office_systems_boundary():
    """BR-TC-138 | BR-PMS-138: external patent-office systems boundary."""
    app = submit_application(
        applicant_user_id=1001,
        title="External Office App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    today = timezone.now().date()
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="Office Communication",
        issue_date=today,
        due_date=today + timedelta(days=30),
        details="Recorded from patent office",
        requires_applicant_review=False,
    )
    assert OfficeAction.objects.filter(pk=oa.pk).exists()


def test_br_tc_139_external_financial_systems_boundary():
    """BR-TC-139 | BR-PMS-139: external financial systems boundary."""
    app = submit_application(
        applicant_user_id=1001,
        title="Financial Metadata App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    budget = app.budget
    assert budget.total_cost is not None


def test_br_tc_140_external_document_management_systems_boundary():
    """BR-TC-140 | BR-PMS-140: external document-management systems boundary."""
    app = submit_application(
        applicant_user_id=1001,
        title="Doc Boundary App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    assert list(app.documents.all()) == []


def test_br_tc_141_external_prior_art_databases_as_query_sources():
    """BR-TC-141 | BR-PMS-141: external prior-art databases act as query sources rather than PMS-owned repositories."""
    with pytest.raises(ExternalServiceUnavailableError):
        search_prior_art(query="photonics", domain="Physics", actor_user_id=1001)


def test_br_tc_142_external_filing_success_not_treated_as_internally_controlled():
    """BR-TC-142 | BR-PMS-142: external filing success not treated as internally controlled."""
    app = submit_application(
        applicant_user_id=1001,
        title="External Confirmation App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    AttorneyAssignment.objects.create(
        application=app,
        attorney_user_id=5001,
        assigned_by_user_id=1001,
        status="accepted",
        is_active=True,
    )
    budget = app.budget
    budget.status = "approved"
    budget.save(update_fields=["status", "updated_at"])
    with pytest.raises(ExternalServiceUnavailableError):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="EXT-999",
            external_filing_date=datetime.date(2026, 11, 1),
            filing_confirmation="CONF-999",
        )
    app.refresh_from_db()
    assert app.external_filing_id == ""
