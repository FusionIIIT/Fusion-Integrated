"""FR-004 – Resolve a complaint.

The resolve view requires the ``complaints.complaint.resolve`` permission.
When ``verification_required`` is ``none`` the complaint is closed
directly; otherwise it moves to ``resolved``.
"""

import pytest

from modules.complaints.models import Complaint

@pytest.mark.django_db
def test_fr_004_resolve_to_resolved(api_client, stub_iam, make_session, complaint_factory):
    # Permission for resolve.
    session = make_session(user_id=3001, permissions=["complaints.complaint.resolve"])
    stub_iam(session=session)
    # Create a complaint that requires verification (so we stay in RESOLVED).
    complaint = complaint_factory(verification_required="user")
    payload = {"resolution_details": "Fixed the leak"}
    url = f"/api/v1/complaints/{complaint.id}/resolve/"
    resp = api_client.post(url, payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolution_details"] == payload["resolution_details"]

@pytest.mark.django_db
def test_fr_004_resolve_to_closed_when_no_verification(api_client, stub_iam, make_session, complaint_factory):
    session = make_session(user_id=3001, permissions=["complaints.complaint.resolve"])
    stub_iam(session=session)
    # verification_required = "none" (default) leads to immediate closure.
    complaint = complaint_factory()
    payload = {"resolution_details": "All set"}
    url = f"/api/v1/complaints/{complaint.id}/resolve/"
    resp = api_client.post(url, payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"

@pytest.mark.django_db
def test_fr_004_missing_permission(api_client, stub_iam, make_session, complaint_factory):
    session = make_session(user_id=3001, permissions=[])
    stub_iam(session=session)
    complaint = complaint_factory()
    resp = api_client.post(f"/api/v1/complaints/{complaint.id}/resolve/", {"resolution_details": "X"})
    assert resp.status_code == 403

