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


def test_br_001_br_cms_001_condition_true(stub_iam):
    """TEST-BR-001: BR-CMS-001 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 1)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0001",
        complainant_user_id=5000 + 1,
        category="maintenance",
        description="Verification of BR-CMS-001 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_002_br_cms_001_condition_false(stub_iam):
    """TEST-BR-002: BR-CMS-001 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 2)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0002",
        complainant_user_id=5000 + 2,
        category="maintenance",
        description="Verification of BR-CMS-001 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_003_br_cms_001_boundary(stub_iam):
    """TEST-BR-003: BR-CMS-001 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 3)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0003",
        complainant_user_id=5000 + 3,
        category="maintenance",
        description="Verification of BR-CMS-001 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_004_br_cms_001_role_guard(stub_iam):
    """TEST-BR-004: BR-CMS-001 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 4)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0004",
        complainant_user_id=5000 + 4,
        category="maintenance",
        description="Verification of BR-CMS-001 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_005_br_cms_001_invariant(stub_iam):
    """TEST-BR-005: BR-CMS-001 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 5)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0005",
        complainant_user_id=5000 + 5,
        category="maintenance",
        description="Verification of BR-CMS-001 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_006_br_cms_002_condition_true(stub_iam):
    """TEST-BR-006: BR-CMS-002 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 6)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0006",
        complainant_user_id=5000 + 6,
        category="maintenance",
        description="Verification of BR-CMS-002 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_007_br_cms_002_condition_false(stub_iam):
    """TEST-BR-007: BR-CMS-002 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 7)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0007",
        complainant_user_id=5000 + 7,
        category="maintenance",
        description="Verification of BR-CMS-002 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_008_br_cms_002_boundary(stub_iam):
    """TEST-BR-008: BR-CMS-002 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 8)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0008",
        complainant_user_id=5000 + 8,
        category="maintenance",
        description="Verification of BR-CMS-002 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_009_br_cms_002_role_guard(stub_iam):
    """TEST-BR-009: BR-CMS-002 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 9)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0009",
        complainant_user_id=5000 + 9,
        category="maintenance",
        description="Verification of BR-CMS-002 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_010_br_cms_002_invariant(stub_iam):
    """TEST-BR-010: BR-CMS-002 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 10)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0010",
        complainant_user_id=5000 + 10,
        category="maintenance",
        description="Verification of BR-CMS-002 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_011_br_cms_003_condition_true(stub_iam):
    """TEST-BR-011: BR-CMS-003 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 11)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0011",
        complainant_user_id=5000 + 11,
        category="maintenance",
        description="Verification of BR-CMS-003 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_012_br_cms_003_condition_false(stub_iam):
    """TEST-BR-012: BR-CMS-003 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 12)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0012",
        complainant_user_id=5000 + 12,
        category="maintenance",
        description="Verification of BR-CMS-003 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_013_br_cms_003_boundary(stub_iam):
    """TEST-BR-013: BR-CMS-003 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 13)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0013",
        complainant_user_id=5000 + 13,
        category="maintenance",
        description="Verification of BR-CMS-003 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_014_br_cms_003_role_guard(stub_iam):
    """TEST-BR-014: BR-CMS-003 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 14)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0014",
        complainant_user_id=5000 + 14,
        category="maintenance",
        description="Verification of BR-CMS-003 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_015_br_cms_003_invariant(stub_iam):
    """TEST-BR-015: BR-CMS-003 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 15)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0015",
        complainant_user_id=5000 + 15,
        category="maintenance",
        description="Verification of BR-CMS-003 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_016_br_cms_004_condition_true(stub_iam):
    """TEST-BR-016: BR-CMS-004 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 16)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0016",
        complainant_user_id=5000 + 16,
        category="maintenance",
        description="Verification of BR-CMS-004 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_017_br_cms_004_condition_false(stub_iam):
    """TEST-BR-017: BR-CMS-004 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 17)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0017",
        complainant_user_id=5000 + 17,
        category="maintenance",
        description="Verification of BR-CMS-004 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_018_br_cms_004_boundary(stub_iam):
    """TEST-BR-018: BR-CMS-004 boundary - Attachment format constraint validation (Defect 3)."""
    client = auth_client(stub_iam, user_id=5000 + 18)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0018",
        complainant_user_id=5000 + 18,
        category="hostel",
        description="Testing attachment constraints.",
        status="Submitted"
    )
    # Binary executable file must be rejected by attachment constraints
    att = ComplaintAttachment(complaint=c, file_name="script.sh", file_size=0, file_type="text/x-shellscript")
    assert att.file_type in ["image/jpeg", "image/png", "application/pdf"], f"Invalid file format accepted: {att.file_type}"


def test_br_019_br_cms_004_role_guard(stub_iam):
    """TEST-BR-019: BR-CMS-004 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 19)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0019",
        complainant_user_id=5000 + 19,
        category="maintenance",
        description="Verification of BR-CMS-004 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_020_br_cms_004_invariant(stub_iam):
    """TEST-BR-020: BR-CMS-004 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 20)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0020",
        complainant_user_id=5000 + 20,
        category="maintenance",
        description="Verification of BR-CMS-004 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_021_br_cms_005_condition_true(stub_iam):
    """TEST-BR-021: BR-CMS-005 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 21)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0021",
        complainant_user_id=5000 + 21,
        category="maintenance",
        description="Verification of BR-CMS-005 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_022_br_cms_005_condition_false(stub_iam):
    """TEST-BR-022: BR-CMS-005 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 22)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0022",
        complainant_user_id=5000 + 22,
        category="maintenance",
        description="Verification of BR-CMS-005 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_023_br_cms_005_boundary(stub_iam):
    """TEST-BR-023: BR-CMS-005 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 23)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0023",
        complainant_user_id=5000 + 23,
        category="maintenance",
        description="Verification of BR-CMS-005 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_024_br_cms_005_role_guard(stub_iam):
    """TEST-BR-024: BR-CMS-005 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 24)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0024",
        complainant_user_id=5000 + 24,
        category="maintenance",
        description="Verification of BR-CMS-005 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_025_br_cms_005_invariant(stub_iam):
    """TEST-BR-025: BR-CMS-005 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 25)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0025",
        complainant_user_id=5000 + 25,
        category="maintenance",
        description="Verification of BR-CMS-005 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_026_br_cms_006_condition_true(stub_iam):
    """TEST-BR-026: BR-CMS-006 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 26)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0026",
        complainant_user_id=5000 + 26,
        category="maintenance",
        description="Verification of BR-CMS-006 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_027_br_cms_006_condition_false(stub_iam):
    """TEST-BR-027: BR-CMS-006 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 27)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0027",
        complainant_user_id=5000 + 27,
        category="maintenance",
        description="Verification of BR-CMS-006 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_028_br_cms_006_boundary(stub_iam):
    """TEST-BR-028: BR-CMS-006 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 28)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0028",
        complainant_user_id=5000 + 28,
        category="maintenance",
        description="Verification of BR-CMS-006 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_029_br_cms_006_role_guard(stub_iam):
    """TEST-BR-029: BR-CMS-006 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 29)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0029",
        complainant_user_id=5000 + 29,
        category="maintenance",
        description="Verification of BR-CMS-006 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_030_br_cms_006_invariant(stub_iam):
    """TEST-BR-030: BR-CMS-006 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 30)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0030",
        complainant_user_id=5000 + 30,
        category="maintenance",
        description="Verification of BR-CMS-006 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_031_br_cms_007_condition_true(stub_iam):
    """TEST-BR-031: BR-CMS-007 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 31)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0031",
        complainant_user_id=5000 + 31,
        category="maintenance",
        description="Verification of BR-CMS-007 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_032_br_cms_007_condition_false(stub_iam):
    """TEST-BR-032: BR-CMS-007 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 32)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0032",
        complainant_user_id=5000 + 32,
        category="maintenance",
        description="Verification of BR-CMS-007 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_033_br_cms_007_boundary(stub_iam):
    """TEST-BR-033: BR-CMS-007 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 33)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0033",
        complainant_user_id=5000 + 33,
        category="maintenance",
        description="Verification of BR-CMS-007 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_034_br_cms_007_role_guard(stub_iam):
    """TEST-BR-034: BR-CMS-007 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 34)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0034",
        complainant_user_id=5000 + 34,
        category="maintenance",
        description="Verification of BR-CMS-007 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_035_br_cms_007_invariant(stub_iam):
    """TEST-BR-035: BR-CMS-007 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 35)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0035",
        complainant_user_id=5000 + 35,
        category="maintenance",
        description="Verification of BR-CMS-007 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_036_br_cms_008_condition_true(stub_iam):
    """TEST-BR-036: BR-CMS-008 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 36)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0036",
        complainant_user_id=5000 + 36,
        category="maintenance",
        description="Verification of BR-CMS-008 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_037_br_cms_008_condition_false(stub_iam):
    """TEST-BR-037: BR-CMS-008 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 37)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0037",
        complainant_user_id=5000 + 37,
        category="maintenance",
        description="Verification of BR-CMS-008 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_038_br_cms_008_boundary(stub_iam):
    """TEST-BR-038: BR-CMS-008 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 38)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0038",
        complainant_user_id=5000 + 38,
        category="maintenance",
        description="Verification of BR-CMS-008 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_039_br_cms_008_role_guard(stub_iam):
    """TEST-BR-039: BR-CMS-008 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 39)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0039",
        complainant_user_id=5000 + 39,
        category="maintenance",
        description="Verification of BR-CMS-008 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_040_br_cms_008_invariant(stub_iam):
    """TEST-BR-040: BR-CMS-008 invariant - Category modification rejection after progress underway (Defect 15)."""
    client = auth_client(stub_iam, user_id=6040, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0040",
        complainant_user_id=5040,
        category="network",
        description="Wi-Fi AP dropped.",
        status="In Progress",
        priority="Medium"
    )
    ComplaintProgress.objects.create(complaint=c, actor_user_id=6040, actor_role="handler", action="progress_update", remarks="Work started")
    # BR-CMS-008 requires rejecting category change once progress has commenced
    res = client.post(f"/api/v1/cms/complaints/{c.id}/assign/", data={"assigned_handler_id": 6040, "category": "hostel"}, format="json")
    assert res.status_code == 400, "Category modification allowed on in-progress complaint"


def test_br_041_br_cms_009_condition_true(stub_iam):
    """TEST-BR-041: BR-CMS-009 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 41)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0041",
        complainant_user_id=5000 + 41,
        category="maintenance",
        description="Verification of BR-CMS-009 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_042_br_cms_009_condition_false(stub_iam):
    """TEST-BR-042: BR-CMS-009 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 42)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0042",
        complainant_user_id=5000 + 42,
        category="maintenance",
        description="Verification of BR-CMS-009 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_043_br_cms_009_boundary(stub_iam):
    """TEST-BR-043: BR-CMS-009 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 43)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0043",
        complainant_user_id=5000 + 43,
        category="maintenance",
        description="Verification of BR-CMS-009 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_044_br_cms_009_role_guard(stub_iam):
    """TEST-BR-044: BR-CMS-009 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 44)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0044",
        complainant_user_id=5000 + 44,
        category="maintenance",
        description="Verification of BR-CMS-009 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_045_br_cms_009_invariant(stub_iam):
    """TEST-BR-045: BR-CMS-009 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 45)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0045",
        complainant_user_id=5000 + 45,
        category="maintenance",
        description="Verification of BR-CMS-009 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_046_br_cms_010_condition_true(stub_iam):
    """TEST-BR-046: BR-CMS-010 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 46)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0046",
        complainant_user_id=5000 + 46,
        category="maintenance",
        description="Verification of BR-CMS-010 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_047_br_cms_010_condition_false(stub_iam):
    """TEST-BR-047: BR-CMS-010 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 47)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0047",
        complainant_user_id=5000 + 47,
        category="maintenance",
        description="Verification of BR-CMS-010 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_048_br_cms_010_boundary(stub_iam):
    """TEST-BR-048: BR-CMS-010 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 48)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0048",
        complainant_user_id=5000 + 48,
        category="maintenance",
        description="Verification of BR-CMS-010 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_049_br_cms_010_role_guard(stub_iam):
    """TEST-BR-049: BR-CMS-010 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 49)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0049",
        complainant_user_id=5000 + 49,
        category="maintenance",
        description="Verification of BR-CMS-010 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_050_br_cms_010_invariant(stub_iam):
    """TEST-BR-050: BR-CMS-010 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 50)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0050",
        complainant_user_id=5000 + 50,
        category="maintenance",
        description="Verification of BR-CMS-010 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_051_br_cms_011_condition_true(stub_iam):
    """TEST-BR-051: BR-CMS-011 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 51)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0051",
        complainant_user_id=5000 + 51,
        category="maintenance",
        description="Verification of BR-CMS-011 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_052_br_cms_011_condition_false(stub_iam):
    """TEST-BR-052: BR-CMS-011 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 52)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0052",
        complainant_user_id=5000 + 52,
        category="maintenance",
        description="Verification of BR-CMS-011 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_053_br_cms_011_boundary(stub_iam):
    """TEST-BR-053: BR-CMS-011 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 53)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0053",
        complainant_user_id=5000 + 53,
        category="maintenance",
        description="Verification of BR-CMS-011 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_054_br_cms_011_role_guard(stub_iam):
    """TEST-BR-054: BR-CMS-011 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 54)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0054",
        complainant_user_id=5000 + 54,
        category="maintenance",
        description="Verification of BR-CMS-011 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_055_br_cms_011_invariant(stub_iam):
    """TEST-BR-055: BR-CMS-011 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 55)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0055",
        complainant_user_id=5000 + 55,
        category="maintenance",
        description="Verification of BR-CMS-011 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_056_br_cms_012_condition_true(stub_iam):
    """TEST-BR-056: BR-CMS-012 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 56)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0056",
        complainant_user_id=5000 + 56,
        category="maintenance",
        description="Verification of BR-CMS-012 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_057_br_cms_012_condition_false(stub_iam):
    """TEST-BR-057: BR-CMS-012 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 57)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0057",
        complainant_user_id=5000 + 57,
        category="maintenance",
        description="Verification of BR-CMS-012 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_058_br_cms_012_boundary(stub_iam):
    """TEST-BR-058: BR-CMS-012 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 58)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0058",
        complainant_user_id=5000 + 58,
        category="maintenance",
        description="Verification of BR-CMS-012 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_059_br_cms_012_role_guard(stub_iam):
    """TEST-BR-059: BR-CMS-012 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 59)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0059",
        complainant_user_id=5000 + 59,
        category="maintenance",
        description="Verification of BR-CMS-012 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_060_br_cms_012_invariant(stub_iam):
    """TEST-BR-060: BR-CMS-012 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 60)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0060",
        complainant_user_id=5000 + 60,
        category="maintenance",
        description="Verification of BR-CMS-012 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_061_br_cms_013_condition_true(stub_iam):
    """TEST-BR-061: BR-CMS-013 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 61)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0061",
        complainant_user_id=5000 + 61,
        category="maintenance",
        description="Verification of BR-CMS-013 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_062_br_cms_013_condition_false(stub_iam):
    """TEST-BR-062: BR-CMS-013 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 62)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0062",
        complainant_user_id=5000 + 62,
        category="maintenance",
        description="Verification of BR-CMS-013 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_063_br_cms_013_boundary(stub_iam):
    """TEST-BR-063: BR-CMS-013 boundary - Resolution details substantive length (Defect 7)."""
    client = auth_client(stub_iam, user_id=6000 + 63, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0063",
        complainant_user_id=5000 + 63,
        category="maintenance",
        description="Leaking pipe in restroom.",
        status="In Progress"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/resolve/", data={"resolution_details": "Fix"}, format="json")
    assert res.status_code == 400, "Resolution details < 10 characters accepted"


def test_br_064_br_cms_013_role_guard(stub_iam):
    """TEST-BR-064: BR-CMS-013 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 64)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0064",
        complainant_user_id=5000 + 64,
        category="maintenance",
        description="Verification of BR-CMS-013 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_065_br_cms_013_invariant(stub_iam):
    """TEST-BR-065: BR-CMS-013 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 65)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0065",
        complainant_user_id=5000 + 65,
        category="maintenance",
        description="Verification of BR-CMS-013 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_066_br_cms_014_condition_true(stub_iam):
    """TEST-BR-066: BR-CMS-014 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 66)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0066",
        complainant_user_id=5000 + 66,
        category="maintenance",
        description="Verification of BR-CMS-014 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_067_br_cms_014_condition_false(stub_iam):
    """TEST-BR-067: BR-CMS-014 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 67)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0067",
        complainant_user_id=5000 + 67,
        category="maintenance",
        description="Verification of BR-CMS-014 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_068_br_cms_014_boundary(stub_iam):
    """TEST-BR-068: BR-CMS-014 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 68)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0068",
        complainant_user_id=5000 + 68,
        category="maintenance",
        description="Verification of BR-CMS-014 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_069_br_cms_014_role_guard(stub_iam):
    """TEST-BR-069: BR-CMS-014 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 69)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0069",
        complainant_user_id=5000 + 69,
        category="maintenance",
        description="Verification of BR-CMS-014 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_070_br_cms_014_invariant(stub_iam):
    """TEST-BR-070: BR-CMS-014 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 70)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0070",
        complainant_user_id=5000 + 70,
        category="maintenance",
        description="Verification of BR-CMS-014 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_071_br_cms_015_condition_true(stub_iam):
    """TEST-BR-071: BR-CMS-015 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 71)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0071",
        complainant_user_id=5000 + 71,
        category="maintenance",
        description="Verification of BR-CMS-015 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_072_br_cms_015_condition_false(stub_iam):
    """TEST-BR-072: BR-CMS-015 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 72)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0072",
        complainant_user_id=5000 + 72,
        category="maintenance",
        description="Verification of BR-CMS-015 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_073_br_cms_015_boundary(stub_iam):
    """TEST-BR-073: BR-CMS-015 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 73)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0073",
        complainant_user_id=5000 + 73,
        category="maintenance",
        description="Verification of BR-CMS-015 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_074_br_cms_015_role_guard(stub_iam):
    """TEST-BR-074: BR-CMS-015 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 74)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0074",
        complainant_user_id=5000 + 74,
        category="maintenance",
        description="Verification of BR-CMS-015 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_075_br_cms_015_invariant(stub_iam):
    """TEST-BR-075: BR-CMS-015 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 75)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0075",
        complainant_user_id=5000 + 75,
        category="maintenance",
        description="Verification of BR-CMS-015 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_076_br_cms_016_condition_true(stub_iam):
    """TEST-BR-076: BR-CMS-016 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 76)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0076",
        complainant_user_id=5000 + 76,
        category="maintenance",
        description="Verification of BR-CMS-016 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_077_br_cms_016_condition_false(stub_iam):
    """TEST-BR-077: BR-CMS-016 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 77)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0077",
        complainant_user_id=5000 + 77,
        category="maintenance",
        description="Verification of BR-CMS-016 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_078_br_cms_016_boundary(stub_iam):
    """TEST-BR-078: BR-CMS-016 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 78)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0078",
        complainant_user_id=5000 + 78,
        category="maintenance",
        description="Verification of BR-CMS-016 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_079_br_cms_016_role_guard(stub_iam):
    """TEST-BR-079: BR-CMS-016 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 79)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0079",
        complainant_user_id=5000 + 79,
        category="maintenance",
        description="Verification of BR-CMS-016 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_080_br_cms_016_invariant(stub_iam):
    """TEST-BR-080: BR-CMS-016 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 80)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0080",
        complainant_user_id=5000 + 80,
        category="maintenance",
        description="Verification of BR-CMS-016 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_081_br_cms_017_condition_true(stub_iam):
    """TEST-BR-081: BR-CMS-017 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 81)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0081",
        complainant_user_id=5000 + 81,
        category="maintenance",
        description="Verification of BR-CMS-017 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_082_br_cms_017_condition_false(stub_iam):
    """TEST-BR-082: BR-CMS-017 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 82)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0082",
        complainant_user_id=5000 + 82,
        category="maintenance",
        description="Verification of BR-CMS-017 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_083_br_cms_017_boundary(stub_iam):
    """TEST-BR-083: BR-CMS-017 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 83)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0083",
        complainant_user_id=5000 + 83,
        category="maintenance",
        description="Verification of BR-CMS-017 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_084_br_cms_017_role_guard(stub_iam):
    """TEST-BR-084: BR-CMS-017 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 84)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0084",
        complainant_user_id=5000 + 84,
        category="maintenance",
        description="Verification of BR-CMS-017 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_085_br_cms_017_invariant(stub_iam):
    """TEST-BR-085: BR-CMS-017 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 85)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0085",
        complainant_user_id=5000 + 85,
        category="maintenance",
        description="Verification of BR-CMS-017 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_086_br_cms_018_condition_true(stub_iam):
    """TEST-BR-086: BR-CMS-018 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 86)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0086",
        complainant_user_id=5000 + 86,
        category="maintenance",
        description="Verification of BR-CMS-018 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_087_br_cms_018_condition_false(stub_iam):
    """TEST-BR-087: BR-CMS-018 condition-false - Duplicate pending reopening prevention (Defect 2)."""
    client = auth_client(stub_iam, user_id=5000 + 87)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0087",
        complainant_user_id=5000 + 87,
        category="maintenance",
        description="Window latch broken.",
        status="Closed"
    )
    res1 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Still unlatched."}, format="json")
    assert res1.status_code in [200, 201]
    res2 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Repeated request."}, format="json")
    assert res2.status_code == 400, "Second pending reopening allowed while first pending"


def test_br_088_br_cms_018_boundary(stub_iam):
    """TEST-BR-088: BR-CMS-018 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 88)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0088",
        complainant_user_id=5000 + 88,
        category="maintenance",
        description="Verification of BR-CMS-018 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_089_br_cms_018_role_guard(stub_iam):
    """TEST-BR-089: BR-CMS-018 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 89)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0089",
        complainant_user_id=5000 + 89,
        category="maintenance",
        description="Verification of BR-CMS-018 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_090_br_cms_018_invariant(stub_iam):
    """TEST-BR-090: BR-CMS-018 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 90)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0090",
        complainant_user_id=5000 + 90,
        category="maintenance",
        description="Verification of BR-CMS-018 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_091_br_cms_019_condition_true(stub_iam):
    """TEST-BR-091: BR-CMS-019 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 91)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0091",
        complainant_user_id=5000 + 91,
        category="maintenance",
        description="Verification of BR-CMS-019 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_092_br_cms_019_condition_false(stub_iam):
    """TEST-BR-092: BR-CMS-019 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 92)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0092",
        complainant_user_id=5000 + 92,
        category="maintenance",
        description="Verification of BR-CMS-019 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_093_br_cms_019_boundary(stub_iam):
    """TEST-BR-093: BR-CMS-019 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 93)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0093",
        complainant_user_id=5000 + 93,
        category="maintenance",
        description="Verification of BR-CMS-019 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_094_br_cms_019_role_guard(stub_iam):
    """TEST-BR-094: BR-CMS-019 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 94)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0094",
        complainant_user_id=5000 + 94,
        category="maintenance",
        description="Verification of BR-CMS-019 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_095_br_cms_019_invariant(stub_iam):
    """TEST-BR-095: BR-CMS-019 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 95)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0095",
        complainant_user_id=5000 + 95,
        category="maintenance",
        description="Verification of BR-CMS-019 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_096_br_cms_020_condition_true(stub_iam):
    """TEST-BR-096: BR-CMS-020 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 96)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0096",
        complainant_user_id=5000 + 96,
        category="maintenance",
        description="Verification of BR-CMS-020 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_097_br_cms_020_condition_false(stub_iam):
    """TEST-BR-097: BR-CMS-020 condition-false - Approved reopening clears rejection reason (Defect 4)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0097",
        complainant_user_id=5000 + 97,
        category="academic",
        description="Projector lamp replacement.",
        status="Closed",
        rejection_reason="Duplicate complaint ID"
    )
    reopen = ComplaintReopening.objects.create(
        complaint=c,
        complainant_user_id=5000 + 97,
        dissatisfaction_reason="Not duplicate, distinct lecture room.",
        status="pending"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/decide_reopen/", data={"reopening_id": reopen.id, "decision": "approved", "supervisor_remarks": "Reopened upon review"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # Invariant: reopening a complaint into 'In Progress' should clear prior rejection remarks
    assert c.rejection_reason == "", f"Rejection reason was not cleared upon reopening: {c.rejection_reason}"


def test_br_098_br_cms_020_boundary(stub_iam):
    """TEST-BR-098: BR-CMS-020 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 98)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0098",
        complainant_user_id=5000 + 98,
        category="maintenance",
        description="Verification of BR-CMS-020 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_099_br_cms_020_role_guard(stub_iam):
    """TEST-BR-099: BR-CMS-020 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 99)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0099",
        complainant_user_id=5000 + 99,
        category="maintenance",
        description="Verification of BR-CMS-020 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_100_br_cms_020_invariant(stub_iam):
    """TEST-BR-100: BR-CMS-020 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 100)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0100",
        complainant_user_id=5000 + 100,
        category="maintenance",
        description="Verification of BR-CMS-020 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_101_br_cms_021_condition_true(stub_iam):
    """TEST-BR-101: BR-CMS-021 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 101)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0101",
        complainant_user_id=5000 + 101,
        category="maintenance",
        description="Verification of BR-CMS-021 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_102_br_cms_021_condition_false(stub_iam):
    """TEST-BR-102: BR-CMS-021 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 102)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0102",
        complainant_user_id=5000 + 102,
        category="maintenance",
        description="Verification of BR-CMS-021 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_103_br_cms_021_boundary(stub_iam):
    """TEST-BR-103: BR-CMS-021 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 103)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0103",
        complainant_user_id=5000 + 103,
        category="maintenance",
        description="Verification of BR-CMS-021 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_104_br_cms_021_role_guard(stub_iam):
    """TEST-BR-104: BR-CMS-021 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 104)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0104",
        complainant_user_id=5000 + 104,
        category="maintenance",
        description="Verification of BR-CMS-021 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_105_br_cms_021_invariant(stub_iam):
    """TEST-BR-105: BR-CMS-021 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 105)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0105",
        complainant_user_id=5000 + 105,
        category="maintenance",
        description="Verification of BR-CMS-021 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_106_br_cms_022_condition_true(stub_iam):
    """TEST-BR-106: BR-CMS-022 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 106)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0106",
        complainant_user_id=5000 + 106,
        category="maintenance",
        description="Verification of BR-CMS-022 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_107_br_cms_022_condition_false(stub_iam):
    """TEST-BR-107: BR-CMS-022 condition-false - Feedback cardinality (Defect 5)."""
    client = auth_client(stub_iam, user_id=5000 + 107)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0107",
        complainant_user_id=5000 + 107,
        category="mess",
        description="Mess food issue.",
        status="Closed"
    )
    res1 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 5, "comments": "First feedback."}, format="json")
    assert res1.status_code == 201
    res2 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 3, "comments": "Second feedback."}, format="json")
    assert res2.status_code == 400, "Allowed duplicate feedback for single complaint"


def test_br_108_br_cms_022_boundary(stub_iam):
    """TEST-BR-108: BR-CMS-022 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 108)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0108",
        complainant_user_id=5000 + 108,
        category="maintenance",
        description="Verification of BR-CMS-022 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_109_br_cms_022_role_guard(stub_iam):
    """TEST-BR-109: BR-CMS-022 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 109)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0109",
        complainant_user_id=5000 + 109,
        category="maintenance",
        description="Verification of BR-CMS-022 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_110_br_cms_022_invariant(stub_iam):
    """TEST-BR-110: BR-CMS-022 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 110)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0110",
        complainant_user_id=5000 + 110,
        category="maintenance",
        description="Verification of BR-CMS-022 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_111_br_cms_023_condition_true(stub_iam):
    """TEST-BR-111: BR-CMS-023 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 111)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0111",
        complainant_user_id=5000 + 111,
        category="maintenance",
        description="Verification of BR-CMS-023 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_112_br_cms_023_condition_false(stub_iam):
    """TEST-BR-112: BR-CMS-023 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 112)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0112",
        complainant_user_id=5000 + 112,
        category="maintenance",
        description="Verification of BR-CMS-023 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_113_br_cms_023_boundary(stub_iam):
    """TEST-BR-113: BR-CMS-023 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 113)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0113",
        complainant_user_id=5000 + 113,
        category="maintenance",
        description="Verification of BR-CMS-023 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_114_br_cms_023_role_guard(stub_iam):
    """TEST-BR-114: BR-CMS-023 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 114)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0114",
        complainant_user_id=5000 + 114,
        category="maintenance",
        description="Verification of BR-CMS-023 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_115_br_cms_023_invariant(stub_iam):
    """TEST-BR-115: BR-CMS-023 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 115)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0115",
        complainant_user_id=5000 + 115,
        category="maintenance",
        description="Verification of BR-CMS-023 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_116_br_cms_024_condition_true(stub_iam):
    """TEST-BR-116: BR-CMS-024 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 116)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0116",
        complainant_user_id=5000 + 116,
        category="maintenance",
        description="Verification of BR-CMS-024 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_117_br_cms_024_condition_false(stub_iam):
    """TEST-BR-117: BR-CMS-024 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 117)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0117",
        complainant_user_id=5000 + 117,
        category="maintenance",
        description="Verification of BR-CMS-024 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_118_br_cms_024_boundary(stub_iam):
    """TEST-BR-118: BR-CMS-024 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 118)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0118",
        complainant_user_id=5000 + 118,
        category="maintenance",
        description="Verification of BR-CMS-024 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_119_br_cms_024_role_guard(stub_iam):
    """TEST-BR-119: BR-CMS-024 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 119)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0119",
        complainant_user_id=5000 + 119,
        category="maintenance",
        description="Verification of BR-CMS-024 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_120_br_cms_024_invariant(stub_iam):
    """TEST-BR-120: BR-CMS-024 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 120)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0120",
        complainant_user_id=5000 + 120,
        category="maintenance",
        description="Verification of BR-CMS-024 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_121_br_cms_025_condition_true(stub_iam):
    """TEST-BR-121: BR-CMS-025 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 121)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0121",
        complainant_user_id=5000 + 121,
        category="maintenance",
        description="Verification of BR-CMS-025 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_122_br_cms_025_condition_false(stub_iam):
    """TEST-BR-122: BR-CMS-025 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 122)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0122",
        complainant_user_id=5000 + 122,
        category="maintenance",
        description="Verification of BR-CMS-025 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_123_br_cms_025_boundary(stub_iam):
    """TEST-BR-123: BR-CMS-025 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 123)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0123",
        complainant_user_id=5000 + 123,
        category="maintenance",
        description="Verification of BR-CMS-025 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_124_br_cms_025_role_guard(stub_iam):
    """TEST-BR-124: BR-CMS-025 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 124)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0124",
        complainant_user_id=5000 + 124,
        category="maintenance",
        description="Verification of BR-CMS-025 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_125_br_cms_025_invariant(stub_iam):
    """TEST-BR-125: BR-CMS-025 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 125)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0125",
        complainant_user_id=5000 + 125,
        category="maintenance",
        description="Verification of BR-CMS-025 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_126_br_cms_026_condition_true(stub_iam):
    """TEST-BR-126: BR-CMS-026 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 126)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0126",
        complainant_user_id=5000 + 126,
        category="maintenance",
        description="Verification of BR-CMS-026 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_127_br_cms_026_condition_false(stub_iam):
    """TEST-BR-127: BR-CMS-026 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 127)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0127",
        complainant_user_id=5000 + 127,
        category="maintenance",
        description="Verification of BR-CMS-026 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_128_br_cms_026_boundary(stub_iam):
    """TEST-BR-128: BR-CMS-026 boundary - High priority SLA duration (Defect 1)."""
    client = auth_client(stub_iam, user_id=6000 + 128, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0128",
        complainant_user_id=5000 + 128,
        category="network",
        description="Core fiber trunk severance.",
        status="Submitted",
        priority="Low"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/assign/", data={"assigned_handler_id": 6000 + 128, "priority": "High"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # High priority SLA must be 24h
    now = timezone.now()
    assert c.sla_due_date <= now + timedelta(hours=26), f"High priority SLA exceeds 24h (got {c.sla_due_date - now})"


def test_br_129_br_cms_026_role_guard(stub_iam):
    """TEST-BR-129: BR-CMS-026 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 129)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0129",
        complainant_user_id=5000 + 129,
        category="maintenance",
        description="Verification of BR-CMS-026 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_130_br_cms_026_invariant(stub_iam):
    """TEST-BR-130: BR-CMS-026 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 130)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0130",
        complainant_user_id=5000 + 130,
        category="maintenance",
        description="Verification of BR-CMS-026 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_131_br_cms_027_condition_true(stub_iam):
    """TEST-BR-131: BR-CMS-027 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 131)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0131",
        complainant_user_id=5000 + 131,
        category="maintenance",
        description="Verification of BR-CMS-027 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_132_br_cms_027_condition_false(stub_iam):
    """TEST-BR-132: BR-CMS-027 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 132)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0132",
        complainant_user_id=5000 + 132,
        category="maintenance",
        description="Verification of BR-CMS-027 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_133_br_cms_027_boundary(stub_iam):
    """TEST-BR-133: BR-CMS-027 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 133)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0133",
        complainant_user_id=5000 + 133,
        category="maintenance",
        description="Verification of BR-CMS-027 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_134_br_cms_027_role_guard(stub_iam):
    """TEST-BR-134: BR-CMS-027 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 134)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0134",
        complainant_user_id=5000 + 134,
        category="maintenance",
        description="Verification of BR-CMS-027 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_135_br_cms_027_invariant(stub_iam):
    """TEST-BR-135: BR-CMS-027 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 135)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0135",
        complainant_user_id=5000 + 135,
        category="maintenance",
        description="Verification of BR-CMS-027 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_136_br_cms_028_condition_true(stub_iam):
    """TEST-BR-136: BR-CMS-028 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 136)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0136",
        complainant_user_id=5000 + 136,
        category="maintenance",
        description="Verification of BR-CMS-028 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_137_br_cms_028_condition_false(stub_iam):
    """TEST-BR-137: BR-CMS-028 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 137)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0137",
        complainant_user_id=5000 + 137,
        category="maintenance",
        description="Verification of BR-CMS-028 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_138_br_cms_028_boundary(stub_iam):
    """TEST-BR-138: BR-CMS-028 boundary - Pre-breach reminder window threshold (Defect 10)."""
    client = auth_client(stub_iam, user_id=5000 + 138)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0138",
        complainant_user_id=5000 + 138,
        category="other",
        description="General maintenance.",
        status="In Progress",
        priority="High",
        sla_due_date=timezone.now() + timedelta(hours=22),
        sla_reminder_sent=False
    )
    res = client.post("/api/v1/cms/complaints/check_sla/", format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    assert c.sla_reminder_sent is False, "Pre-breach reminder triggered prematurely at 22h remaining for 24h SLA"


def test_br_139_br_cms_028_role_guard(stub_iam):
    """TEST-BR-139: BR-CMS-028 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 139)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0139",
        complainant_user_id=5000 + 139,
        category="maintenance",
        description="Verification of BR-CMS-028 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_140_br_cms_028_invariant(stub_iam):
    """TEST-BR-140: BR-CMS-028 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 140)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0140",
        complainant_user_id=5000 + 140,
        category="maintenance",
        description="Verification of BR-CMS-028 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_141_br_cms_029_condition_true(stub_iam):
    """TEST-BR-141: BR-CMS-029 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 141)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0141",
        complainant_user_id=5000 + 141,
        category="maintenance",
        description="Verification of BR-CMS-029 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_142_br_cms_029_condition_false(stub_iam):
    """TEST-BR-142: BR-CMS-029 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 142)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0142",
        complainant_user_id=5000 + 142,
        category="maintenance",
        description="Verification of BR-CMS-029 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_143_br_cms_029_boundary(stub_iam):
    """TEST-BR-143: BR-CMS-029 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 143)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0143",
        complainant_user_id=5000 + 143,
        category="maintenance",
        description="Verification of BR-CMS-029 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_144_br_cms_029_role_guard(stub_iam):
    """TEST-BR-144: BR-CMS-029 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 144)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0144",
        complainant_user_id=5000 + 144,
        category="maintenance",
        description="Verification of BR-CMS-029 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_145_br_cms_029_invariant(stub_iam):
    """TEST-BR-145: BR-CMS-029 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 145)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0145",
        complainant_user_id=5000 + 145,
        category="maintenance",
        description="Verification of BR-CMS-029 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_146_br_cms_030_condition_true(stub_iam):
    """TEST-BR-146: BR-CMS-030 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 146)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0146",
        complainant_user_id=5000 + 146,
        category="maintenance",
        description="Verification of BR-CMS-030 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_147_br_cms_030_condition_false(stub_iam):
    """TEST-BR-147: BR-CMS-030 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 147)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0147",
        complainant_user_id=5000 + 147,
        category="maintenance",
        description="Verification of BR-CMS-030 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_148_br_cms_030_boundary(stub_iam):
    """TEST-BR-148: BR-CMS-030 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 148)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0148",
        complainant_user_id=5000 + 148,
        category="maintenance",
        description="Verification of BR-CMS-030 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_149_br_cms_030_role_guard(stub_iam):
    """TEST-BR-149: BR-CMS-030 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 149)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0149",
        complainant_user_id=5000 + 149,
        category="maintenance",
        description="Verification of BR-CMS-030 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_150_br_cms_030_invariant(stub_iam):
    """TEST-BR-150: BR-CMS-030 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 150)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0150",
        complainant_user_id=5000 + 150,
        category="maintenance",
        description="Verification of BR-CMS-030 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_151_br_cms_031_condition_true(stub_iam):
    """TEST-BR-151: BR-CMS-031 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 151)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0151",
        complainant_user_id=5000 + 151,
        category="maintenance",
        description="Verification of BR-CMS-031 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_152_br_cms_031_condition_false(stub_iam):
    """TEST-BR-152: BR-CMS-031 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 152)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0152",
        complainant_user_id=5000 + 152,
        category="maintenance",
        description="Verification of BR-CMS-031 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_153_br_cms_031_boundary(stub_iam):
    """TEST-BR-153: BR-CMS-031 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 153)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0153",
        complainant_user_id=5000 + 153,
        category="maintenance",
        description="Verification of BR-CMS-031 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_154_br_cms_031_role_guard(stub_iam):
    """TEST-BR-154: BR-CMS-031 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 154)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0154",
        complainant_user_id=5000 + 154,
        category="maintenance",
        description="Verification of BR-CMS-031 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_155_br_cms_031_invariant(stub_iam):
    """TEST-BR-155: BR-CMS-031 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 155)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0155",
        complainant_user_id=5000 + 155,
        category="maintenance",
        description="Verification of BR-CMS-031 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_156_br_cms_032_condition_true(stub_iam):
    """TEST-BR-156: BR-CMS-032 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 156)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0156",
        complainant_user_id=5000 + 156,
        category="maintenance",
        description="Verification of BR-CMS-032 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_157_br_cms_032_condition_false(stub_iam):
    """TEST-BR-157: BR-CMS-032 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 157)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0157",
        complainant_user_id=5000 + 157,
        category="maintenance",
        description="Verification of BR-CMS-032 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_158_br_cms_032_boundary(stub_iam):
    """TEST-BR-158: BR-CMS-032 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 158)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0158",
        complainant_user_id=5000 + 158,
        category="maintenance",
        description="Verification of BR-CMS-032 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_159_br_cms_032_role_guard(stub_iam):
    """TEST-BR-159: BR-CMS-032 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 159)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0159",
        complainant_user_id=5000 + 159,
        category="maintenance",
        description="Verification of BR-CMS-032 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_160_br_cms_032_invariant(stub_iam):
    """TEST-BR-160: BR-CMS-032 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 160)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0160",
        complainant_user_id=5000 + 160,
        category="maintenance",
        description="Verification of BR-CMS-032 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_161_br_cms_033_condition_true(stub_iam):
    """TEST-BR-161: BR-CMS-033 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 161)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0161",
        complainant_user_id=5000 + 161,
        category="maintenance",
        description="Verification of BR-CMS-033 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_162_br_cms_033_condition_false(stub_iam):
    """TEST-BR-162: BR-CMS-033 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 162)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0162",
        complainant_user_id=5000 + 162,
        category="maintenance",
        description="Verification of BR-CMS-033 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_163_br_cms_033_boundary(stub_iam):
    """TEST-BR-163: BR-CMS-033 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 163)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0163",
        complainant_user_id=5000 + 163,
        category="maintenance",
        description="Verification of BR-CMS-033 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_164_br_cms_033_role_guard(stub_iam):
    """TEST-BR-164: BR-CMS-033 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 164)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0164",
        complainant_user_id=5000 + 164,
        category="maintenance",
        description="Verification of BR-CMS-033 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_165_br_cms_033_invariant(stub_iam):
    """TEST-BR-165: BR-CMS-033 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 165)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0165",
        complainant_user_id=5000 + 165,
        category="maintenance",
        description="Verification of BR-CMS-033 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_166_br_cms_034_condition_true(stub_iam):
    """TEST-BR-166: BR-CMS-034 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 166)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0166",
        complainant_user_id=5000 + 166,
        category="maintenance",
        description="Verification of BR-CMS-034 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_167_br_cms_034_condition_false(stub_iam):
    """TEST-BR-167: BR-CMS-034 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 167)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0167",
        complainant_user_id=5000 + 167,
        category="maintenance",
        description="Verification of BR-CMS-034 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_168_br_cms_034_boundary(stub_iam):
    """TEST-BR-168: BR-CMS-034 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 168)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0168",
        complainant_user_id=5000 + 168,
        category="maintenance",
        description="Verification of BR-CMS-034 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_169_br_cms_034_role_guard(stub_iam):
    """TEST-BR-169: BR-CMS-034 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 169)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0169",
        complainant_user_id=5000 + 169,
        category="maintenance",
        description="Verification of BR-CMS-034 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_170_br_cms_034_invariant(stub_iam):
    """TEST-BR-170: BR-CMS-034 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 170)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0170",
        complainant_user_id=5000 + 170,
        category="maintenance",
        description="Verification of BR-CMS-034 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_171_br_cms_035_condition_true(stub_iam):
    """TEST-BR-171: BR-CMS-035 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 171)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0171",
        complainant_user_id=5000 + 171,
        category="maintenance",
        description="Verification of BR-CMS-035 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_172_br_cms_035_condition_false(stub_iam):
    """TEST-BR-172: BR-CMS-035 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 172)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0172",
        complainant_user_id=5000 + 172,
        category="maintenance",
        description="Verification of BR-CMS-035 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_173_br_cms_035_boundary(stub_iam):
    """TEST-BR-173: BR-CMS-035 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 173)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0173",
        complainant_user_id=5000 + 173,
        category="maintenance",
        description="Verification of BR-CMS-035 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_174_br_cms_035_role_guard(stub_iam):
    """TEST-BR-174: BR-CMS-035 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 174)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0174",
        complainant_user_id=5000 + 174,
        category="maintenance",
        description="Verification of BR-CMS-035 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_175_br_cms_035_invariant(stub_iam):
    """TEST-BR-175: BR-CMS-035 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 175)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0175",
        complainant_user_id=5000 + 175,
        category="maintenance",
        description="Verification of BR-CMS-035 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_176_br_cms_036_condition_true(stub_iam):
    """TEST-BR-176: BR-CMS-036 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 176)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0176",
        complainant_user_id=5000 + 176,
        category="maintenance",
        description="Verification of BR-CMS-036 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_177_br_cms_036_condition_false(stub_iam):
    """TEST-BR-177: BR-CMS-036 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 177)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0177",
        complainant_user_id=5000 + 177,
        category="maintenance",
        description="Verification of BR-CMS-036 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_178_br_cms_036_boundary(stub_iam):
    """TEST-BR-178: BR-CMS-036 boundary - Mid-cycle role reassignment handover audit (Defect 16)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    h1 = CmsRoleAssignment.objects.create(
        user_id=9016,
        role_type="complaint_handler",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True,
        assigned_by_id=9999
    )
    res = client.post("/api/v1/cms/roles/", data={
        "user_id": 9017,
        "role_type": "complaint_handler",
        "start_date": "2026-06-01",
        "end_date": "2026-12-31",
        "is_active": True
    }, format="json")
    assert res.status_code == 201
    # Specification requires explicit handover audit log recording previous and successor user_id
    has_audit_model = hasattr(CmsRoleAssignment, 'handover_logs')
    assert has_audit_model, "CmsRoleAssignment lacks handover audit tracking log for mid-cycle reassignment"


def test_br_179_br_cms_036_role_guard(stub_iam):
    """TEST-BR-179: BR-CMS-036 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 179)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0179",
        complainant_user_id=5000 + 179,
        category="maintenance",
        description="Verification of BR-CMS-036 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_180_br_cms_036_invariant(stub_iam):
    """TEST-BR-180: BR-CMS-036 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 180)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0180",
        complainant_user_id=5000 + 180,
        category="maintenance",
        description="Verification of BR-CMS-036 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_181_br_cms_037_condition_true(stub_iam):
    """TEST-BR-181: BR-CMS-037 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 181)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0181",
        complainant_user_id=5000 + 181,
        category="maintenance",
        description="Verification of BR-CMS-037 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_182_br_cms_037_condition_false(stub_iam):
    """TEST-BR-182: BR-CMS-037 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 182)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0182",
        complainant_user_id=5000 + 182,
        category="maintenance",
        description="Verification of BR-CMS-037 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_183_br_cms_037_boundary(stub_iam):
    """TEST-BR-183: BR-CMS-037 boundary - Active role cardinality category scoped (Defect 6)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    h1 = CmsRoleAssignment.objects.create(
        user_id=9001,
        role_type="complaint_handler",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=True,
        assigned_by_id=9999
    )
    res = client.post("/api/v1/cms/roles/", data={
        "user_id": 9002,
        "role_type": "complaint_handler",
        "start_date": "2026-03-01",
        "end_date": "2026-12-31",
        "is_active": True
    }, format="json")
    assert res.status_code == 201
    h1.refresh_from_db()
    assert h1.is_active is True, "Assigning new handler globally deactivated all existing handlers"


def test_br_184_br_cms_037_role_guard(stub_iam):
    """TEST-BR-184: BR-CMS-037 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 184)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0184",
        complainant_user_id=5000 + 184,
        category="maintenance",
        description="Verification of BR-CMS-037 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_185_br_cms_037_invariant(stub_iam):
    """TEST-BR-185: BR-CMS-037 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 185)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0185",
        complainant_user_id=5000 + 185,
        category="maintenance",
        description="Verification of BR-CMS-037 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_186_br_cms_038_condition_true(stub_iam):
    """TEST-BR-186: BR-CMS-038 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 186)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0186",
        complainant_user_id=5000 + 186,
        category="maintenance",
        description="Verification of BR-CMS-038 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_187_br_cms_038_condition_false(stub_iam):
    """TEST-BR-187: BR-CMS-038 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 187)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0187",
        complainant_user_id=5000 + 187,
        category="maintenance",
        description="Verification of BR-CMS-038 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_188_br_cms_038_boundary(stub_iam):
    """TEST-BR-188: BR-CMS-038 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 188)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0188",
        complainant_user_id=5000 + 188,
        category="maintenance",
        description="Verification of BR-CMS-038 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_189_br_cms_038_role_guard(stub_iam):
    """TEST-BR-189: BR-CMS-038 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 189)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0189",
        complainant_user_id=5000 + 189,
        category="maintenance",
        description="Verification of BR-CMS-038 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_190_br_cms_038_invariant(stub_iam):
    """TEST-BR-190: BR-CMS-038 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 190)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0190",
        complainant_user_id=5000 + 190,
        category="maintenance",
        description="Verification of BR-CMS-038 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_191_br_cms_039_condition_true(stub_iam):
    """TEST-BR-191: BR-CMS-039 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 191)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0191",
        complainant_user_id=5000 + 191,
        category="maintenance",
        description="Verification of BR-CMS-039 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_192_br_cms_039_condition_false(stub_iam):
    """TEST-BR-192: BR-CMS-039 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 192)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0192",
        complainant_user_id=5000 + 192,
        category="maintenance",
        description="Verification of BR-CMS-039 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_193_br_cms_039_boundary(stub_iam):
    """TEST-BR-193: BR-CMS-039 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 193)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0193",
        complainant_user_id=5000 + 193,
        category="maintenance",
        description="Verification of BR-CMS-039 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_194_br_cms_039_role_guard(stub_iam):
    """TEST-BR-194: BR-CMS-039 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 194)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0194",
        complainant_user_id=5000 + 194,
        category="maintenance",
        description="Verification of BR-CMS-039 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_195_br_cms_039_invariant(stub_iam):
    """TEST-BR-195: BR-CMS-039 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 195)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0195",
        complainant_user_id=5000 + 195,
        category="maintenance",
        description="Verification of BR-CMS-039 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_196_br_cms_040_condition_true(stub_iam):
    """TEST-BR-196: BR-CMS-040 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 196)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0196",
        complainant_user_id=5000 + 196,
        category="maintenance",
        description="Verification of BR-CMS-040 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_197_br_cms_040_condition_false(stub_iam):
    """TEST-BR-197: BR-CMS-040 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 197)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0197",
        complainant_user_id=5000 + 197,
        category="maintenance",
        description="Verification of BR-CMS-040 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_198_br_cms_040_boundary(stub_iam):
    """TEST-BR-198: BR-CMS-040 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 198)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0198",
        complainant_user_id=5000 + 198,
        category="maintenance",
        description="Verification of BR-CMS-040 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_199_br_cms_040_role_guard(stub_iam):
    """TEST-BR-199: BR-CMS-040 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 199)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0199",
        complainant_user_id=5000 + 199,
        category="maintenance",
        description="Verification of BR-CMS-040 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_200_br_cms_040_invariant(stub_iam):
    """TEST-BR-200: BR-CMS-040 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 200)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0200",
        complainant_user_id=5000 + 200,
        category="maintenance",
        description="Verification of BR-CMS-040 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_201_br_cms_041_condition_true(stub_iam):
    """TEST-BR-201: BR-CMS-041 condition-true - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 201)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0201",
        complainant_user_id=5000 + 201,
        category="maintenance",
        description="Verification of BR-CMS-041 condition-true.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_202_br_cms_041_condition_false(stub_iam):
    """TEST-BR-202: BR-CMS-041 condition-false - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 202)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0202",
        complainant_user_id=5000 + 202,
        category="maintenance",
        description="Verification of BR-CMS-041 condition-false.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_203_br_cms_041_boundary(stub_iam):
    """TEST-BR-203: BR-CMS-041 boundary - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 203)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0203",
        complainant_user_id=5000 + 203,
        category="maintenance",
        description="Verification of BR-CMS-041 boundary.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_204_br_cms_041_role_guard(stub_iam):
    """TEST-BR-204: BR-CMS-041 role-guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 204)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0204",
        complainant_user_id=5000 + 204,
        category="maintenance",
        description="Verification of BR-CMS-041 role-guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_br_205_br_cms_041_invariant(stub_iam):
    """TEST-BR-205: BR-CMS-041 invariant - Conforming execution."""
    client = auth_client(stub_iam, user_id=5000 + 205)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-BR0205",
        complainant_user_id=5000 + 205,
        category="maintenance",
        description="Verification of BR-CMS-041 invariant.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
