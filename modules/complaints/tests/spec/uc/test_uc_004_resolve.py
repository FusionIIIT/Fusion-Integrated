"""UC-004 – Resolve Complaint tests.

Scenarios:
- Successful resolution (complaint in_progress with verification_required='user' moves to 'resolved')
- Missing resolution details (validation error)
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_004_successful_resolution(api_client, stub_iam, make_session, complaint_factory):
    """Handler resolves an in_progress complaint requiring verification; moves to resolved."""
    complaint = complaint_factory(status="in_progress", verification_required="user")
    session = make_session(user_id=6006, permissions=["complaints.complaint.resolve"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"resolution_details": "Fixed wiring"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/resolve/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolution_details"] == payload["resolution_details"]

@pytest.mark.django_db
def test_uc_004_missing_details(api_client, stub_iam, make_session, complaint_factory):
    """Missing resolution details should result in a validation error."""
    complaint = complaint_factory(status="in_progress")
    session = make_session(user_id=6006, permissions=["complaints.complaint.resolve"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/resolve/", payload, format="json")
    # implementation‑derived error status (400 Bad Request)
    assert response.status_code == 400
