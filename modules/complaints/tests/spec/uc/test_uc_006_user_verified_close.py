"""UC-006 – User‑Verified Closure tests.

Scenarios:
- Authorized user (original complainant) closes a resolved complaint when verification_required='user'.
- Unauthorized user (different student) attempts closure and is denied.
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_uc_006_authorized_user_closure(api_client, stub_iam, make_session, complaint_factory):
    """Complainant closes a resolved complaint with user verification required."""
    # Create a resolved complaint with verification_required='user'
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        # ensure the complainant_user_id matches the session user
        complainant_user_id=8008,
    )
    session = make_session(
        user_id=8008,
        permissions=["complaints.complaint.close"],
        active_role="complainant",
    )
    stub_iam(session=session)
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    # implementation‑derived success status (200 OK)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"

@pytest.mark.django_db
def test_uc_006_unauthorized_user(api_client, stub_iam, make_session, complaint_factory):
    """A different user should be denied from closing the complaint."""
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        complainant_user_id=8008,
    )
    # Different user attempts closure
    session = make_session(
        user_id=9999,
        permissions=["complaints.complaint.close"],
        active_role="complainant",
    )
    stub_iam(session=session)
    response = api_client.post(f"/api/v1/complaints/{complaint.id}/verify-close/", {}, format="json")
    # Implementation isolation returns 404 Not Found to prevent enumeration
    assert response.status_code == 404
