"""BR-006 – Single Manual Escalation Constraint.

Business Rule:
Manual escalation can be performed only once per complaint; subsequent attempts
are rejected (Page 4 – Workflow BW-CMS-07).
"""

import pytest
from modules.complaints.domain.errors import ComplaintAlreadyEscalated
from modules.complaints import services
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_br_006_manual_escalation_once_service(complaint_factory):
    """Service-level: Escalating an already escalated complaint raises ComplaintAlreadyEscalated."""
    complaint = complaint_factory(status="in_progress", is_escalated=False)

    # First escalation succeeds
    updated = services.escalate_complaint_manually(
        complaint=complaint,
        handler_user_id=2001,
        remarks="Needs supervisor attention.",
    )
    assert updated.is_escalated is True
    assert updated.escalation_type == "manual"

    # Second escalation attempt fails
    with pytest.raises(ComplaintAlreadyEscalated, match="already marked as escalated"):
        services.escalate_complaint_manually(
            complaint=updated,
            handler_user_id=2001,
            remarks="Second escalation attempt.",
        )

@pytest.mark.django_db
def test_br_006_duplicate_manual_escalation_api(api_client, stub_iam, make_session, complaint_factory):
    """API-level: Second manual escalation request returns 400 Bad Request."""
    complaint = complaint_factory(status="in_progress", is_escalated=False)
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.escalate"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    # First escalation
    res1 = api_client.post(
        f"/api/v1/complaints/{complaint.id}/escalate/",
        {"remarks": "First escalation"},
        format="json",
    )
    assert res1.status_code == 200
    assert res1.json()["is_escalated"] is True

    # Duplicate escalation attempt
    res2 = api_client.post(
        f"/api/v1/complaints/{complaint.id}/escalate/",
        {"remarks": "Duplicate escalation"},
        format="json",
    )
    assert res2.status_code == 400
