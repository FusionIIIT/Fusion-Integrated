"""UC-008 – Request Reopen tests.

Scenarios:
- Valid reopen request for a closed complaint (200 OK).
- Invalid request when complaint is not closed (400 Bad Request).
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_008_valid_reopen_request(api_client, stub_iam, make_session, complaint_factory):
    """Complainant requests reopening of a closed complaint."""
    complaint = complaint_factory(status="closed", complainant_user_id=10001)
    session = make_session(
        user_id=10001,
        permissions=["complaints.complaint.reopen"],
        active_role="complainant",
    )
    stub_iam(session=session)
    payload = {"reopening_reason": "Issue persists"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reopen-request/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["reopening_status"] == "pending"
    assert data["reopening_reason"] == payload["reopening_reason"]

@pytest.mark.django_db
def test_uc_008_invalid_status(api_client, stub_iam, make_session, complaint_factory):
    """Reopen request on a complaint that is not closed should fail."""
    complaint = complaint_factory(status="resolved", complainant_user_id=10001)
    session = make_session(
        user_id=10001,
        permissions=["complaints.complaint.reopen"],
        active_role="complainant",
    )
    stub_iam(session=session)
    payload = {"reopening_reason": "Issue persists"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reopen-request/", payload, format="json")
    # implementation‑derived error status (400 Bad Request)
    assert response.status_code == 400
