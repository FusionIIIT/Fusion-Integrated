"""BW-CMS-04 (WF-04) – Complaint Rejection Workflow.

Workflow:
Handler rejects a complaint from 'submitted' or 'in_progress' with mandatory
justification, moving it to terminal 'rejected' state (Page 4 – BW-CMS-04).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_004_rejection_from_submitted(api_client, stub_iam, make_session, complaint_factory):
    """Handler rejects a submitted complaint with valid justification."""
    complaint = complaint_factory(status="submitted")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.resolve", "complaints.complaint.view"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    reason = "Issue outside scope of institute maintenance."
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reject/",
        {"rejection_reason": reason},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == reason
    assert data["rejected_at"] is not None

@pytest.mark.django_db
def test_wf_004_rejection_from_in_progress(api_client, stub_iam, make_session, complaint_factory):
    """Handler rejects an in_progress complaint after technical assessment."""
    complaint = complaint_factory(status="in_progress")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.resolve", "complaints.complaint.view"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    reason = "Personal property; institute does not repair private electronics."
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reject/",
        {"rejection_reason": reason},
        format="json",
    )
    assert res.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == "rejected"
    assert complaint.rejection_reason == reason

@pytest.mark.django_db
def test_wf_004_rejection_terminal_cannot_reopen(api_client, stub_iam, make_session, complaint_factory):
    """A rejected complaint cannot have reopening requested (terminal state)."""
    complaint = complaint_factory(status="rejected", complainant_user_id=1001)
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.reopen", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-request/",
        {"reopening_reason": "Disagree with rejection"},
        format="json",
    )
    # Only closed complaints can be requested for reopening -> 400 Bad Request
    assert res.status_code == 400
