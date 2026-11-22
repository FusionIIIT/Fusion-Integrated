"""BR-009 – Complaint ID Format Pattern.

Business Rule:
Complaint ID format follows pattern CMP-YYYYMMDD-XXXX (generated on submission)
(Page 4 – BW-CMS-01 description).
"""

import re
import pytest
from django.utils import timezone
from modules.complaints import services
from modules.complaints.models import ComplaintCategory
from modules.complaints.tests.spec.helpers import complaint_factory

COMPLAINT_ID_REGEX = re.compile(r"^CMP-\d{8}-\d{4}$")

@pytest.mark.django_db
def test_br_009_complaint_id_format_matches_pattern():
    """Generated complaint_id strictly matches the CMP-YYYYMMDD-XXXX regex pattern."""
    category, _ = ComplaintCategory.objects.get_or_create(
        name="Electrical",
        defaults={"is_active": True, "default_sla_hours": 48},
    )
    complaint = services.submit_complaint(
        complainant_user_id=1001,
        category_id=category.id,
        location="Hall 3 Room 12",
        description="Switchboard sparking",
    )
    assert COMPLAINT_ID_REGEX.match(complaint.complaint_id), (
        f"Complaint ID '{complaint.complaint_id}' does not match expected pattern CMP-YYYYMMDD-XXXX"
    )

    # Verify date portion corresponds to today in UTC/local
    today_str = timezone.now().strftime("%Y%m%d")
    assert today_str in complaint.complaint_id

@pytest.mark.django_db
def test_br_009_complaint_id_sequential_increment():
    """Consecutive submissions on the same day increment sequence number."""
    category, _ = ComplaintCategory.objects.get_or_create(
        name="Network",
        defaults={"is_active": True, "default_sla_hours": 24},
    )

    c1 = services.submit_complaint(
        complainant_user_id=1001,
        category_id=category.id,
        location="Lab 1",
        description="LAN port disconnected",
    )
    c2 = services.submit_complaint(
        complainant_user_id=1002,
        category_id=category.id,
        location="Lab 2",
        description="Wi-Fi dropouts",
    )

    seq1 = int(c1.complaint_id.split("-")[-1])
    seq2 = int(c2.complaint_id.split("-")[-1])
    assert seq2 == seq1 + 1

@pytest.mark.django_db
def test_br_009_complaint_id_via_api(api_client, stub_iam, make_session):
    """API-level: POST /api/v1/complaints/ returns compliant complaint_id format."""
    session = make_session(user_id=1001, permissions=["complaints.complaint.create"])
    stub_iam(session=session)

    category, _ = ComplaintCategory.objects.get_or_create(
        name="Sanitation",
        defaults={"is_active": True},
    )
    payload = {
        "category_id": category.id,
        "location": "Mess Hall",
        "description": "Water dispenser leak",
    }
    response = api_client.post("/api/v1/complaints/", payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert COMPLAINT_ID_REGEX.match(data["complaint_id"])
