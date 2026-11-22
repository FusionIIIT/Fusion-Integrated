"""UC-009 – Review Reopen Request tests.

Scenarios:
- Supervisor approves a pending reopen request (status changes to 'in_progress').
- Supervisor denies a pending reopen request (status remains 'closed').
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_009_approve(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor approves a pending reopen request, moving complaint back to in_progress."""
    # Create a complaint in closed state with a pending reopen request
    complaint = complaint_factory(
        status="closed",
        reopening_status="pending",
        reopening_reason="Issue persists",
    )
    session = make_session(
        user_id=11011,
        permissions=["complaints.complaint.supervise"],
        active_role="complaint_supervisor",
    )
    stub_iam(session=session)
    payload = {"approved": True}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reopen-review/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["reopening_status"] == "approved"

@pytest.mark.django_db
def test_uc_009_deny(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor denies a pending reopen request; complaint stays closed."""
    complaint = complaint_factory(
        status="closed",
        reopening_status="pending",
        reopening_reason="Issue persists",
    )
    session = make_session(
        user_id=11011,
        permissions=["complaints.complaint.supervise"],
        active_role="complaint_supervisor",
    )
    stub_iam(session=session)
    payload = {"approved": False, "review_remarks": "Not justified"}
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/reopen-review/", payload, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    assert data["reopening_status"] == "denied"
    assert data["reopening_review_remarks"] == payload["review_remarks"]
