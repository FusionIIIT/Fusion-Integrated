"""BW-CMS-08 (WF-08) – Automatic SLA Escalation Workflow.

Workflow:
Background endpoint processes overdue complaints and sets automatic escalation;
also triggers pre-breach SLA reminder notifications
(Page 4 – BW-CMS-08).

Ambiguity Note (WF-A-001):
The specification does not mandate exact scheduling intervals (e.g. cron vs on-demand);
the CMS implementation exposes an autonomous trigger endpoint at POST /api/v1/complaints/sla-check/
which processes both breach escalations and pre-breach reminders.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_008_process_overdue_complaints_via_api(api_client, stub_iam, make_session, complaint_factory):
    """POST /sla-check/ scans for overdue complaints and flags them with automatic SLA escalation."""
    now = timezone.now()
    overdue_deadline = now - timedelta(hours=3)

    c1 = complaint_factory(
        status="submitted",
        sla_deadline=overdue_deadline,
        is_escalated=False,
    )
    c2 = complaint_factory(
        status="in_progress",
        sla_deadline=overdue_deadline,
        is_escalated=False,
    )

    session = make_session(
        user_id=4001,
        permissions=[],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=session)

    res = api_client.post("/api/v1/complaints/sla-check/", {}, format="json")
    assert res.status_code == 200
    data = res.json()
    assert data["escalated_count"] >= 2
    assert "reminders_sent" in data

    c1.refresh_from_db()
    c2.refresh_from_db()

    assert c1.is_escalated is True
    assert c1.escalation_type == "automatic_sla"
    assert c2.is_escalated is True
    assert c2.escalation_type == "automatic_sla"

    # Verify system transition logged
    assert ComplaintTransition.objects.filter(
        complaint=c1,
        actor_role="system",
        remarks__contains="System automatic SLA escalation",
    ).exists()

@pytest.mark.django_db
def test_wf_008_pre_breach_reminder_triggered(api_client, stub_iam, make_session, complaint_factory):
    """POST /sla-check/ sends pre-breach reminder when at least 75% SLA duration has elapsed."""
    now = timezone.now()
    # 75% elapsed: created 36 hours ago, deadline in 12 hours (total 48 hours, 36/48 = 0.75)
    created_at = now - timedelta(hours=36)
    deadline = now + timedelta(hours=12)

    c = complaint_factory(
        status="in_progress",
        is_escalated=False,
        sla_reminder_sent=False,
        sla_deadline=deadline,
    )
    # Manually adjust created_at to simulate time passage
    c.created_at = created_at
    c.save(update_fields=["created_at"])

    session = make_session(
        user_id=4001,
        permissions=[],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=session)

    res = api_client.post("/api/v1/complaints/sla-check/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["reminders_sent"] >= 1

    c.refresh_from_db()
    assert c.sla_reminder_sent is True
    assert ComplaintTransition.objects.filter(
        complaint=c,
        actor_role="system",
        remarks__contains="Pre-breach SLA reminder",
    ).exists()
