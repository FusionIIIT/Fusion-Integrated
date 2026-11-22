"""UC-002 – Assign Complaint tests.

Covers scenarios from design/UC_DESIGN.json:
- Successful assignment
- Forbidden role (student attempting assignment)
- Idempotent re‑assign same worker
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_002_successful_assignment(api_client, stub_iam, make_session, complaint_factory):
    """Handler assigns a worker to a submitted complaint successfully."""
    # Create a submitted complaint
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=2002, permissions=["complaints.complaint.assign"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"worker_id": 42, "priority": "high"}
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    response = api_client.post(url, payload, format="json")
    # Implementation‑derived status (usually 200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_worker_id"] == payload["worker_id"]
    assert data["priority"] == payload["priority"]

@pytest.mark.django_db
def test_uc_002_forbidden_role(api_client, stub_iam, make_session, complaint_factory):
    """A user without the handler permission (e.g., a student) must be forbidden from assigning."""
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=3003, permissions=["complaints.complaint.view_self"], active_role="student")
    stub_iam(session=session)
    payload = {"worker_id": 42, "priority": "high"}
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    response = api_client.post(url, payload, format="json")
    # Implementation‑derived forbidden status (usually 403 Forbidden)
    assert response.status_code == 403

@pytest.mark.django_db
def test_uc_002_idempotent_reassign(api_client, stub_iam, make_session, complaint_factory):
    """Re‑assigning the same worker should be idempotent (no error)."""
    complaint = complaint_factory(status="submitted", assigned_worker_id=42)
    session = make_session(user_id=4004, permissions=["complaints.complaint.assign"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"worker_id": 42, "priority": "high"}
    url = f"/api/v1/complaints/{complaint.id}/assign/"
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 200
    assert response.json()["assigned_worker_id"] == 42
