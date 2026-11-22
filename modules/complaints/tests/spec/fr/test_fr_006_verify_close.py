"""Tests for FR-006: Verify complaint closure.

Two closure paths are defined in the specification:
* User‑verified closure (original complainant)
* Supervisor‑verified closure (role ``complaint_supervisor``)

The exact HTTP status code is derived from the view implementation (usually
200 OK). Permissions are enforced via ``complaints.complaint.close``.
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


@pytest.mark.django_db
def test_user_verified_closure(api_client, stub_iam, make_session, complaint_factory):
    """Original complainant can close a resolved complaint.

    The complaint must have ``verification_required='user'``. After a successful
    request the status changes to ``closed``.
    """
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        complainant_user_id=1,
    )
    make_session(
        user_id=1,
        permissions=["complaints.complaint.close"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/verify-close/"
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == "closed"


@pytest.mark.django_db
def test_supervisor_verified_closure(api_client, stub_iam, make_session, complaint_factory):
    """Supervisor can close a resolved complaint when ``verification_required``
    is ``supervisor``.
    """
    complaint = complaint_factory(
        status="resolved",
        verification_required="supervisor",
        complainant_user_id=1,
    )
    make_session(
        user_id=99,
        permissions=["complaints.complaint.close"],
        active_role="complaint_supervisor",
    )
    url = f"/api/v1/complaints/{complaint.id}/verify-close/"
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == "closed"


@pytest.mark.django_db
def test_unauthorized_closure(api_client, stub_iam, make_session, complaint_factory):
    """A user who is not the complainant nor a supervisor cannot close.
    """
    complaint = complaint_factory(
        status="resolved",
        verification_required="user",
        complainant_user_id=1,
    )
    make_session(
        user_id=2,
        permissions=["complaints.complaint.close"],
        active_role="complainant",
    )
    url = f"/api/v1/complaints/{complaint.id}/verify-close/"
    response = api_client.post(url, {}, format="json")
    # Derived from implementation – usually 403 Forbidden.
    assert response.status_code == 403
