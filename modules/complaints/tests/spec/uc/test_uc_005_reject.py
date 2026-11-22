"""UC-005 – Reject Complaint tests.

Scenarios:
- Valid rejection with reason (200 OK)
- Missing reason (400 Bad Request)
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_005_valid_rejection(api_client, stub_iam, make_session, complaint_factory):
    """Handler rejects a complaint with a mandatory reason."""
    # Complaint can be in submitted or in_progress; use submitted for simplicity
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=7007, permissions=["complaints.complaint.resolve"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"rejection_reason": "Invalid request"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reject/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == payload["rejection_reason"]

@pytest.mark.django_db
def test_uc_005_missing_reason(api_client, stub_iam, make_session, complaint_factory):
    """Missing rejection reason should trigger validation error."""
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=7007, permissions=["complaints.complaint.resolve"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reject/", payload, format="json")
    # implementation‑derived error status (400 Bad Request)
    assert response.status_code == 400
