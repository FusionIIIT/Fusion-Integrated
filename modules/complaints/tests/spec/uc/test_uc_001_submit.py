"""UC-001 – Submit Complaint tests.

Covers the scenarios defined in design/UC_DESIGN.json:
- Happy path
- Missing fields
- Unauthenticated request
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_001_happy_path(api_client, stub_iam, make_session, complaint_factory):
    """Happy path: authenticated complainant creates a complaint successfully."""
    session = make_session(user_id=1001, permissions=["complaints.complaint.create"])
    stub_iam(session=session)
    # Ensure a category exists (use the same category id logic as FR)
    from modules.complaints.models import ComplaintCategory
    ComplaintCategory.objects.get_or_create(name="Electrical", defaults={"is_active": True})
    payload = {
        "category_id": 1,
        "location": "Building A",
        "description": "Power outage",
        "priority": "high",
        "verification_required": "none",
    }
    response = api_client.post("/api/v1/complaints/", payload)
    # Implementation‑derived status code (typically 201 Created)
    assert response.status_code == 201
    data = response.json()
    assert data["category"]["id"] == payload["category_id"]
    assert data["location"] == payload["location"]
    assert data["description"] == payload["description"]
    assert data["priority"] == payload["priority"]

@pytest.mark.django_db
def test_uc_001_missing_fields(api_client, stub_iam, make_session):
    """Missing required fields should result in a client error."""
    session = make_session(user_id=1001, permissions=["complaints.complaint.create"])
    stub_iam(session=session)
    payload = {"category_id": 1, "location": "Building A"}
    response = api_client.post("/api/v1/complaints/", payload)
    # Implementation‑derived error status (typically 400 Bad Request)
    assert response.status_code == 400

@pytest.mark.django_db
def test_uc_001_unauthenticated(api_client, stub_iam):
    """Unauthenticated request should be rejected."""
    stub_iam(session=None)
    payload = {"category_id": 1, "location": "B", "description": "X"}
    response = api_client.post("/api/v1/complaints/", payload)
    # Implementation returns 401 Unauthorized for unauthenticated requests
    assert response.status_code == 401
