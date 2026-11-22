"""UC-010 – Manual Escalation tests.

Scenarios:
- Escalate a complaint that is not already escalated (200 OK).
- Attempt to escalate an already escalated complaint (400 Bad Request).
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_010_escalate_once(api_client, stub_iam, make_session, complaint_factory):
    """Handler escalates a non‑escalated complaint manually."""
    complaint = complaint_factory(is_escalated=False)
    session = make_session(
        user_id=12012,
        permissions=["complaints.complaint.escalate"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)
    payload = {"remarks": "Requires senior review"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/escalate/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["is_escalated"] is True
    assert data["escalation_type"] == "manual"
    assert data["escalation_remarks"] == payload["remarks"]

@pytest.mark.django_db
def test_uc_010_duplicate_escalation(api_client, stub_iam, make_session, complaint_factory):
    """Attempting to escalate an already escalated complaint should fail."""
    complaint = complaint_factory(is_escalated=True, escalation_type="manual")
    session = make_session(
        user_id=12012,
        permissions=["complaints.complaint.escalate"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)
    payload = {"remarks": "Second escalation attempt"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/escalate/", payload, format="json")
    # implementation‑derived error status (400 Bad Request)
    assert response.status_code == 400
