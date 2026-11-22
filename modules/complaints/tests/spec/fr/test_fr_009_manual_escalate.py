"""Tests for FR-009: Manual escalation of a complaint.

The specification only requires that a handler can flag a complaint for manual
escalation via ``POST /{id}/escalate/``. The exact HTTP status code is derived
from the implementation (usually 200). The test verifies that the ``is_escalated``
boolean becomes ``True`` and that the ``escalation_type`` field is set to
``"manual"``.
"""

import pytest

from modules.complaints.tests.spec.helpers import complaint_factory


@pytest.mark.django_db
def test_manual_escalation(api_client, stub_iam, make_session, complaint_factory):
    """Handler can manually flag a complaint for escalation.
    """
    complaint = complaint_factory(status="in_progress", is_escalated=False)
    make_session(
        user_id=2,
        permissions=["complaints.complaint.escalate"],
        active_role="complaint_handler",
    )
    url = f"/api/v1/complaints/{complaint.id}/escalate/"
    response = api_client.post(url, {"type": "manual"}, format="json")
    assert response.status_code == 200
    complaint.refresh_from_db()
    assert complaint.is_escalated is True
    assert getattr(complaint, "escalation_type", None) == "manual"


@pytest.mark.django_db
def test_negative_already_escalated(api_client, stub_iam, make_session, complaint_factory):
    """Attempting to manually escalate an already escalated complaint should be
    rejected (client error derived from implementation, typically 400).
    """
    complaint = complaint_factory(status="in_progress", is_escalated=True)
    make_session(
        user_id=2,
        permissions=["complaints.complaint.escalate"],
        active_role="complaint_handler",
    )
    url = f"/api/v1/complaints/{complaint.id}/escalate/"
    response = api_client.post(url, {"type": "manual"}, format="json")
    assert response.status_code == 400
