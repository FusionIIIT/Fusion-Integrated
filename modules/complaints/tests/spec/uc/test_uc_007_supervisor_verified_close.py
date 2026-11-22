"""UC-007 – Supervisor‑Verified Closure tests.

Scenarios:
- Supervisor closes a resolved complaint when verification_required='supervisor'.
- Unauthorized user (non‑supervisor) attempts closure and is denied.
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_007_supervisor_closure(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor closes a resolved complaint with supervisor verification required."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="supervisor",
        complainant_user_id=9009,  # original complainant
    )
    session = make_session(
        user_id=9100,
        permissions=["complaints.complaint.close"],
        active_role="complaint_supervisor",
    )
    stub_iam(session=session)
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"

@pytest.mark.django_db
def test_uc_007_unauthorized_user(api_client, stub_iam, make_session, complaint_factory):
    """A non‑supervisor (e.g., a regular handler) should be denied from closing the complaint."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="supervisor",
        complainant_user_id=9009,
    )
    session = make_session(
        user_id=9200,
        permissions=["complaints.complaint.close"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    # implementation‑derived permission error (403 Forbidden)
    assert response.status_code == 403
