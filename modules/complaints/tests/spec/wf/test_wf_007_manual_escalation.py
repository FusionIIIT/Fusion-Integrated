"""BW-CMS-07 (WF-07) – Manual Escalation Workflow.

Workflow:
Handler manually escalates an unresolved complaint for supervisory intervention;
system sets is_escalated=true and escalation_type='manual'
(Page 4 – BW-CMS-07).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_007_manual_escalation_happy_path(api_client, stub_iam, make_session, complaint_factory):
    """Handler escalates an in-progress complaint with remarks; marks complaint escalated."""
    complaint = complaint_factory(status="in_progress", is_escalated=False)
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.escalate", "complaints.complaint.view"],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=session)

    remarks = "Awaiting imported replacement part; deadline imminent."
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/escalate/",
        {"remarks": remarks},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_escalated"] is True
    assert data["escalation_type"] == "manual"
    assert data["escalated_at"] is not None
    assert data["escalation_remarks"] == remarks

    complaint.refresh_from_db()
    assert complaint.is_escalated is True
    assert complaint.escalation_type == "manual"
    assert ComplaintTransition.objects.filter(
        complaint=complaint,
        actor_role="complaint_handler",
        remarks__contains="Manual Escalation",
    ).exists()

@pytest.mark.django_db
def test_wf_007_cannot_escalate_resolved_or_closed(api_client, stub_iam, make_session, complaint_factory):
    """Attempting to escalate a resolved or closed complaint returns 400 Bad Request."""
    complaint = complaint_factory(status="resolved", is_escalated=False)
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.escalate", "complaints.complaint.view"],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/escalate/",
        {"remarks": "Escalation on resolved"},
        format="json",
    )
    assert res.status_code == 400

@pytest.mark.django_db
def test_wf_007_duplicate_escalation_rejected(api_client, stub_iam, make_session, complaint_factory):
    """Attempting to escalate an already escalated complaint returns 400 Bad Request."""
    complaint = complaint_factory(status="in_progress", is_escalated=True, escalation_type="manual")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.escalate", "complaints.complaint.view"],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/escalate/",
        {"remarks": "Second escalation attempt"},
        format="json",
    )
    assert res.status_code == 400
