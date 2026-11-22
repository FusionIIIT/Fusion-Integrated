"""BW-CMS-05 (WF-05) – Reopening Request Workflow.

Workflow:
Complainant requests reopening of a closed complaint when issue persists
(Page 4 – BW-CMS-05).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_005_valid_reopen_request_by_complainant(api_client, stub_iam, make_session, complaint_factory):
    """Complainant requests reopening of closed complaint; state records pending request."""
    complaint = complaint_factory(status="closed", complainant_user_id=1001)
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.reopen", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=session)

    reason = "Tap leaking again after initial washer replacement."
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-request/",
        {"reopening_reason": reason},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "closed"
    assert data["reopening_status"] == "pending"
    assert data["reopening_reason"] == reason

    complaint.refresh_from_db()
    assert complaint.reopening_status == "pending"
    assert ComplaintTransition.objects.filter(
        complaint=complaint,
        actor_role="complainant",
        remarks__contains="Reopening requested",
    ).exists()

@pytest.mark.django_db
def test_wf_005_reopen_request_fails_on_non_closed_complaint(api_client, stub_iam, make_session, complaint_factory):
    """Attempting reopening on a non-closed (e.g., resolved) complaint returns 400 Bad Request."""
    complaint = complaint_factory(status="resolved", complainant_user_id=1001)
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.reopen", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-request/",
        {"reopening_reason": "Still broken"},
        format="json",
    )
    assert res.status_code == 400

@pytest.mark.django_db
def test_wf_005_non_owner_cannot_request_reopening(api_client, stub_iam, make_session, complaint_factory):
    """Different user cannot request reopening on another complainant's closed complaint."""
    complaint = complaint_factory(status="closed", complainant_user_id=1001)
    other_session = make_session(
        user_id=8888,
        permissions=["complaints.complaint.reopen", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=other_session)

    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reopen-request/",
        {"reopening_reason": "Interference attempt"},
        format="json",
    )
    assert res.status_code == 404
