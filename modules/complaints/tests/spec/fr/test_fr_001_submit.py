"""FR-001 – Submit a new complaint.

Positive test verifies that a complaint is created and the required fields
are stored.  Negative tests cover missing authentication (no IAM session)
and missing mandatory fields – the service raises ``ComplaintValidationError``
which the view translates to HTTP 400.
"""

import pytest
from fusion_auth.client import IamSession

from modules.complaints.models import ComplaintCategory

@pytest.mark.django_db
def test_fr_001_positive_submission(api_client, stub_iam, make_session):
    # Grant the exact permission required for submission.
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.create"],
    )
    stub_iam(session=session)

    # Ensure an active category exists.
    ComplaintCategory.objects.get_or_create(name="Electrical", defaults={"is_active": True})

    payload = {
        "category_id": 1,
        "location": "Building A",
        "description": "Power outage",
        "priority": "high",
        "verification_required": "none",
    }
    response = api_client.post("/api/v1/complaints/", payload)
    assert response.status_code == 201
    data = response.json()
    # The response includes the created complaint fields.
    assert data["category"]["id"] == payload["category_id"]
    assert data["location"] == payload["location"]
    assert data["description"] == payload["description"]
    assert data["priority"] == payload["priority"]

@pytest.mark.django_db
def test_fr_001_missing_authentication(api_client, stub_iam):
    # No session – the request is unauthenticated.
    stub_iam(session=None)
    payload = {"category_id": 1, "location": "B", "description": "X"}
    response = api_client.post("/api/v1/complaints/", payload)
    assert response.status_code == 403

@pytest.mark.django_db
def test_fr_001_missing_required_fields(api_client, stub_iam, make_session):
    session = make_session(user_id=1001, permissions=["complaints.complaint.create"])
    stub_iam(session=session)
    # Omit description – service will raise validation error.
    payload = {"category_id": 1, "location": "B"}
    response = api_client.post("/api/v1/complaints/", payload)
    assert response.status_code == 400

