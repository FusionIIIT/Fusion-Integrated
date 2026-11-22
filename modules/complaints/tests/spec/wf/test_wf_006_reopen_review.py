"""BW-CMS-06 (WF-06) – Reopening Review Workflow.

Workflow:
Supervisor reviews a pending reopening request:
- Approve: moves complaint from 'closed' back to 'in_progress' (reopening_status='approved')
- Deny: complaint remains 'closed' (reopening_status='denied')
(Page 4 – BW-CMS-06).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_006_supervisor_approves_reopening(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor approves reopening; complaint transitions from closed to in_progress."""
    complaint = complaint_factory(
        status="closed",
        reopening_status="pending",
        reopening_reason="Issue recurred",
    )
    supervisor_session = make_session(
        user_id=3001,
        permissions=["complaints.complaint.supervise", "complaints.complaint.view"],
        active_role="complaint_supervisor",
        kind="staff",
    )
    stub_iam(session=supervisor_session)

    payload = {"approved": True, "review_remarks": "Approved for re-work"}
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-review/",
        payload,
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "in_progress"
    assert data["reopening_status"] == "approved"

    complaint.refresh_from_db()
    assert complaint.status == "in_progress"
    assert complaint.reopening_status == "approved"
    assert ComplaintTransition.objects.filter(
        complaint=complaint,
        from_status="closed",
        to_status="in_progress",
        actor_role="complaint_supervisor",
    ).exists()

@pytest.mark.django_db
def test_wf_006_supervisor_denies_reopening(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor denies reopening; complaint remains closed with denied status."""
    complaint = complaint_factory(
        status="closed",
        reopening_status="pending",
        reopening_reason="Cosmetic scratch",
    )
    supervisor_session = make_session(
        user_id=3001,
        permissions=["complaints.complaint.supervise", "complaints.complaint.view"],
        active_role="complaint_supervisor",
        kind="staff",
    )
    stub_iam(session=supervisor_session)

    payload = {"approved": False, "review_remarks": "Wear and tear, not covered"}
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-review/",
        payload,
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "closed"
    assert data["reopening_status"] == "denied"
    assert data["reopening_review_remarks"] == payload["review_remarks"]

    complaint.refresh_from_db()
    assert complaint.status == "closed"
    assert complaint.reopening_status == "denied"

@pytest.mark.django_db
def test_wf_006_review_fails_when_no_pending_request(api_client, stub_iam, make_session, complaint_factory):
    """Reviewing a complaint without a pending reopening request returns 400 Bad Request."""
    complaint = complaint_factory(
        status="closed",
        reopening_status="none",
    )
    supervisor_session = make_session(
        user_id=3001,
        permissions=["complaints.complaint.supervise", "complaints.complaint.view"],
        active_role="complaint_supervisor",
        kind="staff",
    )
    stub_iam(session=supervisor_session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-review/",
        {"approved": True},
        format="json",
    )
    assert res.status_code == 400
