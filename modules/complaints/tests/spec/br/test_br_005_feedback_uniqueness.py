"""BR-005 – Single Feedback Record Constraint per Complaint.

Business Rule:
Each complaint may have at most one feedback record, enforced via a OneToOne
relationship (Page 5 – DB constraint OneToOne feedback).
"""

import pytest
from django.db import IntegrityError
from modules.complaints.models import ComplaintFeedback
from modules.complaints.domain.errors import ComplaintValidationError
from modules.complaints import services
from modules.complaints.tests.spec.helpers import complaint_factory

@pytest.mark.django_db
def test_br_005_single_feedback_service_rejection(complaint_factory):
    """Service-level: Submitting second feedback raises ComplaintValidationError."""
    complaint = complaint_factory(status="closed", complainant_user_id=1001)

    # First feedback succeeds
    f1 = services.submit_feedback(
        complaint=complaint,
        complainant_user_id=1001,
        rating=5,
        comments="Great job!",
    )
    assert f1.rating == 5

    # Second feedback attempt raises validation error
    with pytest.raises(ComplaintValidationError, match="Feedback has already been submitted"):
        services.submit_feedback(
            complaint=complaint,
            complainant_user_id=1001,
            rating=4,
            comments="Second attempt",
        )

@pytest.mark.django_db
def test_br_005_duplicate_feedback_api(api_client, stub_iam, make_session, complaint_factory):
    """API-level: Second feedback submission returns 400 Bad Request."""
    complaint = complaint_factory(status="resolved", complainant_user_id=1001)
    session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.feedback"],
        active_role="complainant",
    )
    stub_iam(session=session)

    # First feedback via API
    res1 = api_client.post(
        f"/api/v1/complaints/{complaint.id}/feedback/",
        {"rating": 4, "comments": "Resolved promptly"},
        format="json",
    )
    assert res1.status_code == 201

    # Second feedback via API
    res2 = api_client.post(
        f"/api/v1/complaints/{complaint.id}/feedback/",
        {"rating": 3, "comments": "Duplicate"},
        format="json",
    )
    assert res2.status_code == 400

@pytest.mark.django_db
def test_br_005_db_level_onetoone_integrity_enforcement(complaint_factory):
    """DB-level: Direct insertion of duplicate ComplaintFeedback violates OneToOne constraint."""
    complaint = complaint_factory(status="closed", complainant_user_id=1001)

    ComplaintFeedback.objects.create(
        complaint=complaint,
        complainant_user_id=1001,
        rating=5,
    )

    with pytest.raises(IntegrityError):
        ComplaintFeedback.objects.create(
            complaint=complaint,
            complainant_user_id=1001,
            rating=1,
        )
