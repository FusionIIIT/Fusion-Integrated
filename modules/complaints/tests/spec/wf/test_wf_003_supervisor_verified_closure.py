"""BW-CMS-03 (WF-03) – Supervisor-Verified Closure Workflow.

Workflow:
Supervisor closes a resolved complaint when verification_required='supervisor'
(Page 4 – BW-CMS-03).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_003_supervisor_closure_happy_path(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor verifies and closes a resolved complaint requiring supervisor verification."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="supervisor",
        complainant_user_id=1001,
    )
    session = make_session(
        user_id=3001,
        permissions=["complaints.complaint.close", "complaints.complaint.supervise"],
        active_role="complaint_supervisor",
        kind="staff",
    )
    stub_iam(session=session)

    payload = {"remarks": "Supervisor inspection conducted; standards satisfied."}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", payload, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_at"] is not None

    complaint.refresh_from_db()
    assert complaint.status == "closed"
    assert ComplaintTransition.objects.filter(
        complaint=complaint,
        from_status="resolved",
        to_status="closed",
        actor_role="complaint_supervisor",
    ).exists()

@pytest.mark.django_db
def test_wf_003_handler_cannot_close_supervisor_verified_complaint(api_client, stub_iam, make_session, complaint_factory):
    """Complaint Handler cannot verify-close a complaint requiring supervisor verification."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="supervisor",
        complainant_user_id=1001,
    )
    handler_session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.close", "complaints.complaint.view"],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=handler_session)

    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    assert response.status_code == 403
