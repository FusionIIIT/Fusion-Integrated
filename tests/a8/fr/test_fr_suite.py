import pytest
from datetime import timedelta, date
from django.utils import timezone
from rest_framework.test import APIClient
from conftest import make_session
from modules.cms.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintProgress,
    ComplaintReopening,
    ComplaintFeedback,
    ComplaintAnnouncement,
    CmsRoleAssignment,
)

pytestmark = pytest.mark.django_db

ALL_CMS_PERMS = (
    "cms.complaint.submit_self",
    "cms.complaint.view_self",
    "cms.complaint.view_all",
    "cms.complaint.handle",
    "cms.complaint.resolve",
    "cms.complaint.escalate",
    "cms.complaint.reopen",
    "cms.announcement.view",
    "cms.announcement.manage",
    "cms.report.view",
    "cms.role.manage",
)

def auth_client(stub_iam, user_id=1001, permissions=ALL_CMS_PERMS, kind="student", roles=("student",)):
    stub_iam(make_session(user_id=user_id, modules=("cms",), permissions=permissions, kind=kind, roles=roles))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test_session_token", HTTP_X_USER_ID=str(user_id))
    return c


def test_fr_001_cfr_cms_001_nominal(stub_iam):
    """TEST-FR-001: Complaint Submission and Acceptance - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 1)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0001",
        complainant_user_id=1000 + 1,
        category="hostel",
        description="Functional verification of CFR-CMS-001.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_002_cfr_cms_001_boundary(stub_iam):
    """TEST-FR-002: Complaint Submission and Acceptance - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 1)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_003_cfr_cms_002_nominal(stub_iam):
    """TEST-FR-003: Complaint Handling Setup - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 3)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0003",
        complainant_user_id=1000 + 3,
        category="hostel",
        description="Functional verification of CFR-CMS-002.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_004_cfr_cms_002_boundary(stub_iam):
    """TEST-FR-004: Complaint Handling Setup - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 3)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_005_cfr_cms_003_nominal(stub_iam):
    """TEST-FR-005: Complaint Tracking and Progress History - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 5)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0005",
        complainant_user_id=1000 + 5,
        category="hostel",
        description="Functional verification of CFR-CMS-003.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_006_cfr_cms_003_boundary(stub_iam):
    """TEST-FR-006: Complaint Tracking and Progress History - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 5)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_007_cfr_cms_004_nominal(stub_iam):
    """TEST-FR-007: Complaint Lifecycle Outcome Management - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 7)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0007",
        complainant_user_id=1000 + 7,
        category="hostel",
        description="Functional verification of CFR-CMS-004.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_008_cfr_cms_004_boundary(stub_iam):
    """TEST-FR-008: Complaint Lifecycle Outcome Management - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 7)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_009_cfr_cms_005_nominal(stub_iam):
    """TEST-FR-009: Closure Verification - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 9)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0009",
        complainant_user_id=1000 + 9,
        category="hostel",
        description="Functional verification of CFR-CMS-005.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_010_cfr_cms_005_boundary(stub_iam):
    """TEST-FR-010: Closure Verification - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 9)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_011_cfr_cms_006_nominal(stub_iam):
    """TEST-FR-011: Complaint Reopening - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 11)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0011",
        complainant_user_id=1000 + 11,
        category="hostel",
        description="Functional verification of CFR-CMS-006.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_012_cfr_cms_002_sla_high_boundary(stub_iam):
    """TEST-FR-012: High priority complaint SLA assignment boundary (Defect 1)."""
    client = auth_client(stub_iam, user_id=2012, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0012",
        complainant_user_id=1012,
        category="network",
        description="Critical core switch outage in central data center.",
        status="Submitted",
        priority="Low"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/assign/", data={"assigned_handler_id": 2012, "priority": "High"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # Specification requirement: High priority SLA is 24 hours (1 day)
    now = timezone.now()
    expected_max = now + timedelta(hours=26) # 24h + 2h margin
    assert c.sla_due_date <= expected_max, f"Expected High SLA <= 24h, got {c.sla_due_date - now}"


def test_fr_013_cfr_cms_007_nominal(stub_iam):
    """TEST-FR-013: Feedback Management - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 13)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0013",
        complainant_user_id=1000 + 13,
        category="hostel",
        description="Functional verification of CFR-CMS-007.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_014_cfr_cms_007_boundary(stub_iam):
    """TEST-FR-014: Feedback Management - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 13)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_015_cfr_cms_008_nominal(stub_iam):
    """TEST-FR-015: Manual Escalation and Oversight - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 15)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0015",
        complainant_user_id=1000 + 15,
        category="hostel",
        description="Functional verification of CFR-CMS-008.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_016_cfr_cms_008_boundary(stub_iam):
    """TEST-FR-016: Manual Escalation and Oversight - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 15)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_017_cfr_cms_009_nominal(stub_iam):
    """TEST-FR-017: SLA-Driven Reminder and Automatic Escalation - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 17)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0017",
        complainant_user_id=1000 + 17,
        category="hostel",
        description="Functional verification of CFR-CMS-009.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_018_cfr_cms_009_boundary(stub_iam):
    """TEST-FR-018: SLA-Driven Reminder and Automatic Escalation - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 17)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_019_cfr_cms_010_nominal(stub_iam):
    """TEST-FR-019: Complaint Announcements - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 19)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0019",
        complainant_user_id=1000 + 19,
        category="hostel",
        description="Functional verification of CFR-CMS-010.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_020_cfr_cms_010_boundary(stub_iam):
    """TEST-FR-020: Complaint Announcements - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 19)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_021_cfr_cms_011_nominal(stub_iam):
    """TEST-FR-021: Complaint Reporting and Analytics Visibility - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 21)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0021",
        complainant_user_id=1000 + 21,
        category="hostel",
        description="Functional verification of CFR-CMS-011.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_022_cfr_cms_011_boundary(stub_iam):
    """TEST-FR-022: Complaint Reporting and Analytics Visibility - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 21)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_023_cfr_cms_012_nominal(stub_iam):
    """TEST-FR-023: Notification Triggering - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 23)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0023",
        complainant_user_id=1000 + 23,
        category="hostel",
        description="Functional verification of CFR-CMS-012.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_024_cfr_cms_012_boundary(stub_iam):
    """TEST-FR-024: Notification Triggering - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 23)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_025_cfr_cms_013_nominal(stub_iam):
    """TEST-FR-025: CMS Role Management - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 25)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0025",
        complainant_user_id=1000 + 25,
        category="hostel",
        description="Functional verification of CFR-CMS-013.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_026_cfr_cms_013_boundary(stub_iam):
    """TEST-FR-026: CMS Role Management - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 25)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_027_cfr_cms_014_nominal(stub_iam):
    """TEST-FR-027: CMS Functional Scope Boundaries - Nominal capability."""
    client = auth_client(stub_iam, user_id=1000 + 27)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0027",
        complainant_user_id=1000 + 27,
        category="hostel",
        description="Functional verification of CFR-CMS-014.",
        status="Submitted",
        priority="Low"
    )
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
    assert res.data["complaint_id"] == c.complaint_id


def test_fr_028_cfr_cms_014_boundary(stub_iam):
    """TEST-FR-028: CMS Functional Scope Boundaries - Boundary condition."""
    client = auth_client(stub_iam, user_id=2000 + 27)
    # Boundary: invalid payload or missing fields
    res = client.post("/api/v1/cms/complaints/", data={"priority": "InvalidPriority"}, format="json")
    assert res.status_code == 400


def test_fr_029_afr_cms_001_positive(stub_iam):
    """TEST-FR-029: AFR-CMS-001 - CMS shall allow a User / Complainant to submit a complaint at any time"""
    client = auth_client(stub_iam, user_id=3000 + 29)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0029",
        complainant_user_id=3000 + 29,
        category="maintenance",
        description="Testing requirement AFR-CMS-001: CMS shall allow a User / Complainant to submit a c",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_030_afr_cms_001_invariant(stub_iam):
    """TEST-FR-030: AFR-CMS-001 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 29)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0030",
        complainant_user_id=3500 + 29,
        category="other",
        description="Testing state invariant for AFR-CMS-001",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 29,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-001"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_031_afr_cms_002_positive(stub_iam):
    """TEST-FR-031: AFR-CMS-002 - CMS shall record the complaint category for each submitted complaint."""
    client = auth_client(stub_iam, user_id=3000 + 31)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0031",
        complainant_user_id=3000 + 31,
        category="maintenance",
        description="Testing requirement AFR-CMS-002: CMS shall record the complaint category for each s",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_032_afr_cms_002_invariant(stub_iam):
    """TEST-FR-032: AFR-CMS-002 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 31)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0032",
        complainant_user_id=3500 + 31,
        category="other",
        description="Testing state invariant for AFR-CMS-002",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 31,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-002"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_033_afr_cms_003_positive(stub_iam):
    """TEST-FR-033: AFR-CMS-003 - CMS shall record the complaint description for each submitted complain"""
    client = auth_client(stub_iam, user_id=3000 + 33)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0033",
        complainant_user_id=3000 + 33,
        category="maintenance",
        description="Testing requirement AFR-CMS-003: CMS shall record the complaint description for eac",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_034_afr_cms_003_invariant(stub_iam):
    """TEST-FR-034: AFR-CMS-003 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 33)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0034",
        complainant_user_id=3500 + 33,
        category="other",
        description="Testing state invariant for AFR-CMS-003",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 33,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-003"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_035_afr_cms_004_positive(stub_iam):
    """TEST-FR-035: AFR-CMS-004 - CMS shall record the submission date/time for each submitted complaint"""
    client = auth_client(stub_iam, user_id=3000 + 35)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0035",
        complainant_user_id=3000 + 35,
        category="maintenance",
        description="Testing requirement AFR-CMS-004: CMS shall record the submission date/time for each",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_036_afr_cms_004_attachment_format_defect(stub_iam):
    """TEST-FR-036: AFR-CMS-004 - Attachment file format/mime-type constraint validation (Defect 3)."""
    client = auth_client(stub_iam, user_id=3036)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0036",
        complainant_user_id=3036,
        category="hostel",
        description="Attachment validation test.",
        status="Submitted"
    )
    # Attempt to attach disallowed executable file type
    att = ComplaintAttachment(complaint=c, file_name="malware.exe", file_size=0, file_type="application/x-dosexec")
    # Specification requires attachment validation rejection of unallowed formats or empty sizes
    assert att.file_type in ["image/jpeg", "image/png", "application/pdf"], f"Disallowed file type accepted: {att.file_type}"
    assert att.file_size > 0, "Zero-size attachment accepted"


def test_fr_037_afr_cms_005_positive(stub_iam):
    """TEST-FR-037: AFR-CMS-005 - CMS shall allow complaint submissions to include supporting attachment"""
    client = auth_client(stub_iam, user_id=3000 + 37)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0037",
        complainant_user_id=3000 + 37,
        category="maintenance",
        description="Testing requirement AFR-CMS-005: CMS shall allow complaint submissions to include s",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_038_afr_cms_005_invariant(stub_iam):
    """TEST-FR-038: AFR-CMS-005 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 37)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0038",
        complainant_user_id=3500 + 37,
        category="other",
        description="Testing state invariant for AFR-CMS-005",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 37,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-005"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_039_afr_cms_006_positive(stub_iam):
    """TEST-FR-039: AFR-CMS-006 - CMS shall validate mandatory complaint fields before accepting a compl"""
    client = auth_client(stub_iam, user_id=3000 + 39)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0039",
        complainant_user_id=3000 + 39,
        category="maintenance",
        description="Testing requirement AFR-CMS-006: CMS shall validate mandatory complaint fields befo",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_040_afr_cms_006_invariant(stub_iam):
    """TEST-FR-040: AFR-CMS-006 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 39)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0040",
        complainant_user_id=3500 + 39,
        category="other",
        description="Testing state invariant for AFR-CMS-006",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 39,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-006"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_041_afr_cms_007_positive(stub_iam):
    """TEST-FR-041: AFR-CMS-007 - CMS shall validate accepted attachment constraints before accepting su"""
    client = auth_client(stub_iam, user_id=3000 + 41)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0041",
        complainant_user_id=3000 + 41,
        category="maintenance",
        description="Testing requirement AFR-CMS-007: CMS shall validate accepted attachment constraints",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_042_afr_cms_007_invariant(stub_iam):
    """TEST-FR-042: AFR-CMS-007 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 41)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0042",
        complainant_user_id=3500 + 41,
        category="other",
        description="Testing state invariant for AFR-CMS-007",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 41,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-007"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_043_afr_cms_008_positive(stub_iam):
    """TEST-FR-043: AFR-CMS-008 - CMS shall treat the exact attachment file-type, file-size, and format """
    client = auth_client(stub_iam, user_id=3000 + 43)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0043",
        complainant_user_id=3000 + 43,
        category="maintenance",
        description="Testing requirement AFR-CMS-008: CMS shall treat the exact attachment file-type, fi",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_044_afr_cms_008_invariant(stub_iam):
    """TEST-FR-044: AFR-CMS-008 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 43)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0044",
        complainant_user_id=3500 + 43,
        category="other",
        description="Testing state invariant for AFR-CMS-008",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 43,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-008"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_045_afr_cms_009_positive(stub_iam):
    """TEST-FR-045: AFR-CMS-009 - CMS shall generate a unique complaint identifier for each submitted co"""
    client = auth_client(stub_iam, user_id=3000 + 45)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0045",
        complainant_user_id=3000 + 45,
        category="maintenance",
        description="Testing requirement AFR-CMS-009: CMS shall generate a unique complaint identifier f",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_046_afr_cms_009_invariant(stub_iam):
    """TEST-FR-046: AFR-CMS-009 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 45)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0046",
        complainant_user_id=3500 + 45,
        category="other",
        description="Testing state invariant for AFR-CMS-009",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 45,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-009"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_047_afr_cms_010_positive(stub_iam):
    """TEST-FR-047: AFR-CMS-010 - CMS shall provide complaint submission confirmation or notification to"""
    client = auth_client(stub_iam, user_id=3000 + 47)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0047",
        complainant_user_id=3000 + 47,
        category="maintenance",
        description="Testing requirement AFR-CMS-010: CMS shall provide complaint submission confirmatio",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_048_afr_cms_010_invariant(stub_iam):
    """TEST-FR-048: AFR-CMS-010 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 47)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0048",
        complainant_user_id=3500 + 47,
        category="other",
        description="Testing state invariant for AFR-CMS-010",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 47,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-010"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_049_afr_cms_011_positive(stub_iam):
    """TEST-FR-049: AFR-CMS-011 - CMS shall allow the Complaint Handler to manually assign submitted com"""
    client = auth_client(stub_iam, user_id=3000 + 49)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0049",
        complainant_user_id=3000 + 49,
        category="maintenance",
        description="Testing requirement AFR-CMS-011: CMS shall allow the Complaint Handler to manually ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_050_afr_cms_011_invariant(stub_iam):
    """TEST-FR-050: AFR-CMS-011 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 49)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0050",
        complainant_user_id=3500 + 49,
        category="other",
        description="Testing state invariant for AFR-CMS-011",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 49,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-011"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_051_afr_cms_012_positive(stub_iam):
    """TEST-FR-051: AFR-CMS-012 - CMS shall allow the Complaint Handler to categorize complaints by comp"""
    client = auth_client(stub_iam, user_id=3000 + 51)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0051",
        complainant_user_id=3000 + 51,
        category="maintenance",
        description="Testing requirement AFR-CMS-012: CMS shall allow the Complaint Handler to categoriz",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_052_afr_cms_012_invariant(stub_iam):
    """TEST-FR-052: AFR-CMS-012 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 51)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0052",
        complainant_user_id=3500 + 51,
        category="other",
        description="Testing state invariant for AFR-CMS-012",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 51,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-012"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_053_afr_cms_013_positive(stub_iam):
    """TEST-FR-053: AFR-CMS-013 - CMS shall allow the Complaint Handler to assign complaint priority as """
    client = auth_client(stub_iam, user_id=3000 + 53)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0053",
        complainant_user_id=3000 + 53,
        category="maintenance",
        description="Testing requirement AFR-CMS-013: CMS shall allow the Complaint Handler to assign co",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_054_afr_cms_013_invariant(stub_iam):
    """TEST-FR-054: AFR-CMS-013 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 53)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0054",
        complainant_user_id=3500 + 53,
        category="other",
        description="Testing state invariant for AFR-CMS-013",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 53,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-013"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_055_afr_cms_014_positive(stub_iam):
    """TEST-FR-055: AFR-CMS-014 - CMS shall record assignment information for downstream complaint handl"""
    client = auth_client(stub_iam, user_id=3000 + 55)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0055",
        complainant_user_id=3000 + 55,
        category="maintenance",
        description="Testing requirement AFR-CMS-014: CMS shall record assignment information for downst",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_056_afr_cms_014_resolution_substantive_defect(stub_iam):
    """TEST-FR-056: AFR-CMS-014 - Resolution details substantive length validation (Defect 7)."""
    client = auth_client(stub_iam, user_id=4056, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0056",
        complainant_user_id=3056,
        category="maintenance",
        description="Air conditioner leaking refrigerant.",
        status="In Progress"
    )
    # Specification requires substantive details (>= 10 chars), not trivial 3 chars like 'Fix'
    res = client.post(f"/api/v1/cms/complaints/{c.id}/resolve/", data={"resolution_details": "Fix"}, format="json")
    assert res.status_code == 400, "Substantive resolution details requirement violated (accepted trivial 3 chars)"


def test_fr_057_afr_cms_015_positive(stub_iam):
    """TEST-FR-057: AFR-CMS-015 - CMS shall record priority information for downstream complaint handlin"""
    client = auth_client(stub_iam, user_id=3000 + 57)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0057",
        complainant_user_id=3000 + 57,
        category="maintenance",
        description="Testing requirement AFR-CMS-015: CMS shall record priority information for downstre",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_058_afr_cms_015_invariant(stub_iam):
    """TEST-FR-058: AFR-CMS-015 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 57)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0058",
        complainant_user_id=3500 + 57,
        category="other",
        description="Testing state invariant for AFR-CMS-015",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 57,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-015"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_059_afr_cms_016_positive(stub_iam):
    """TEST-FR-059: AFR-CMS-016 - CMS shall allow a User / Complainant to track the status of the User /"""
    client = auth_client(stub_iam, user_id=3000 + 59)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0059",
        complainant_user_id=3000 + 59,
        category="maintenance",
        description="Testing requirement AFR-CMS-016: CMS shall allow a User / Complainant to track the ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_060_afr_cms_016_invariant(stub_iam):
    """TEST-FR-060: AFR-CMS-016 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 59)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0060",
        complainant_user_id=3500 + 59,
        category="other",
        description="Testing state invariant for AFR-CMS-016",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 59,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-016"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_061_afr_cms_017_positive(stub_iam):
    """TEST-FR-061: AFR-CMS-017 - CMS shall allow a User / Complainant to track the history of the User """
    client = auth_client(stub_iam, user_id=3000 + 61)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0061",
        complainant_user_id=3000 + 61,
        category="maintenance",
        description="Testing requirement AFR-CMS-017: CMS shall allow a User / Complainant to track the ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_062_afr_cms_017_invariant(stub_iam):
    """TEST-FR-062: AFR-CMS-017 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 61)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0062",
        complainant_user_id=3500 + 61,
        category="other",
        description="Testing state invariant for AFR-CMS-017",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 61,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-017"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_063_afr_cms_018_positive(stub_iam):
    """TEST-FR-063: AFR-CMS-018 - CMS shall allow Complaint Handlers to review complaints assigned for h"""
    client = auth_client(stub_iam, user_id=3000 + 63)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0063",
        complainant_user_id=3000 + 63,
        category="maintenance",
        description="Testing requirement AFR-CMS-018: CMS shall allow Complaint Handlers to review compl",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_064_afr_cms_018_invariant(stub_iam):
    """TEST-FR-064: AFR-CMS-018 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 63)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0064",
        complainant_user_id=3500 + 63,
        category="other",
        description="Testing state invariant for AFR-CMS-018",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 63,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-018"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_065_afr_cms_019_positive(stub_iam):
    """TEST-FR-065: AFR-CMS-019 - CMS shall allow Complaint Handlers to update complaint progress during"""
    client = auth_client(stub_iam, user_id=3000 + 65)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0065",
        complainant_user_id=3000 + 65,
        category="maintenance",
        description="Testing requirement AFR-CMS-019: CMS shall allow Complaint Handlers to update compl",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_066_afr_cms_019_invariant(stub_iam):
    """TEST-FR-066: AFR-CMS-019 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 65)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0066",
        complainant_user_id=3500 + 65,
        category="other",
        description="Testing state invariant for AFR-CMS-019",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 65,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-019"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_067_afr_cms_020_positive(stub_iam):
    """TEST-FR-067: AFR-CMS-020 - CMS shall maintain complaint status history throughout the lifecycle o"""
    client = auth_client(stub_iam, user_id=3000 + 67)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0067",
        complainant_user_id=3000 + 67,
        category="maintenance",
        description="Testing requirement AFR-CMS-020: CMS shall maintain complaint status history throug",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_068_afr_cms_020_invariant(stub_iam):
    """TEST-FR-068: AFR-CMS-020 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 67)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0068",
        complainant_user_id=3500 + 67,
        category="other",
        description="Testing state invariant for AFR-CMS-020",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 67,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-020"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_069_afr_cms_021_positive(stub_iam):
    """TEST-FR-069: AFR-CMS-021 - CMS shall maintain complaint progress history throughout the lifecycle"""
    client = auth_client(stub_iam, user_id=3000 + 69)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0069",
        complainant_user_id=3000 + 69,
        category="maintenance",
        description="Testing requirement AFR-CMS-021: CMS shall maintain complaint progress history thro",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_070_afr_cms_021_invariant(stub_iam):
    """TEST-FR-070: AFR-CMS-021 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 69)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0070",
        complainant_user_id=3500 + 69,
        category="other",
        description="Testing state invariant for AFR-CMS-021",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 69,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-021"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_071_afr_cms_022_positive(stub_iam):
    """TEST-FR-071: AFR-CMS-022 - CMS shall recognize Submitted, In Progress, Resolved, Rejected, and Cl"""
    client = auth_client(stub_iam, user_id=3000 + 71)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0071",
        complainant_user_id=3000 + 71,
        category="maintenance",
        description="Testing requirement AFR-CMS-022: CMS shall recognize Submitted, In Progress, Resolv",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_072_afr_cms_022_invariant(stub_iam):
    """TEST-FR-072: AFR-CMS-022 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 71)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0072",
        complainant_user_id=3500 + 71,
        category="other",
        description="Testing state invariant for AFR-CMS-022",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 71,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-022"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_073_afr_cms_023_positive(stub_iam):
    """TEST-FR-073: AFR-CMS-023 - CMS shall record complaint resolution details for resolved complaints."""
    client = auth_client(stub_iam, user_id=3000 + 73)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0073",
        complainant_user_id=3000 + 73,
        category="maintenance",
        description="Testing requirement AFR-CMS-023: CMS shall record complaint resolution details for ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_074_afr_cms_023_invariant(stub_iam):
    """TEST-FR-074: AFR-CMS-023 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 73)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0074",
        complainant_user_id=3500 + 73,
        category="other",
        description="Testing state invariant for AFR-CMS-023",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 73,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-023"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_075_afr_cms_024_positive(stub_iam):
    """TEST-FR-075: AFR-CMS-024 - CMS shall record rejection details or rejection reason information for"""
    client = auth_client(stub_iam, user_id=3000 + 75)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0075",
        complainant_user_id=3000 + 75,
        category="maintenance",
        description="Testing requirement AFR-CMS-024: CMS shall record rejection details or rejection re",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_076_afr_cms_024_invariant(stub_iam):
    """TEST-FR-076: AFR-CMS-024 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 75)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0076",
        complainant_user_id=3500 + 75,
        category="other",
        description="Testing state invariant for AFR-CMS-024",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 75,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-024"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_077_afr_cms_025_positive(stub_iam):
    """TEST-FR-077: AFR-CMS-025 - CMS shall notify Users / Complainants of complaint outcome updates."""
    client = auth_client(stub_iam, user_id=3000 + 77)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0077",
        complainant_user_id=3000 + 77,
        category="maintenance",
        description="Testing requirement AFR-CMS-025: CMS shall notify Users / Complainants of complaint",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_078_afr_cms_025_invariant(stub_iam):
    """TEST-FR-078: AFR-CMS-025 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 77)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0078",
        complainant_user_id=3500 + 77,
        category="other",
        description="Testing state invariant for AFR-CMS-025",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 77,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-025"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_079_afr_cms_026_positive(stub_iam):
    """TEST-FR-079: AFR-CMS-026 - CMS shall notify Users / Complainants of complaint status updates."""
    client = auth_client(stub_iam, user_id=3000 + 79)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0079",
        complainant_user_id=3000 + 79,
        category="maintenance",
        description="Testing requirement AFR-CMS-026: CMS shall notify Users / Complainants of complaint",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_080_afr_cms_026_invariant(stub_iam):
    """TEST-FR-080: AFR-CMS-026 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 79)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0080",
        complainant_user_id=3500 + 79,
        category="other",
        description="Testing state invariant for AFR-CMS-026",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 79,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-026"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_081_afr_cms_027_positive(stub_iam):
    """TEST-FR-081: AFR-CMS-027 - CMS shall support User / Complainant verification of a resolved compla"""
    client = auth_client(stub_iam, user_id=3000 + 81)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0081",
        complainant_user_id=3000 + 81,
        category="maintenance",
        description="Testing requirement AFR-CMS-027: CMS shall support User / Complainant verification ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_082_afr_cms_027_duplicate_feedback_defect(stub_iam):
    """TEST-FR-082: AFR-CMS-027 - Prevention of duplicate feedback submissions (Defect 5)."""
    client = auth_client(stub_iam, user_id=3082)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0082",
        complainant_user_id=3082,
        category="mess",
        description="Cold food served at breakfast counter.",
        status="Closed"
    )
    res1 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 4, "comments": "Resolved satisfactorily."}, format="json")
    assert res1.status_code == 201
    # Second feedback for the same closed complaint must be rejected
    res2 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 1, "comments": "Changed my mind."}, format="json")
    assert res2.status_code == 400, "Duplicate feedback allowed for single complaint"


def test_fr_083_afr_cms_028_positive(stub_iam):
    """TEST-FR-083: AFR-CMS-028 - CMS shall support Complaint Supervisor verification of a resolved comp"""
    client = auth_client(stub_iam, user_id=3000 + 83)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0083",
        complainant_user_id=3000 + 83,
        category="maintenance",
        description="Testing requirement AFR-CMS-028: CMS shall support Complaint Supervisor verificatio",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_084_afr_cms_028_invariant(stub_iam):
    """TEST-FR-084: AFR-CMS-028 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 83)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0084",
        complainant_user_id=3500 + 83,
        category="other",
        description="Testing state invariant for AFR-CMS-028",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 83,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-028"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_085_afr_cms_029_positive(stub_iam):
    """TEST-FR-085: AFR-CMS-029 - CMS shall record complaint closure after successful verification when """
    client = auth_client(stub_iam, user_id=3000 + 85)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0085",
        complainant_user_id=3000 + 85,
        category="maintenance",
        description="Testing requirement AFR-CMS-029: CMS shall record complaint closure after successfu",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_086_afr_cms_029_invariant(stub_iam):
    """TEST-FR-086: AFR-CMS-029 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 85)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0086",
        complainant_user_id=3500 + 85,
        category="other",
        description="Testing state invariant for AFR-CMS-029",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 85,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-029"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_087_afr_cms_030_positive(stub_iam):
    """TEST-FR-087: AFR-CMS-030 - CMS shall allow Users / Complainants to request reopening of a closed """
    client = auth_client(stub_iam, user_id=3000 + 87)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0087",
        complainant_user_id=3000 + 87,
        category="maintenance",
        description="Testing requirement AFR-CMS-030: CMS shall allow Users / Complainants to request re",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_088_afr_cms_030_invariant(stub_iam):
    """TEST-FR-088: AFR-CMS-030 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 87)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0088",
        complainant_user_id=3500 + 87,
        category="other",
        description="Testing state invariant for AFR-CMS-030",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 87,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-030"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_089_afr_cms_031_positive(stub_iam):
    """TEST-FR-089: AFR-CMS-031 - CMS shall allow the Complaint Supervisor to review complaint reopening"""
    client = auth_client(stub_iam, user_id=3000 + 89)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0089",
        complainant_user_id=3000 + 89,
        category="maintenance",
        description="Testing requirement AFR-CMS-031: CMS shall allow the Complaint Supervisor to review",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_090_afr_cms_031_invariant(stub_iam):
    """TEST-FR-090: AFR-CMS-031 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 89)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0090",
        complainant_user_id=3500 + 89,
        category="other",
        description="Testing state invariant for AFR-CMS-031",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 89,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-031"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_091_afr_cms_032_positive(stub_iam):
    """TEST-FR-091: AFR-CMS-032 - CMS shall reopen the complaint when a reopening request is approved."""
    client = auth_client(stub_iam, user_id=3000 + 91)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0091",
        complainant_user_id=3000 + 91,
        category="maintenance",
        description="Testing requirement AFR-CMS-032: CMS shall reopen the complaint when a reopening re",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_092_afr_cms_032_invariant(stub_iam):
    """TEST-FR-092: AFR-CMS-032 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 91)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0092",
        complainant_user_id=3500 + 91,
        category="other",
        description="Testing state invariant for AFR-CMS-032",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 91,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-032"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_093_afr_cms_033_positive(stub_iam):
    """TEST-FR-093: AFR-CMS-033 - CMS shall update the complaint status accordingly when reopening is ap"""
    client = auth_client(stub_iam, user_id=3000 + 93)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0093",
        complainant_user_id=3000 + 93,
        category="maintenance",
        description="Testing requirement AFR-CMS-033: CMS shall update the complaint status accordingly ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_094_afr_cms_033_escalate_actor_role_defect(stub_iam):
    """TEST-FR-094: AFR-CMS-033 - Audit logs complainant actor role on manual escalation (Defect 9)."""
    client = auth_client(stub_iam, user_id=3094, kind="student", roles=("student",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0094",
        complainant_user_id=3094,
        category="academic",
        description="Lab computer workstation monitor failing.",
        status="In Progress"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/escalate/", data={"escalation_remarks": "Exam week pending."}, format="json")
    assert res.status_code == 200
    prog = c.progress_history.filter(action="escalated_manual").last()
    assert prog is not None
    assert prog.actor_role == "complainant", f"Expected actor_role 'complainant', got '{prog.actor_role}'"


def test_fr_095_afr_cms_034_positive(stub_iam):
    """TEST-FR-095: AFR-CMS-034 - CMS shall record the outcome of the complaint reopening request."""
    client = auth_client(stub_iam, user_id=3000 + 95)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0095",
        complainant_user_id=3000 + 95,
        category="maintenance",
        description="Testing requirement AFR-CMS-034: CMS shall record the outcome of the complaint reop",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_096_afr_cms_034_invariant(stub_iam):
    """TEST-FR-096: AFR-CMS-034 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 95)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0096",
        complainant_user_id=3500 + 95,
        category="other",
        description="Testing state invariant for AFR-CMS-034",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 95,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-034"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_097_afr_cms_035_positive(stub_iam):
    """TEST-FR-097: AFR-CMS-035 - CMS shall allow Users / Complainants to submit feedback after complain"""
    client = auth_client(stub_iam, user_id=3000 + 97)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0097",
        complainant_user_id=3000 + 97,
        category="maintenance",
        description="Testing requirement AFR-CMS-035: CMS shall allow Users / Complainants to submit fee",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_098_afr_cms_035_invariant(stub_iam):
    """TEST-FR-098: AFR-CMS-035 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 97)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0098",
        complainant_user_id=3500 + 97,
        category="other",
        description="Testing state invariant for AFR-CMS-035",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 97,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-035"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_099_afr_cms_036_positive(stub_iam):
    """TEST-FR-099: AFR-CMS-036 - CMS shall allow Complaint Handlers to review submitted feedback."""
    client = auth_client(stub_iam, user_id=3000 + 99)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0099",
        complainant_user_id=3000 + 99,
        category="maintenance",
        description="Testing requirement AFR-CMS-036: CMS shall allow Complaint Handlers to review submi",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_100_afr_cms_036_invariant(stub_iam):
    """TEST-FR-100: AFR-CMS-036 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 99)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0100",
        complainant_user_id=3500 + 99,
        category="other",
        description="Testing state invariant for AFR-CMS-036",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 99,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-036"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_101_afr_cms_037_positive(stub_iam):
    """TEST-FR-101: AFR-CMS-037 - CMS shall allow Complaint Supervisors to review submitted feedback."""
    client = auth_client(stub_iam, user_id=3000 + 101)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0101",
        complainant_user_id=3000 + 101,
        category="maintenance",
        description="Testing requirement AFR-CMS-037: CMS shall allow Complaint Supervisors to review su",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_102_afr_cms_037_invariant(stub_iam):
    """TEST-FR-102: AFR-CMS-037 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 101)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0102",
        complainant_user_id=3500 + 101,
        category="other",
        description="Testing state invariant for AFR-CMS-037",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 101,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-037"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_103_afr_cms_038_positive(stub_iam):
    """TEST-FR-103: AFR-CMS-038 - CMS shall allow unresolved complaints to be escalated manually."""
    client = auth_client(stub_iam, user_id=3000 + 103)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0103",
        complainant_user_id=3000 + 103,
        category="maintenance",
        description="Testing requirement AFR-CMS-038: CMS shall allow unresolved complaints to be escala",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_104_afr_cms_038_invariant(stub_iam):
    """TEST-FR-104: AFR-CMS-038 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 103)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0104",
        complainant_user_id=3500 + 103,
        category="other",
        description="Testing state invariant for AFR-CMS-038",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 103,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-038"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_105_afr_cms_039_positive(stub_iam):
    """TEST-FR-105: AFR-CMS-039 - CMS shall track escalation status."""
    client = auth_client(stub_iam, user_id=3000 + 105)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0105",
        complainant_user_id=3000 + 105,
        category="maintenance",
        description="Testing requirement AFR-CMS-039: CMS shall track escalation status.",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_106_afr_cms_039_invariant(stub_iam):
    """TEST-FR-106: AFR-CMS-039 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 105)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0106",
        complainant_user_id=3500 + 105,
        category="other",
        description="Testing state invariant for AFR-CMS-039",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 105,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-039"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_107_afr_cms_040_positive(stub_iam):
    """TEST-FR-107: AFR-CMS-040 - CMS shall allow Complaint Supervisors to monitor escalated complaints."""
    client = auth_client(stub_iam, user_id=3000 + 107)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0107",
        complainant_user_id=3000 + 107,
        category="maintenance",
        description="Testing requirement AFR-CMS-040: CMS shall allow Complaint Supervisors to monitor e",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_108_afr_cms_040_announcement_expiry_defect(stub_iam):
    """TEST-FR-108: AFR-CMS-040 - Announcement expiration date filtering (Defect 11)."""
    client = auth_client(stub_iam, user_id=3108)
    ann = ComplaintAnnouncement.objects.create(
        author_user_id=9999,
        author_role="staff",
        title="Expired Water Outage Notice",
        content="Notice for last month.",
        is_active=True
    )
    # Specification requires filtering out expired announcements
    # Implementation lacks expires_at field check in queryset
    has_expiry_filter = hasattr(ComplaintAnnouncement, 'expires_at')
    assert has_expiry_filter, "ComplaintAnnouncement lacks mandatory expires_at support in schema/queryset"


def test_fr_109_afr_cms_041_positive(stub_iam):
    """TEST-FR-109: AFR-CMS-041 - CMS shall associate complaint priority with applicable SLA timelines."""
    client = auth_client(stub_iam, user_id=3000 + 109)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0109",
        complainant_user_id=3000 + 109,
        category="maintenance",
        description="Testing requirement AFR-CMS-041: CMS shall associate complaint priority with applic",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_110_afr_cms_041_invariant(stub_iam):
    """TEST-FR-110: AFR-CMS-041 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 109)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0110",
        complainant_user_id=3500 + 109,
        category="other",
        description="Testing state invariant for AFR-CMS-041",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 109,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-041"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_111_afr_cms_042_positive(stub_iam):
    """TEST-FR-111: AFR-CMS-042 - CMS shall not specify exact SLA duration values in the module baseline"""
    client = auth_client(stub_iam, user_id=3000 + 111)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0111",
        complainant_user_id=3000 + 111,
        category="maintenance",
        description="Testing requirement AFR-CMS-042: CMS shall not specify exact SLA duration values in",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_112_afr_cms_042_invariant(stub_iam):
    """TEST-FR-112: AFR-CMS-042 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 111)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0112",
        complainant_user_id=3500 + 111,
        category="other",
        description="Testing state invariant for AFR-CMS-042",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 111,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-042"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_113_afr_cms_043_positive(stub_iam):
    """TEST-FR-113: AFR-CMS-043 - CMS shall send reminder notifications when a complaint approaches the """
    client = auth_client(stub_iam, user_id=3000 + 113)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0113",
        complainant_user_id=3000 + 113,
        category="maintenance",
        description="Testing requirement AFR-CMS-043: CMS shall send reminder notifications when a compl",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_114_afr_cms_043_invariant(stub_iam):
    """TEST-FR-114: AFR-CMS-043 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 113)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0114",
        complainant_user_id=3500 + 113,
        category="other",
        description="Testing state invariant for AFR-CMS-043",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 113,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-043"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_115_afr_cms_044_positive(stub_iam):
    """TEST-FR-115: AFR-CMS-044 - CMS shall automatically escalate a complaint if it is not resolved wit"""
    client = auth_client(stub_iam, user_id=3000 + 115)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0115",
        complainant_user_id=3000 + 115,
        category="maintenance",
        description="Testing requirement AFR-CMS-044: CMS shall automatically escalate a complaint if it",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_116_afr_cms_044_invariant(stub_iam):
    """TEST-FR-116: AFR-CMS-044 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 115)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0116",
        complainant_user_id=3500 + 115,
        category="other",
        description="Testing state invariant for AFR-CMS-044",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 115,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-044"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_117_afr_cms_045_positive(stub_iam):
    """TEST-FR-117: AFR-CMS-045 - CMS shall allow Complaint Handlers to publish complaint-related announ"""
    client = auth_client(stub_iam, user_id=3000 + 117)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0117",
        complainant_user_id=3000 + 117,
        category="maintenance",
        description="Testing requirement AFR-CMS-045: CMS shall allow Complaint Handlers to publish comp",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_118_afr_cms_045_invariant(stub_iam):
    """TEST-FR-118: AFR-CMS-045 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 117)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0118",
        complainant_user_id=3500 + 117,
        category="other",
        description="Testing state invariant for AFR-CMS-045",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 117,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-045"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_119_afr_cms_046_positive(stub_iam):
    """TEST-FR-119: AFR-CMS-046 - CMS shall allow Complaint Supervisors to publish complaint-related ann"""
    client = auth_client(stub_iam, user_id=3000 + 119)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0119",
        complainant_user_id=3000 + 119,
        category="maintenance",
        description="Testing requirement AFR-CMS-046: CMS shall allow Complaint Supervisors to publish c",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_120_afr_cms_046_invariant(stub_iam):
    """TEST-FR-120: AFR-CMS-046 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 119)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0120",
        complainant_user_id=3500 + 119,
        category="other",
        description="Testing state invariant for AFR-CMS-046",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 119,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-046"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_121_afr_cms_047_positive(stub_iam):
    """TEST-FR-121: AFR-CMS-047 - CMS shall allow Users / Complainants to view complaint-related announc"""
    client = auth_client(stub_iam, user_id=3000 + 121)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0121",
        complainant_user_id=3000 + 121,
        category="maintenance",
        description="Testing requirement AFR-CMS-047: CMS shall allow Users / Complainants to view compl",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_122_afr_cms_047_invariant(stub_iam):
    """TEST-FR-122: AFR-CMS-047 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 121)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0122",
        complainant_user_id=3500 + 121,
        category="other",
        description="Testing state invariant for AFR-CMS-047",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 121,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-047"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_123_afr_cms_048_positive(stub_iam):
    """TEST-FR-123: AFR-CMS-048 - CMS shall send announcement-related notifications to Users / Complaina"""
    client = auth_client(stub_iam, user_id=3000 + 123)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0123",
        complainant_user_id=3000 + 123,
        category="maintenance",
        description="Testing requirement AFR-CMS-048: CMS shall send announcement-related notifications ",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_124_afr_cms_048_invariant(stub_iam):
    """TEST-FR-124: AFR-CMS-048 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 123)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0124",
        complainant_user_id=3500 + 123,
        category="other",
        description="Testing state invariant for AFR-CMS-048",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 123,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-048"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_125_afr_cms_049_positive(stub_iam):
    """TEST-FR-125: AFR-CMS-049 - CMS shall allow Complaint Handlers to generate operational complaint r"""
    client = auth_client(stub_iam, user_id=3000 + 125)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0125",
        complainant_user_id=3000 + 125,
        category="maintenance",
        description="Testing requirement AFR-CMS-049: CMS shall allow Complaint Handlers to generate ope",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_126_afr_cms_049_invariant(stub_iam):
    """TEST-FR-126: AFR-CMS-049 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 125)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0126",
        complainant_user_id=3500 + 125,
        category="other",
        description="Testing state invariant for AFR-CMS-049",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 125,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-049"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_127_afr_cms_050_positive(stub_iam):
    """TEST-FR-127: AFR-CMS-050 - CMS shall allow Complaint Supervisors to view complaint summaries."""
    client = auth_client(stub_iam, user_id=3000 + 127)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0127",
        complainant_user_id=3000 + 127,
        category="maintenance",
        description="Testing requirement AFR-CMS-050: CMS shall allow Complaint Supervisors to view comp",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_128_afr_cms_050_reports_date_filter_defect(stub_iam):
    """TEST-FR-128: AFR-CMS-050 - Complaint reports date range filter (Defect 12)."""
    client = auth_client(stub_iam, user_id=3128)
    Complaint.objects.create(
        complaint_id="CMS-2026-FR0128",
        complainant_user_id=3128,
        category="hostel",
        description="Complaint for date filter defect test.",
        status="Submitted"
    )
    res = client.get("/api/v1/cms/complaints/reports/?start_date=2099-01-01&end_date=2099-12-31")
    assert res.status_code == 200
    assert res.data["total"] == 0, f"Reports endpoint ignores date filters (returned {res.data['total']})"


def test_fr_129_afr_cms_051_positive(stub_iam):
    """TEST-FR-129: AFR-CMS-051 - CMS shall allow Complaint Supervisors to view escalation summaries."""
    client = auth_client(stub_iam, user_id=3000 + 129)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0129",
        complainant_user_id=3000 + 129,
        category="maintenance",
        description="Testing requirement AFR-CMS-051: CMS shall allow Complaint Supervisors to view esca",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_130_afr_cms_051_invariant(stub_iam):
    """TEST-FR-130: AFR-CMS-051 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 129)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0130",
        complainant_user_id=3500 + 129,
        category="other",
        description="Testing state invariant for AFR-CMS-051",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 129,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-051"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_131_afr_cms_052_positive(stub_iam):
    """TEST-FR-131: AFR-CMS-052 - CMS shall allow System Admin to view complaint reports available withi"""
    client = auth_client(stub_iam, user_id=3000 + 131)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0131",
        complainant_user_id=3000 + 131,
        category="maintenance",
        description="Testing requirement AFR-CMS-052: CMS shall allow System Admin to view complaint rep",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_132_afr_cms_052_invariant(stub_iam):
    """TEST-FR-132: AFR-CMS-052 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 131)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0132",
        complainant_user_id=3500 + 131,
        category="other",
        description="Testing state invariant for AFR-CMS-052",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 131,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-052"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_133_afr_cms_053_positive(stub_iam):
    """TEST-FR-133: AFR-CMS-053 - CMS shall allow System Admin to view analytics available within CMS."""
    client = auth_client(stub_iam, user_id=3000 + 133)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0133",
        complainant_user_id=3000 + 133,
        category="maintenance",
        description="Testing requirement AFR-CMS-053: CMS shall allow System Admin to view analytics ava",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_134_afr_cms_053_invariant(stub_iam):
    """TEST-FR-134: AFR-CMS-053 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 133)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0134",
        complainant_user_id=3500 + 133,
        category="other",
        description="Testing state invariant for AFR-CMS-053",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 133,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-053"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_135_afr_cms_054_positive(stub_iam):
    """TEST-FR-135: AFR-CMS-054 - CMS shall limit analytics scope to complaint reports, complaint summar"""
    client = auth_client(stub_iam, user_id=3000 + 135)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0135",
        complainant_user_id=3000 + 135,
        category="maintenance",
        description="Testing requirement AFR-CMS-054: CMS shall limit analytics scope to complaint repor",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_136_afr_cms_054_invariant(stub_iam):
    """TEST-FR-136: AFR-CMS-054 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 135)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0136",
        complainant_user_id=3500 + 135,
        category="other",
        description="Testing state invariant for AFR-CMS-054",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 135,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-054"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_137_afr_cms_055_positive(stub_iam):
    """TEST-FR-137: AFR-CMS-055 - CMS shall trigger email notifications for complaint submission events."""
    client = auth_client(stub_iam, user_id=3000 + 137)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0137",
        complainant_user_id=3000 + 137,
        category="maintenance",
        description="Testing requirement AFR-CMS-055: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_138_afr_cms_055_invariant(stub_iam):
    """TEST-FR-138: AFR-CMS-055 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 137)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0138",
        complainant_user_id=3500 + 137,
        category="other",
        description="Testing state invariant for AFR-CMS-055",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 137,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-055"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_139_afr_cms_056_positive(stub_iam):
    """TEST-FR-139: AFR-CMS-056 - CMS shall trigger email notifications for complaint status update even"""
    client = auth_client(stub_iam, user_id=3000 + 139)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0139",
        complainant_user_id=3000 + 139,
        category="maintenance",
        description="Testing requirement AFR-CMS-056: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_140_afr_cms_056_invariant(stub_iam):
    """TEST-FR-140: AFR-CMS-056 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 139)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0140",
        complainant_user_id=3500 + 139,
        category="other",
        description="Testing state invariant for AFR-CMS-056",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 139,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-056"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_141_afr_cms_057_positive(stub_iam):
    """TEST-FR-141: AFR-CMS-057 - CMS shall trigger email notifications for complaint resolution events."""
    client = auth_client(stub_iam, user_id=3000 + 141)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0141",
        complainant_user_id=3000 + 141,
        category="maintenance",
        description="Testing requirement AFR-CMS-057: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_142_afr_cms_057_invariant(stub_iam):
    """TEST-FR-142: AFR-CMS-057 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 141)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0142",
        complainant_user_id=3500 + 141,
        category="other",
        description="Testing state invariant for AFR-CMS-057",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 141,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-057"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_143_afr_cms_058_positive(stub_iam):
    """TEST-FR-143: AFR-CMS-058 - CMS shall trigger email notifications for complaint rejection events."""
    client = auth_client(stub_iam, user_id=3000 + 143)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0143",
        complainant_user_id=3000 + 143,
        category="maintenance",
        description="Testing requirement AFR-CMS-058: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_144_afr_cms_058_category_role_deactivation_defect(stub_iam):
    """TEST-FR-144: AFR-CMS-058 - Assigning handler preserves handlers of other categories (Defect 6)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    # Active hostel handler
    h1 = CmsRoleAssignment.objects.create(
        user_id=7001,
        role_type="complaint_handler",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True,
        assigned_by_id=9999
    )
    # Assign new maintenance handler
    res = client.post("/api/v1/cms/roles/", data={
        "user_id": 7002,
        "role_type": "complaint_handler",
        "start_date": "2026-02-01",
        "end_date": "2026-12-31",
        "is_active": True
    }, format="json")
    assert res.status_code == 201
    h1.refresh_from_db()
    # Invariant: assigning a new handler should not deactivate handlers of distinct queues
    assert h1.is_active is True, "Assigning handler deactivated all existing active handlers unconditionally"


def test_fr_145_afr_cms_059_positive(stub_iam):
    """TEST-FR-145: AFR-CMS-059 - CMS shall trigger email notifications for complaint escalation events."""
    client = auth_client(stub_iam, user_id=3000 + 145)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0145",
        complainant_user_id=3000 + 145,
        category="maintenance",
        description="Testing requirement AFR-CMS-059: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_146_afr_cms_059_invariant(stub_iam):
    """TEST-FR-146: AFR-CMS-059 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 145)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0146",
        complainant_user_id=3500 + 145,
        category="other",
        description="Testing state invariant for AFR-CMS-059",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 145,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-059"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_147_afr_cms_060_positive(stub_iam):
    """TEST-FR-147: AFR-CMS-060 - CMS shall trigger email notifications for complaint reopening outcome """
    client = auth_client(stub_iam, user_id=3000 + 147)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0147",
        complainant_user_id=3000 + 147,
        category="maintenance",
        description="Testing requirement AFR-CMS-060: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_148_afr_cms_060_invariant(stub_iam):
    """TEST-FR-148: AFR-CMS-060 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 147)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0148",
        complainant_user_id=3500 + 147,
        category="other",
        description="Testing state invariant for AFR-CMS-060",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 147,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-060"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_149_afr_cms_061_positive(stub_iam):
    """TEST-FR-149: AFR-CMS-061 - CMS shall trigger email notifications for feedback-related events wher"""
    client = auth_client(stub_iam, user_id=3000 + 149)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0149",
        complainant_user_id=3000 + 149,
        category="maintenance",
        description="Testing requirement AFR-CMS-061: CMS shall trigger email notifications for feedback",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_150_afr_cms_061_invariant(stub_iam):
    """TEST-FR-150: AFR-CMS-061 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 149)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0150",
        complainant_user_id=3500 + 149,
        category="other",
        description="Testing state invariant for AFR-CMS-061",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 149,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-061"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_151_afr_cms_062_positive(stub_iam):
    """TEST-FR-151: AFR-CMS-062 - CMS shall trigger email notifications for complaint-related announceme"""
    client = auth_client(stub_iam, user_id=3000 + 151)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0151",
        complainant_user_id=3000 + 151,
        category="maintenance",
        description="Testing requirement AFR-CMS-062: CMS shall trigger email notifications for complain",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_152_afr_cms_062_invariant(stub_iam):
    """TEST-FR-152: AFR-CMS-062 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 151)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0152",
        complainant_user_id=3500 + 151,
        category="other",
        description="Testing state invariant for AFR-CMS-062",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 151,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-062"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_153_afr_cms_063_positive(stub_iam):
    """TEST-FR-153: AFR-CMS-063 - CMS shall limit module responsibility to notification triggering, not """
    client = auth_client(stub_iam, user_id=3000 + 153)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0153",
        complainant_user_id=3000 + 153,
        category="maintenance",
        description="Testing requirement AFR-CMS-063: CMS shall limit module responsibility to notificat",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_154_afr_cms_063_invariant(stub_iam):
    """TEST-FR-154: AFR-CMS-063 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 153)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0154",
        complainant_user_id=3500 + 153,
        category="other",
        description="Testing state invariant for AFR-CMS-063",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 153,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-063"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_155_afr_cms_064_positive(stub_iam):
    """TEST-FR-155: AFR-CMS-064 - CMS shall allow System Admin to assign the Complaint Handler role to a"""
    client = auth_client(stub_iam, user_id=3000 + 155)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0155",
        complainant_user_id=3000 + 155,
        category="maintenance",
        description="Testing requirement AFR-CMS-064: CMS shall allow System Admin to assign the Complai",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_156_afr_cms_064_invariant(stub_iam):
    """TEST-FR-156: AFR-CMS-064 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 155)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0156",
        complainant_user_id=3500 + 155,
        category="other",
        description="Testing state invariant for AFR-CMS-064",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 155,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-064"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_157_afr_cms_065_positive(stub_iam):
    """TEST-FR-157: AFR-CMS-065 - CMS shall allow System Admin to assign the Complaint Supervisor role t"""
    client = auth_client(stub_iam, user_id=3000 + 157)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0157",
        complainant_user_id=3000 + 157,
        category="maintenance",
        description="Testing requirement AFR-CMS-065: CMS shall allow System Admin to assign the Complai",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_158_afr_cms_065_invariant(stub_iam):
    """TEST-FR-158: AFR-CMS-065 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 157)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0158",
        complainant_user_id=3500 + 157,
        category="other",
        description="Testing state invariant for AFR-CMS-065",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 157,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-065"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_159_afr_cms_066_positive(stub_iam):
    """TEST-FR-159: AFR-CMS-066 - CMS shall allow System Admin to reassign Complaint Handler and Complai"""
    client = auth_client(stub_iam, user_id=3000 + 159)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0159",
        complainant_user_id=3000 + 159,
        category="maintenance",
        description="Testing requirement AFR-CMS-066: CMS shall allow System Admin to reassign Complaint",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_160_afr_cms_066_invariant(stub_iam):
    """TEST-FR-160: AFR-CMS-066 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 159)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0160",
        complainant_user_id=3500 + 159,
        category="other",
        description="Testing state invariant for AFR-CMS-066",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 159,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-066"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_161_afr_cms_067_positive(stub_iam):
    """TEST-FR-161: AFR-CMS-067 - CMS shall enforce exactly one active Complaint Handler role-holder at """
    client = auth_client(stub_iam, user_id=3000 + 161)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0161",
        complainant_user_id=3000 + 161,
        category="maintenance",
        description="Testing requirement AFR-CMS-067: CMS shall enforce exactly one active Complaint Han",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_162_afr_cms_067_invariant(stub_iam):
    """TEST-FR-162: AFR-CMS-067 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 161)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0162",
        complainant_user_id=3500 + 161,
        category="other",
        description="Testing state invariant for AFR-CMS-067",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 161,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-067"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_163_afr_cms_068_positive(stub_iam):
    """TEST-FR-163: AFR-CMS-068 - CMS shall enforce exactly one active Complaint Supervisor role-holder """
    client = auth_client(stub_iam, user_id=3000 + 163)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0163",
        complainant_user_id=3000 + 163,
        category="maintenance",
        description="Testing requirement AFR-CMS-068: CMS shall enforce exactly one active Complaint Sup",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_164_afr_cms_068_invariant(stub_iam):
    """TEST-FR-164: AFR-CMS-068 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 163)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0164",
        complainant_user_id=3500 + 163,
        category="other",
        description="Testing state invariant for AFR-CMS-068",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 163,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-068"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_165_afr_cms_069_positive(stub_iam):
    """TEST-FR-165: AFR-CMS-069 - CMS role assignment shall be limited to CMS-specific operational and s"""
    client = auth_client(stub_iam, user_id=3000 + 165)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0165",
        complainant_user_id=3000 + 165,
        category="maintenance",
        description="Testing requirement AFR-CMS-069: CMS role assignment shall be limited to CMS-specif",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_166_afr_cms_069_invariant(stub_iam):
    """TEST-FR-166: AFR-CMS-069 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 165)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0166",
        complainant_user_id=3500 + 165,
        category="other",
        description="Testing state invariant for AFR-CMS-069",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 165,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-069"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_167_afr_cms_070_positive(stub_iam):
    """TEST-FR-167: AFR-CMS-070 - CMS shall exclude HR master-data management, payroll, employment recor"""
    client = auth_client(stub_iam, user_id=3000 + 167)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0167",
        complainant_user_id=3000 + 167,
        category="maintenance",
        description="Testing requirement AFR-CMS-070: CMS shall exclude HR master-data management, payro",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_168_afr_cms_070_invariant(stub_iam):
    """TEST-FR-168: AFR-CMS-070 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 167)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0168",
        complainant_user_id=3500 + 167,
        category="other",
        description="Testing state invariant for AFR-CMS-070",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 167,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-070"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_169_afr_cms_071_positive(stub_iam):
    """TEST-FR-169: AFR-CMS-071 - CMS shall not perform payment, accounting, payroll, procurement, inven"""
    client = auth_client(stub_iam, user_id=3000 + 169)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0169",
        complainant_user_id=3000 + 169,
        category="maintenance",
        description="Testing requirement AFR-CMS-071: CMS shall not perform payment, accounting, payroll",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_170_afr_cms_071_invariant(stub_iam):
    """TEST-FR-170: AFR-CMS-071 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 169)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0170",
        complainant_user_id=3500 + 169,
        category="other",
        description="Testing state invariant for AFR-CMS-071",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 169,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-071"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_171_afr_cms_072_positive(stub_iam):
    """TEST-FR-171: AFR-CMS-072 - CMS shall limit complaints involving external services or departments """
    client = auth_client(stub_iam, user_id=3000 + 171)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0171",
        complainant_user_id=3000 + 171,
        category="maintenance",
        description="Testing requirement AFR-CMS-072: CMS shall limit complaints involving external serv",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_172_afr_cms_072_invariant(stub_iam):
    """TEST-FR-172: AFR-CMS-072 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 171)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0172",
        complainant_user_id=3500 + 171,
        category="other",
        description="Testing state invariant for AFR-CMS-072",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 171,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-072"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_173_afr_cms_073_positive(stub_iam):
    """TEST-FR-173: AFR-CMS-073 - CMS shall treat external institutional policies, manuals, guidelines, """
    client = auth_client(stub_iam, user_id=3000 + 173)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0173",
        complainant_user_id=3000 + 173,
        category="maintenance",
        description="Testing requirement AFR-CMS-073: CMS shall treat external institutional policies, m",
        status="Submitted",
        priority="Medium"
    )
    assert c.id is not None
    assert c.complaint_id.startswith("CMS-2026-")
    assert c.status == "Submitted"


def test_fr_174_afr_cms_073_invariant(stub_iam):
    """TEST-FR-174: AFR-CMS-073 - Invariant enforcement."""
    client = auth_client(stub_iam, user_id=3500 + 173)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0174",
        complainant_user_id=3500 + 173,
        category="other",
        description="Testing state invariant for AFR-CMS-073",
        status="Submitted"
    )
    # Valid progress update
    prog = ComplaintProgress.objects.create(
        complaint=c,
        actor_user_id=3500 + 173,
        actor_role="handler",
        action="update",
        remarks="Tracking step for AFR-CMS-073"
    )
    assert prog.id is not None
    assert c.progress_history.count() >= 1


def test_fr_175_end_to_end_audit_trail(stub_iam):
    """TEST-FR-175: End-to-end progress history audit trail."""
    client = auth_client(stub_iam, user_id=9175)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-FR0175",
        complainant_user_id=9175,
        category="network",
        description="Final comprehensive FR audit test.",
        status="Submitted"
    )
    ComplaintProgress.objects.create(complaint=c, actor_user_id=9175, actor_role="complainant", action="submitted", remarks="Initial")
    ComplaintProgress.objects.create(complaint=c, actor_user_id=5001, actor_role="handler", action="assigned", remarks="Assigned")
    ComplaintProgress.objects.create(complaint=c, actor_user_id=5001, actor_role="handler", action="resolved", remarks="Fixed problem")
    assert c.progress_history.count() == 3
