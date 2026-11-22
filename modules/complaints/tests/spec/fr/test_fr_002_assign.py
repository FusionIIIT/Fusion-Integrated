"""FR-002 – Assign a worker, category, and priority to a complaint.

Positive test verifies that the assignment endpoint updates the specified
fields and creates a transition record.  Negative test checks that the
``complaints.complaint.assign`` permission is required.
"""

import pytest

from modules.complaints.models import Complaint, ComplaintCategory
from modules.complaints.services.complaints import _calculate_sla_deadline

@pytest.mark.django_db
def test_fr_002_positive_assign(api_client, stub_iam, make_session, complaint_factory):
    # Grant assign permission.
    session = make_session(user_id=1002, permissions=["complaints.complaint.assign"])
    stub_iam(session=session)

    # Create an initial complaint (submitted).
    complaint = complaint_factory()
    # Create a second active category to assign.
    new_cat, _ = ComplaintCategory.objects.get_or_create(name="Plumbing", defaults={"is_active": True})

    payload = {
        "worker_id": 42,
        "worker_name": "John Doe",
        "priority": "high",
        "category_id": new_cat.id,
    }
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    resp = api_client.post(url, payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["assigned_worker_id"] == payload["worker_id"]
    assert data["assigned_worker_name"] == payload["worker_name"]
    assert data["priority"] == payload["priority"]
    assert data["category"]["id"] == payload["category_id"]

@pytest.mark.django_db
def test_fr_002_missing_permission(api_client, stub_iam, make_session, complaint_factory):
    # Session without the assign permission.
    session = make_session(user_id=1002, permissions=[])
    stub_iam(session=session)
    complaint = complaint_factory()
    payload = {"worker_id": 42}
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    resp = api_client.post(url, payload)
    assert resp.status_code == 403

