"""UC-012 – Submit Feedback tests.

Scenarios from design/UC_DESIGN.json:
- First feedback: Complainant submits feedback for a closed complaint (201 Created).
- Duplicate feedback: Attempting to submit feedback a second time is rejected (400 Bad Request).
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_012_first_feedback(api_client, stub_iam, make_session, complaint_factory):
    """Complainant submits initial satisfaction feedback for a closed complaint."""
    complaint = complaint_factory(status="closed", complainant_user_id=14014)
    session = make_session(
        user_id=14014,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    stub_iam(session=session)
    payload = {"rating": 4, "comments": "Quick response"}
    response = api_client.post(
        f"/api/v1/complaints/{complaint.id}/feedback/",
        payload,
        format="json",
    )
    # implementation-derived success status (201 Created)
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 4
    assert data["comments"] == "Quick response"
    assert "id" in data

@pytest.mark.django_db
def test_uc_012_duplicate_feedback(api_client, stub_iam, make_session, complaint_factory):
    """Submitting duplicate feedback for the same complaint is rejected."""
    complaint = complaint_factory(status="closed", complainant_user_id=14014)
    session = make_session(
        user_id=14014,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    stub_iam(session=session)

    # First submission succeeds
    first_resp = api_client.post(
        f"/api/v1/complaints/{complaint.id}/feedback/",
        {"rating": 5, "comments": "Great service"},
        format="json",
    )
    assert first_resp.status_code == 201

    # Second submission attempt is rejected
    second_resp = api_client.post(
        f"/api/v1/complaints/{complaint.id}/feedback/",
        {"rating": 3, "comments": "Trying to submit again"},
        format="json",
    )
    # implementation-derived error status (400 Bad Request)
    assert second_resp.status_code == 400
