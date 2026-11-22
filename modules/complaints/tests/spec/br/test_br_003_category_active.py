"""BR-003 – Inactive Complaint Category Rejection.

Business Rule:
Complaint categories must be active (boolean flag is_active=True) to be assignable
or selectable during complaint intake (Page 5 – Relational Database Schema).
"""

import pytest
from modules.complaints.models import ComplaintCategory
from modules.complaints.domain.errors import ComplaintValidationError
from modules.complaints import services

@pytest.mark.django_db
def test_br_003_submit_with_inactive_category_fails_service():
    """Service-level: Submitting a complaint with an inactive category raises ComplaintValidationError."""
    inactive_category = ComplaintCategory.objects.create(
        name="Obsolete Department",
        description="Inactive category",
        default_sla_hours=48,
        is_active=False,
    )
    with pytest.raises(ComplaintValidationError, match="Valid active complaint category is required"):
        services.submit_complaint(
            complainant_user_id=1001,
            category_id=inactive_category.id,
            location="Old Block",
            description="Inactive category submission test",
        )

@pytest.mark.django_db
def test_br_003_submit_with_inactive_category_api(api_client, stub_iam, make_session):
    """API-level: POST /api/v1/complaints/ with an inactive category returns 400 Bad Request."""
    session = make_session(user_id=1001, permissions=["complaints.complaint.create"])
    stub_iam(session=session)

    inactive_category = ComplaintCategory.objects.create(
        name="Decommissioned Hall",
        description="Inactive category",
        default_sla_hours=48,
        is_active=False,
    )
    payload = {
        "category_id": inactive_category.id,
        "location": "Old Block Room 1",
        "description": "Pipe leaking",
        "priority": "medium",
    }
    response = api_client.post("/api/v1/complaints/", payload, format="json")
    assert response.status_code == 400

@pytest.mark.django_db
def test_br_003_assign_to_inactive_category_fails_api(api_client, stub_iam, make_session, complaint_factory):
    """API-level: Assigning a complaint to an inactive category returns 400 Bad Request."""
    complaint = complaint_factory(status="submitted")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.assign"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    inactive_cat = ComplaintCategory.objects.create(
        name="Discontinued Service",
        description="Inactive category",
        default_sla_hours=24,
        is_active=False,
    )
    payload = {
        "category_id": inactive_cat.id,
        "priority": "high",
    }
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 400
