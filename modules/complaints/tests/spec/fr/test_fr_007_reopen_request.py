"""Tests for FR-007: Complaint reopen request.

The specification defines that only the original complainant may request a
reopening of a *closed* complaint. Permissions are enforced via
``complaints.complaint.reopen``; however the view checks ownership separately.
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


@pytest.mark.django_db
def test_positive_reopen_request(api_client, stub_iam, make_session, complaint_factory):
    """Original complainant can request reopening of a closed complaint.

    The response status code is derived from the view implementation (typically
    200 OK). The complaint's ``reopen_requested`` flag becomes ``True``.
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    make_session(
        user_id=1,
        permissions=["complaints.complaint.reopen"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/reopen-request/"
    response = api_client.post(url, {"reason": "Issue persists"}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert getattr(complaint, "reopen_requested", False) is True


@pytest.mark.django_db
def test_negative_not_original_complainant(api_client, stub_iam, make_session, complaint_factory):
    """A different user cannot request reopening.

    The view should return a client error (derived from implementation, often
    403 Forbidden) and the flag must remain unset.
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    make_session(
        user_id=2,
        permissions=["complaints.complaint.reopen"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/reopen-request/"
    response = api_client.post(url, {"reason": "Issue persists"}, format="json")
    assert response.status_code == 403
    complaint.refresh_from_db()
    assert getattr(complaint, "reopen_requested", False) is False

