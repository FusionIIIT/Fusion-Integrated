"""UC-011 – Automatic SLA Breach Check tests.

Scenarios:
- Trigger SLA check endpoint and verify successful response structure.
"""

import pytest

@pytest.mark.django_db
def test_uc_011_sla_check(api_client, stub_iam, make_session):
    """Execute the SLA check endpoint and expect a 200 response with expected fields."""
    # Authenticate as a user with any permission that allows accessing the endpoint (module grant is sufficient)
    session = make_session(user_id=13013, permissions=[], active_role="complaint_handler")
    stub_iam(session=session)
    response = api_client.post("/api/v1/complaints/sla-check/", {}, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    # The response should contain the two counters defined in the view
    assert "escalated_count" in data
    assert "reminders_sent" in data
    # Both values are integers (could be zero)
    assert isinstance(data["escalated_count"], int)
    assert isinstance(data["reminders_sent"], int)
