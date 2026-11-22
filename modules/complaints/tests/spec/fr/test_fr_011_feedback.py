"""Tests for FR-011: Submit satisfaction feedback after complaint closure.

The specification defines a OneToOne feedback constraint per complaint. The
implementation enforces this in the service layer and returns a client error
when a duplicate submission is attempted. HTTP status codes are derived from
the current view implementation (typically 200 for success, 400 for validation
errors).
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


@pytest.mark.django_db
def test_positive_feedback(api_client, stub_iam, make_session, complaint_factory):
    """Submit valid feedback for a closed complaint.

    Expected outcome: HTTP 200 and the complaint now has a related feedback
    object with the provided rating and comments.
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    make_session(
        user_id=1,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/feedback/"
    data = {"rating": 4, "comments": "Quick response"}
    response = api_client.post(url, data, format="json")
    assert response.status_code == 200
    # Verify feedback was created – the view returns the feedback representation.
    assert response.json().get("rating") == 4
    # Confirm relation exists in DB.
    complaint.refresh_from_db()
    assert hasattr(complaint, "feedback")
    assert complaint.feedback.rating == 4


@pytest.mark.django_db
def test_duplicate_feedback(api_client, stub_iam, make_session, complaint_factory):
    """Submitting feedback a second time should be rejected (client error).
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    make_session(
        user_id=1,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/feedback/"
    data = {"rating": 5, "comments": "Excellent"}
    # First submission succeeds.
    response1 = api_client.post(url, data, format="json")
    assert response1.status_code == 200
    # Second submission should fail.
    response2 = api_client.post(url, data, format="json")
    assert response2.status_code == 400


@pytest.mark.django_db
def test_rating_bounds(api_client, stub_iam, make_session, complaint_factory):
    """Ratings outside the 1‑5 inclusive range are rejected.
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    make_session(
        user_id=1,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/feedback/"
    for rating in [0, 6]:
        data = {"rating": rating, "comments": "Invalid rating"}
        resp = api_client.post(url, data, format="json")
        assert resp.status_code == 400

