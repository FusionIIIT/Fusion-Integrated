"""Tests for FR-005: Complaint rejection.

The specification does not define exact response status codes, so the
assertions on HTTP status are derived from the current view implementation.
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


@pytest.mark.django_db
def test_positive_rejection(api_client, stub_iam, make_session, complaint_factory):
    """Handler can reject a complaint with a reason.

    Expected behaviour: the complaint status changes to ``rejected`` and the
    response contains the supplied reason. The exact HTTP status is taken from
    the implementation (typically 200 OK).
    """
    # Prepare a complaint in a state that can be rejected.
    complaint = complaint_factory(status="submitted")

    # Set up IAM session with required permission.
    make_session(
        user_id=2,
        permissions=["complaints.complaint.resolve"],
        active_role="complaint_handler",
    )

    url = f"/api/v1/complaints/{complaint.id}/reject/"
    data = {"reason": "Not a valid complaint"}
    response = api_client.post(url, data, format="json")

    # Implementation-derived status code – adjust if view changes.
    assert response.status_code == 200
    assert response.json().get("reason") == "Not a valid complaint"
    # Verify state transition.
    complaint.refresh_from_db()
    assert complaint.status == "rejected"


@pytest.mark.django_db
def test_negative_missing_reason(api_client, stub_iam, make_session, complaint_factory):
    """Rejection without a ``reason`` should be rejected by the view.

    The specification does not define the error payload; this test checks that
    the view returns a client error (derived from implementation, typically 400).
    """
    complaint = complaint_factory(status="submitted")
    make_session(
        user_id=2,
        permissions=["complaints.complaint.resolve"],
        active_role="complaint_handler",
    )
    url = f"/api/v1/complaints/{complaint.id}/reject/"
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 400
