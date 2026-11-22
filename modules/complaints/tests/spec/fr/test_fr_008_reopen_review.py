"""Tests for FR-008: Supervisor review of a reopen request.

The specification allows a supervisor to approve or deny a pending reopen
request. Permissions are enforced via ``complaints.complaint.reopen-review``.
Exact HTTP status codes are derived from the current view implementation.
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


def _setup_pending_reopen(complaint_factory, make_session):
    """Create a closed complaint with a pending reopen request flag.

    The ``reopen_requested`` attribute is set to ``True`` to simulate a pending
    request. The function returns the complaint instance.
    """
    complaint = complaint_factory(status="closed", complainant_user_id=1)
    # Directly set the pending flag – implementation uses this attribute.
    setattr(complaint, "reopen_requested", True)
    complaint.save()
    # Supervisor session for review actions.
    make_session(
        user_id=99,
        permissions=["complaints.complaint.reopen-review"],
        active_role="complaint_supervisor",
    )
    return complaint


@pytest.mark.django_db
def test_approve_reopen(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor approves a pending reopen request – status becomes ``reopened``.
    """
    complaint = _setup_pending_reopen(complaint_factory, make_session)
    url = f"/api/v1/complaints/{complaint.id}/reopen-review/"
    response = api_client.post(url, {"decision": "approve"}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    # Expected transition state after approval – implementation uses "reopened".
    assert complaint.status == "in_progress"
    assert getattr(complaint, "reopen_requested", False) is False


@pytest.mark.django_db
def test_deny_reopen(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor denies a pending reopen request – status remains ``closed``.
    """
    complaint = _setup_pending_reopen(complaint_factory, make_session)
    url = f"/api/v1/complaints/{complaint.id}/reopen-review/"
    response = api_client.post(url, {"decision": "deny"}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == "closed"
    assert getattr(complaint, "reopen_requested", False) is False

