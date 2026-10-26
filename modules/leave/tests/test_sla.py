"""Tests for SLA reminders and escalation (BR-EL-032..033, BR-EL-035, BR-EL-038, EL-UC-021)."""

import itertools
import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    LeaveRequest,
    LeaveType,
    SubstituteNomination,
    WorkflowTransition,
)
from modules.leave.services.sla import (
    StageSlaConfig,
    process_sla_events,
)

_counter = itertools.count(1)


@pytest.fixture
def leave_types():
    types = {}
    for code, name, max_consec in [
        ("CL", "Casual Leave", 3),
        ("EL", "Earned Leave", 30),
        ("RH", "Restricted Holiday", 2),
        ("COL", "Commuted Leave", 90),
        ("VL", "Vacation Leave", 60),
    ]:
        lt, _ = LeaveType.objects.get_or_create(
            code=code,
            defaults={"name": name, "max_consecutive_days": max_consec},
        )
        types[code] = lt
    return types


def _make_request(user_id, leave_type, status, hours_ago=0, department="Computer Science"):
    seq = next(_counter)
    now = timezone.now()
    created_time = now - timedelta(hours=hours_ago)
    req = LeaveRequest.objects.create(
        application_number=f"SLA-{user_id}-{hours_ago}-{seq}",
        user_id=user_id,
        cadre="faculty",
        department=department,
        leave_type=leave_type,
        start_date=now.date() + timedelta(days=5),
        end_date=now.date() + timedelta(days=7),
        requested_days=Decimal("3.0"),
        reason="Academic conference",
        status=status,
    )
    # Backdate created_at and updated_at
    LeaveRequest.objects.filter(pk=req.pk).update(created_at=created_time, updated_at=created_time)
    # Create transition into this status
    WorkflowTransition.objects.create(
        request=req,
        from_state="none",
        to_state=status,
        action="apply",
        actor_user_id=user_id,
        actor_role="faculty",
        remarks="Submitted",
    )
    WorkflowTransition.objects.filter(request=req).update(created_at=created_time)
    req.refresh_from_db()
    return req


@pytest.mark.django_db
def test_sla_below_at_and_above_thresholds(leave_types):
    """Requests are reminded or escalated according to elapsed time vs thresholds."""
    custom_configs = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=24.0,
            escalation_threshold_hours=48.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }

    # Req 1: 10h elapsed -> below reminder (24h)
    req_below = _make_request(401, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=10)

    # Req 2: 30h elapsed -> past reminder (24h) but below escalation (48h)
    req_reminder = _make_request(
        402, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=30
    )

    # Req 3: 50h elapsed -> past escalation (48h)
    req_escalation = _make_request(
        403, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=50
    )

    events = []
    report = process_sla_events(
        stage_configs=custom_configs,
        notification_dispatcher=events.append,
    )

    assert report.inspected_requests == 3
    assert report.reminders_sent == 1
    assert report.escalations_sent == 1

    # Verify transitions
    assert req_below.transitions.filter(action__startswith="sla_").count() == 0

    assert req_reminder.transitions.filter(action="sla_reminder").count() == 1
    assert req_reminder.transitions.filter(action="sla_escalation").count() == 0

    assert req_escalation.transitions.filter(action="sla_escalation").count() == 1

    # Verify notification payloads
    assert len(events) == 2
    reminder_event = next(e for e in events if e.event_type == "reminder")
    escalation_event = next(e for e in events if e.event_type == "escalation")
    assert reminder_event.request_id == req_reminder.id
    assert escalation_event.request_id == req_escalation.id


@pytest.mark.django_db
def test_sla_different_workflow_stages_and_recipients(leave_types):
    """Different stages resolve their respective responsible and escalation roles."""
    # 1. Substitute stage: pending substitute response
    req_sub = _make_request(410, leave_types["CL"], LeaveState.AWAITING_SUBSTITUTE, hours_ago=30)
    SubstituteNomination.objects.create(
        request=req_sub,
        substitute_user_id=888,
        status="pending",
        sequence=1,
    )

    events = []
    report = process_sla_events(
        request_ids=[req_sub.id],
        notification_dispatcher=events.append,
    )

    assert report.reminders_sent == 1
    assert len(events) == 1
    assert events[0].recipient_user_id == 888
    assert events[0].recipient_role == "Substitute"

    # Now backdate to escalation threshold (50h)
    req_sub.transitions.all().update(created_at=timezone.now() - timedelta(hours=50))
    events.clear()

    report_esc = process_sla_events(
        request_ids=[req_sub.id],
        notification_dispatcher=events.append,
    )
    assert report_esc.escalations_sent == 1
    # Substitute non-response escalates to applicant (user 410)
    assert events[0].recipient_user_id == 410
    assert events[0].recipient_role == "Applicant"


@pytest.mark.django_db
def test_sla_suppressed_for_non_pending_requests(leave_types):
    """Requests that have left the pending stage receive no reminders or escalations (BR-EL-032..033)."""
    # 100 hours old, but terminal status
    for status in [
        LeaveState.APPROVED,
        LeaveState.REJECTED,
        LeaveState.WITHDRAWN,
        LeaveState.CANCELLED,
    ]:
        req = _make_request(420, leave_types["CL"], status, hours_ago=100)
        events = []
        report = process_sla_events(
            request_ids=[req.id],
            notification_dispatcher=events.append,
        )
        assert report.reminders_sent == 0
        assert report.escalations_sent == 0
        assert len(events) == 0
        assert req.transitions.filter(action__startswith="sla_").count() == 0


@pytest.mark.django_db
def test_sla_idempotent_repeated_execution(leave_types):
    """Repeated execution does not send duplicate reminders or escalations for the same stage."""
    custom_configs = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=24.0,
            escalation_threshold_hours=48.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }

    req = _make_request(430, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=30)
    events = []

    # Run 1: sends reminder
    rep1 = process_sla_events(
        stage_configs=custom_configs,
        request_ids=[req.id],
        notification_dispatcher=events.append,
    )
    assert rep1.reminders_sent == 1
    assert len(events) == 1

    # Run 2: still at 30h elapsed, should skip reminder
    events.clear()
    rep2 = process_sla_events(
        stage_configs=custom_configs,
        request_ids=[req.id],
        notification_dispatcher=events.append,
    )
    assert rep2.reminders_sent == 0
    assert rep2.skipped_requests == 1
    assert len(events) == 0
    assert req.transitions.filter(action="sla_reminder").count() == 1


@pytest.mark.django_db
def test_notification_failure_resilience_and_retry(leave_types):
    """External notification failure does not corrupt workflow state and allows retry."""
    custom_configs = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=24.0,
            escalation_threshold_hours=48.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }

    req = _make_request(440, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=30)

    # Dispatcher that fails (e.g. SMTP connection error)
    def failing_dispatcher(evt):
        raise ConnectionError("Mail server offline")

    rep1 = process_sla_events(
        stage_configs=custom_configs,
        request_ids=[req.id],
        notification_dispatcher=failing_dispatcher,
    )

    assert rep1.notification_failures == 1
    assert rep1.reminders_sent == 0

    # Workflow state is untouched and no transition recorded yet
    req.refresh_from_db()
    assert req.status == LeaveState.AWAITING_UNIT_HEAD
    assert req.transitions.filter(action="sla_reminder").count() == 0

    # Next run with working dispatcher succeeds (retry)
    delivered = []
    rep2 = process_sla_events(
        stage_configs=custom_configs,
        request_ids=[req.id],
        notification_dispatcher=delivered.append,
    )
    assert rep2.notification_failures == 0
    assert rep2.reminders_sent == 1
    assert len(delivered) == 1
    assert req.transitions.filter(action="sla_reminder").count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_sla_execution_protection(leave_types):
    """Concurrent SLA workers on the same overdue request do not duplicate events."""
    custom_configs = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=24.0,
            escalation_threshold_hours=48.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }

    req = _make_request(450, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=30)

    barrier = threading.Barrier(2)
    reports = []

    def worker():
        from django.db import connection

        try:
            barrier.wait()
            rep = process_sla_events(
                stage_configs=custom_configs,
                request_ids=[req.id],
            )
            reports.append(rep)
        finally:
            connection.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    total_reminders = sum(r.reminders_sent for r in reports)
    total_skipped = sum(r.skipped_requests for r in reports)
    assert total_reminders == 1
    assert total_skipped == 1

    # Exactly one reminder transition created
    assert req.transitions.filter(action="sla_reminder").count() == 1


@pytest.mark.django_db
def test_missing_or_invalid_sla_configuration(leave_types):
    """Invalid SLA thresholds (e.g. negative or escalation < reminder) report cleanly."""
    invalid_configs = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=-5.0,
            escalation_threshold_hours=48.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }

    report = process_sla_events(stage_configs=invalid_configs)
    assert len(report.exceptions) == 1
    assert "Invalid negative SLA threshold" in report.exceptions[0]

    invalid_order = {
        LeaveState.AWAITING_UNIT_HEAD: StageSlaConfig(
            reminder_threshold_hours=50.0,
            escalation_threshold_hours=20.0,
            responsible_role="Unit Head",
            escalation_role="Director",
        ),
    }
    report2 = process_sla_events(stage_configs=invalid_order)
    assert len(report2.exceptions) == 1
    assert "cannot be less than reminder threshold" in report2.exceptions[0]


@pytest.mark.django_db
def test_leave_sla_management_command(leave_types, capsys):
    """Management command leave_sla executes and respects --dry-run and thresholds."""
    req = _make_request(460, leave_types["CL"], LeaveState.AWAITING_UNIT_HEAD, hours_ago=30)

    # Dry run
    call_command(
        "leave_sla",
        request_id=req.id,
        reminder_hours=24.0,
        escalation_hours=48.0,
        dry_run=True,
    )
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "Reminders issued:   1" in captured.out
    assert req.transitions.filter(action="sla_reminder").count() == 0

    # Real run
    call_command(
        "leave_sla",
        request_id=req.id,
        reminder_hours=24.0,
        escalation_hours=48.0,
    )
    captured = capsys.readouterr()
    assert "SLA processing finished successfully." in captured.out
    assert req.transitions.filter(action="sla_reminder").count() == 1

    # Re-run reports skipped
    call_command(
        "leave_sla",
        request_id=req.id,
        reminder_hours=24.0,
        escalation_hours=48.0,
    )
    captured = capsys.readouterr()
    assert "Skipped requests:   1" in captured.out
