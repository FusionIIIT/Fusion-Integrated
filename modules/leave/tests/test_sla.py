"""SLA processing: pending-only, one-shot, and re-routing where configured."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, LeaveRequestTransition, SlaThreshold
from modules.leave.services import sla

pytestmark = pytest.mark.django_db


def _waiting_request(*, status=sm.AWAITING_UNIT_HEAD, hours_ago=30, user_id=1001):
    today = timezone.localdate()
    row = LeaveRequest.objects.create(
        user_id=user_id, kind="new", category="CL", start_date=today + timedelta(days=3),
        end_date=today + timedelta(days=4), purpose="Rest", status=status,
        applicant_role="staff", current_step_kind="unit_head",
        current_step_designation="HOD (CSE)", days_requested=2)
    transition = LeaveRequestTransition.objects.create(
        request=row, from_status=sm.DRAFT, to_status=status, event=sm.SUBMIT)
    LeaveRequestTransition.objects.filter(pk=transition.pk).update(
        created_at=timezone.now() - timedelta(hours=hours_ago))
    return row


def test_a_task_past_the_reminder_threshold_is_reminded_once(configured):
    _waiting_request(hours_ago=30)
    first = sla.sweep()
    assert first["reminded"] == 1
    assert first["escalated"] == 0

    second = sla.sweep()
    assert second["reminded"] == 0, "a reminder is one-shot"


def test_a_task_past_the_escalation_threshold_is_escalated(configured):
    _waiting_request(hours_ago=60)
    report = sla.sweep()
    assert report["reminded"] == 1
    assert report["escalated"] == 1


def test_a_decided_task_is_never_reminded(configured):
    _waiting_request(status=sm.APPROVED, hours_ago=200)
    report = sla.sweep()
    assert report == {"reminded": 0, "escalated": 0, "rerouted": 0, "skipped": 0}


def test_escalation_re_routes_only_when_a_designation_is_configured(configured):
    row = _waiting_request(hours_ago=60)
    first = sla.sweep()
    assert first["rerouted"] == 0
    row.refresh_from_db()
    assert row.current_step_designation == "HOD (CSE)"

    threshold = SlaThreshold.objects.get(task_class="unit_head_review")
    threshold.escalation_designation = "Registrar"
    threshold.save(update_fields=["escalation_designation"])

    row2 = _waiting_request(hours_ago=60, user_id=2002)
    report = sla.sweep()
    assert report["rerouted"] == 1
    row2.refresh_from_db()
    assert row2.current_step_designation == "Registrar"
    assert row2.transitions.filter(event="escalate").exists()


def test_a_task_class_with_no_threshold_is_skipped(configured):
    SlaThreshold.objects.all().delete()
    _waiting_request(hours_ago=500)
    report = sla.sweep()
    assert report["reminded"] == 0
    assert report["skipped"] == 1
