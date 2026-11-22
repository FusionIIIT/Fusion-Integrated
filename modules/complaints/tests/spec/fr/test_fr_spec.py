"""FR specification checks (selected obligations only; not full frozen design)."""
import pytest
from modules.complaints.domain.submission import InvalidSubmission, validate_submission
from modules.complaints.models import Complaint, ComplaintHistory, NotificationOutbox
from modules.complaints.services import complaints as svc

pytestmark = pytest.mark.django_db


def test_fr_cms_001_submission_accepted_and_recorded():
    """FR-CMS-001 / AFR-CMS-001: authenticated user's submitted complaint is recorded."""
    row = svc.submit(user_id=101, category="Facilities", description="Broken tap")
    row.refresh_from_db()
    assert row.complainant_user_id == 101
    assert row.category == "Facilities" and row.description == "Broken tap"
    assert row.submitted_at is not None
    assert row.reference is not None
    assert Complaint.objects.filter(reference=row.reference).count() == 1


def test_fr_cms_002_category_is_recorded():
    """FR-CMS-002 / AFR-CMS-002: submitted category remains available."""
    complaint = svc.submit(user_id=102, category="IT", description="Wi-Fi outage")
    assert Complaint.objects.get(pk=complaint.pk).category == "IT"


def test_fr_cms_submission_history_recorded():
    """CFR-CMS-001 / CFR-CMS-003: submission creates auditable history."""
    row = svc.submit(user_id=103, category="Hostel", description="Water shortage")
    assert ComplaintHistory.objects.filter(complaint=row, event="submitted").exists()


def test_fr_cms_submission_notification_triggered():
    """CFR-CMS-012: submission triggers a notification event, not email delivery."""
    row = svc.submit(user_id=104, category="Hostel", description="Light broken")
    assert NotificationOutbox.objects.filter(
        recipient_user_id=104, topic="complaint.submitted"
    ).count() == 1


@pytest.mark.parametrize("category,description", [("", "Details"), ("Facilities", "")])
def test_fr_cms_mandatory_fields(category, description):
    """CFR-CMS-001: missing mandatory category or description is refused."""
    before = Complaint.objects.count()
    with pytest.raises(InvalidSubmission):
        svc.submit(user_id=105, category=category, description=description)
    assert Complaint.objects.count() == before
