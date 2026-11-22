"""UC specification checks of explicit submission and feedback flows."""
import pytest
from modules.complaints.domain.submission import InvalidSubmission
from modules.complaints.models import Complaint, NotificationOutbox
from modules.complaints.services import complaints as svc

pytestmark = pytest.mark.django_db


def test_uc_cms_001_main_success():
    """UC-CMS-001 Main Success Flow: acceptance, ID, timestamp, notification."""
    row = svc.submit(user_id=210, category="Facilities", description="Broken desk")
    assert row.status == "submitted"
    assert row.reference and row.submitted_at
    assert NotificationOutbox.objects.filter(topic="complaint.submitted", recipient_user_id=210).exists()


@pytest.mark.parametrize("category,description", [("", "Valid"), ("Valid", "")])
def test_uc_cms_001_missing_required_field(category, description):
    """UC-CMS-001 Alternative: missing mandatory input is not accepted."""
    before = Complaint.objects.count()
    with pytest.raises(InvalidSubmission):
        svc.submit(user_id=211, category=category, description=description)
    assert Complaint.objects.count() == before


def test_uc_cms_008_reopening_nonclosed_refused():
    """UC-CMS-008: reopening request is available for closed complaints."""
    row = svc.submit(user_id=212, category="Facilities", description="Still broken")
    with pytest.raises(InvalidSubmission):
        svc.request_reopening(reference=row.reference, user_id=212, reason="Not fixed")


def test_uc_cms_009_feedback_before_resolution_refused():
    """UC-CMS-009: feedback is accepted only after resolution or closure."""
    row = svc.submit(user_id=213, category="Facilities", description="Broken socket")
    with pytest.raises(InvalidSubmission):
        svc.submit_feedback(reference=row.reference, user_id=213, message="Feedback")
