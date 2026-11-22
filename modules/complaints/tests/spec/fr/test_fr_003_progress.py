"""FR-003 – Update complaint progress.

The service stores the supplied ``progress_notes`` as a ``ComplaintTransition``
remark.  The API returns the full ``ComplaintDetailSerializer`` which includes
the ``transitions`` list, so the test asserts that a transition with the
expected remark appears.
"""

import pytest

from modules.complaints.models import Complaint

@pytest.mark.django_db
def test_fr_003_positive_progress(api_client, stub_iam, make_session, complaint_factory):
    # Permission required for progress updates.
    session = make_session(user_id=2001, permissions=["complaints.complaint.update"])
    stub_iam(session=session)

    # Start from a submitted complaint – the service will promote it to in_progress.
    complaint = complaint_factory()
    payload = {"progress_notes": "Replaced faulty wiring"}
    url = f"/api/v1/complaints/{complaint.id}/progress/"
    resp = api_client.post(url, payload)
    assert resp.status_code == 200
    data = resp.json()
    # Status should have advanced to in_progress.
    assert data["status"] == "in_progress"
    # A transition with the progress note must be present.
    remarks = [t["remarks"] for t in data.get("transitions", [])]
    assert "Replaced faulty wiring" in remarks

@pytest.mark.django_db
def test_fr_003_missing_permission(api_client, stub_iam, make_session, complaint_factory):
    session = make_session(user_id=2001, permissions=[])
    stub_iam(session=session)
    complaint = complaint_factory()
    resp = api_client.post(f"/api/v1/complaints/{complaint.id}/progress/", {"progress_notes": "test"})
    assert resp.status_code == 403

