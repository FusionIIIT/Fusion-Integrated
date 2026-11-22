"""BR-004 – Mandatory Rejection Reason Requirement.

Business Rule:
Rejection of a complaint requires a mandatory reason recorded in the database
(Page 4 – Workflow BW-CMS-04).
"""

import pytest
from modules.complaints.domain.errors import ComplaintValidationError
from modules.complaints import services
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_br_004_rejection_requires_non_empty_reason_service(complaint_factory):
    """Service-level: Rejecting without a reason raises ComplaintValidationError."""
    complaint = complaint_factory(status="submitted")
    with pytest.raises(ComplaintValidationError, match="Rejection reason is mandatory"):
        services.reject_complaint(
            complaint=complaint,
            actor_user_id=2001,
            rejection_reason="",
        )

    with pytest.raises(ComplaintValidationError, match="Rejection reason is mandatory"):
        services.reject_complaint(
            complaint=complaint,
            actor_user_id=2001,
            rejection_reason="   ",
        )

@pytest.mark.django_db
def test_br_004_reject_missing_reason_api(api_client, stub_iam, make_session, complaint_factory):
    """API-level: Rejecting without reason in payload returns 400 Bad Request."""
    complaint = complaint_factory(status="submitted")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.resolve"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    # Empty payload
    res1 = api_client.post(f"/api/v1/complaints/{complaint.id}/reject/", {}, format="json")
    assert res1.status_code == 400

    # Blank reason string
    res2 = api_client.post(f"/api/v1/complaints/{complaint.id}/reject/", {"rejection_reason": ""}, format="json")
    assert res2.status_code == 400

@pytest.mark.django_db
def test_br_004_valid_rejection_stores_reason(api_client, stub_iam, make_session, complaint_factory):
    """API-level: Valid rejection successfully records the reason in the database."""
    complaint = complaint_factory(status="submitted")
    session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.resolve"],
        active_role="complaint_handler",
    )
    stub_iam(session=session)

    reason = "Duplicate complaint filed for same room."
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/reject/",
        {"rejection_reason": reason},
        format="json",
    )
    assert res.status_code == 200
    complaint.refresh_from_db()
    assert complaint.status == "rejected"
    assert complaint.rejection_reason == reason
    assert complaint.rejected_at is not None
