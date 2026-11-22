"""UC-003 – Progress Update tests.

Scenarios:
- Valid progress (advances status to in_progress and records remarks)
- Invalid state / missing input (empty progress notes return 400 Bad Request)
"""

import pytest
from modules.complaints.tests.spec.helpers import complaint_factory
from modules.complaints.models import ComplaintTransition

@pytest.mark.django_db
def test_uc_003_valid_progress(api_client, stub_iam, make_session, complaint_factory):
    """Handler adds progress notes; complaint advances to in_progress and transition is logged."""
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=5005, permissions=["complaints.complaint.update"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"progress_notes": "Replaced fuse"}
    url = f"/api/v1/complaints/{complaint.id}/progress/"
    response = api_client.post(url, payload, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert ComplaintTransition.objects.filter(complaint=complaint, remarks="Replaced fuse").exists()

@pytest.mark.django_db
def test_uc_003_invalid_state(api_client, stub_iam, make_session, complaint_factory):
    """Empty progress notes should be rejected with 400 Bad Request."""
    complaint = complaint_factory(status="submitted")
    session = make_session(user_id=5005, permissions=["complaints.complaint.update"], active_role="complaint_handler")
    stub_iam(session=session)
    payload = {"progress_notes": ""}
    url = f"/api/v1/complaints/{complaint.id}/progress/"
    response = api_client.post(url, payload, format="json")
    # Implementation returns 400 for empty or invalid progress notes
    assert response.status_code == 400
