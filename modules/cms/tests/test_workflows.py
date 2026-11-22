from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.test import override_settings
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.cms import services
from modules.cms.models import (
    CmsNotificationEvent,
    Complaint,
)
from modules.cms.services import escalate, publish_announcement, submit_feedback


def actor(user_id=101):
    return SimpleNamespace(user_id=user_id, active_role="complaint_handler")


@pytest.mark.django_db
def test_user_verified_closure_records_history_and_trigger():
    owner = actor()
    handler = actor(202)
    complaint = services.submit(actor=owner, category="Facilities", description="Light out")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="medium"
    )
    services.add_progress(complaint_id=complaint.pk, actor=handler, text="Inspection scheduled")
    assert (
        complaint.progress_updates.get(update_text="Inspection scheduled").actor_user_id
        == handler.user_id
    )
    resolved = services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Replaced the light"
    )
    assert resolved.status == "resolved"
    assert [e.event_type for e in resolved.notification_events.all()] == [
        "complaint.submitted",
        "complaint.resolved",
    ]
    closed = services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    assert closed.status == "closed"
    assert list(closed.history.values_list("to_status", flat=True)) == [
        "submitted",
        "resolved",
        "closed",
    ]
    assert closed.notification_events.filter(event_type="complaint.closed").exists()


@pytest.mark.django_db
def test_rejection_requires_reason_and_records_rejected_state():
    owner = actor()
    handler = actor(202)
    complaint = services.submit(actor=owner, category="Facilities", description="Noise")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="low"
    )
    with pytest.raises(ConflictError, match="Outcome details are required"):
        services.decide_outcome(
            complaint_id=complaint.pk, actor=handler, outcome="rejected", details=" "
        )
    complaint = services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="rejected", details="Outside CMS scope"
    )
    assert complaint.status == "rejected"
    assert complaint.rejection_reason == "Outside CMS scope"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="complainant", CMS_REOPENED_STATUS="in_progress")
def test_reopening_is_requested_then_supervisor_decides():
    owner = actor()
    handler = actor(202)
    supervisor = actor(303)
    complaint = services.submit(actor=owner, category="Access", description="Gate")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Access", priority="high"
    )
    services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Access restored"
    )
    services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    request = services.request_reopening(
        complaint_id=complaint.pk, actor=owner, reason="Access failed again"
    )
    assert request.decision == "pending"
    request = services.review_reopening(
        request_id=request.pk, actor=supervisor, decision="approved", note="Reopened for review"
    )
    complaint.refresh_from_db()
    assert request.decision == "approved"
    assert complaint.status == "in_progress"
    assert complaint.history.get(to_status="in_progress").actor_user_id == supervisor.user_id


@pytest.mark.django_db
def test_denied_reopening_keeps_complaint_closed_and_records_decision():
    owner = actor()
    handler = actor(202)
    supervisor = actor(303)
    complaint = services.submit(actor=owner, category="Access", description="Door lock")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Access", priority="medium"
    )
    services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Lock repaired"
    )
    services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    request = services.request_reopening(
        complaint_id=complaint.pk, actor=owner, reason="Issue has not returned"
    )
    request = services.review_reopening(
        request_id=request.pk, actor=supervisor, decision="denied", note="Resolution verified"
    )
    complaint.refresh_from_db()
    assert request.decision == "denied"
    assert complaint.status == "closed"
    assert complaint.notification_events.filter(
        event_type="complaint.reopening_outcome", payload__decision="denied"
    ).exists()


@pytest.mark.django_db
@override_settings(CMS_SLA_REMINDER_HOURS=3, CMS_SLA_HOURS={"low": 24, "medium": 12, "high": 4})
def test_sla_reminder_and_auto_escalation_are_idempotent():
    owner = actor()
    handler = actor(202)
    complaint = services.submit(actor=owner, category="Facilities", description="Water leak")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="high"
    )
    now = timezone.now()
    Complaint.objects.filter(pk=complaint.pk).update(sla_due_at=now + timedelta(hours=2))
    assert services.process_sla(now)["reminded"] == 1
    assert services.process_sla(now)["reminded"] == 0
    assert CmsNotificationEvent.objects.filter(event_type="complaint.sla_reminder").count() == 1
    Complaint.objects.filter(pk=complaint.pk).update(sla_due_at=now - timedelta(minutes=1))
    assert services.process_sla(now)["escalated"] == 1
    assert services.process_sla(now)["escalated"] == 0
    complaint.refresh_from_db()
    assert complaint.status == "submitted"  # escalation is orthogonal to lifecycle status
    assert complaint.escalation_kind == "automatic"


@pytest.mark.django_db
@override_settings(CMS_CLOSURE_VERIFIER="supervisor")
def test_supervisor_verifies_closure_when_configured():
    owner = actor()
    handler = actor(202)
    supervisor = actor(303)
    complaint = services.submit(actor=owner, category="Facilities", description="Door")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="medium"
    )
    services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Fixed"
    )
    with pytest.raises(ConflictError, match="not awaiting your closure verification"):
        services.verify_closure(complaint_id=complaint.pk, actor=owner, verifier="complainant")
    closed = services.verify_closure(
        complaint_id=complaint.pk, actor=supervisor, verifier="supervisor"
    )
    assert closed.status == "closed"
    assert closed.history.get(to_status="closed").actor_user_id == supervisor.user_id


@pytest.mark.django_db
def test_manual_escalation_records_kind_without_changing_lifecycle():
    owner = actor()
    handler = actor(202)
    complaint = services.submit(actor=owner, category="Facilities", description="Leak")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="high"
    )
    escalated = escalate(complaint_id=complaint.pk, actor=handler, kind="manual")
    assert escalated.escalation_kind == "manual"
    assert escalated.status == "submitted"
    assert escalated.notification_events.filter(event_type="complaint.escalated").exists()


@pytest.mark.django_db
def test_feedback_and_announcement_persist_and_trigger_configured_events():
    owner = actor()
    handler = actor(202)
    complaint = services.submit(actor=owner, category="Facilities", description="Broken tap")
    services.setup_handling(
        complaint_id=complaint.pk, actor=handler, category="Facilities", priority="low"
    )
    services.decide_outcome(
        complaint_id=complaint.pk, actor=handler, outcome="resolved", details="Repaired"
    )
    feedback = submit_feedback(complaint_id=complaint.pk, actor=owner, text="Thank you")
    assert feedback.feedback_text == "Thank you"
    assert complaint.notification_events.filter(event_type="complaint.feedback_submitted").exists()

    announcement = publish_announcement(
        actor=handler, title="Maintenance", body="Water supply restored", notify_users=True
    )
    assert announcement.is_published
    event = CmsNotificationEvent.objects.get(event_type="announcement.published")
    assert event.payload["announcement_id"] == announcement.pk
