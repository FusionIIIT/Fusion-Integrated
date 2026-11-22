"""Selected active CMS business rules from v1.3 specification."""
import pytest
from modules.complaints.domain.submission import InvalidSubmission, validate_submission
from modules.complaints.models import Complaint, ComplaintHistory
from modules.complaints.services import complaints as svc

pytestmark = pytest.mark.django_db


def test_br_cms_002_category_and_description_required():
    """BR-CMS-002: mandatory category/type and description validated."""
    with pytest.raises(InvalidSubmission):
        validate_submission(category="", description="A complaint")
    with pytest.raises(InvalidSubmission):
        validate_submission(category="Facilities", description="   ")


def test_br_cms_003_timestamp_recorded():
    """BR-CMS-003: accepted complaint records submission timestamp."""
    row = svc.submit(user_id=301, category="Facilities", description="Broken window")
    assert row.submitted_at is not None


def test_br_cms_006_unique_identifier():
    """BR-CMS-006: accepted complaints receive unique identifiers."""
    first = svc.submit(user_id=302, category="IT", description="Problem A")
    second = svc.submit(user_id=302, category="IT", description="Problem B")
    assert first.reference != second.reference


def test_br_cms_011_status_history():
    """BR-CMS-011: submission is preserved in complaint history."""
    row = svc.submit(user_id=303, category="Hostel", description="No water")
    assert ComplaintHistory.objects.filter(complaint=row, to_status="submitted").exists()


def test_br_cms_012_lifecycle_status_values():
    """BR-CMS-012: defined lifecycle state set."""
    assert {value for value, _ in Complaint.STATUS} == {
        "submitted", "in_progress", "resolved", "rejected", "closed"
    }


def test_br_cms_018_reopening_only_closed():
    """BR-CMS-018: open or unresolved complaint cannot be requested for reopening."""
    row = svc.submit(user_id=304, category="IT", description="Password issue")
    with pytest.raises(InvalidSubmission):
        svc.request_reopening(reference=row.reference, user_id=304, reason="Still failing")


def test_br_cms_022_feedback_eligibility():
    """BR-CMS-022: feedback before resolution or closure is refused."""
    row = svc.submit(user_id=305, category="IT", description="No network")
    with pytest.raises(InvalidSubmission):
        svc.submit_feedback(reference=row.reference, user_id=305, message="Feedback")
