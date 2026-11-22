"""BW-CMS-02 (WF-02) – User-Verified Closure Workflow.

Workflow:
Complainant closes a resolved complaint when verification_required='user'
(Page 4 – BW-CMS-02).
"""

import pytest
from modules.complaints.models import ComplaintTransition
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_wf_002_user_verified_closure_happy_path(api_client, stub_iam, make_session, complaint_factory):
    """Complainant verifies and closes a resolved complaint requiring user verification."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        complainant_user_id=1001,
    )
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.close", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=session)

    payload = {"remarks": "Work inspected and approved"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", payload, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["closed_at"] is not None

    complaint.refresh_from_db()
    assert complaint.status == "closed"
    assert complaint.closed_at is not None

    # Verify closure transition logged
    assert ComplaintTransition.objects.filter(
        complaint=complaint,
        from_status="resolved",
        to_status="closed",
    ).exists()

@pytest.mark.django_db
def test_wf_002_unauthorized_user_cannot_close(api_client, stub_iam, make_session, complaint_factory):
    """Different user cannot verify or close another complainant's complaint (404 isolation)."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        complainant_user_id=1001,
    )
    unauthorized_session = make_session(
        user_id=9999,
        permissions=["complaints.complaint.close", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=unauthorized_session)

    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    assert response.status_code == 404

@pytest.mark.django_db
def test_wf_002_cannot_verify_close_unresolved_complaint(api_client, stub_iam, make_session, complaint_factory):
    """Attempting verify-close on an unresolved complaint returns 400 Bad Request."""
    complaint = complaint_factory(
        status="in_progress",
        verification_required="user",
        complainant_user_id=1001,
    )
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.close", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=session)

    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    assert response.status_code == 400
