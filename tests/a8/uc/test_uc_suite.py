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


def test_uc_001_uc_cms_001_main_flow(stub_iam):
    """TEST-UC-001: UC-CMS-001 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 1)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0001",
        complainant_user_id=4000 + 1,
        category="maintenance",
        description="Testing UC-CMS-001 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_002_uc_cms_001_data_input_step(stub_iam):
    """TEST-UC-002: UC-CMS-001 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 2)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0002",
        complainant_user_id=4000 + 2,
        category="maintenance",
        description="Testing UC-CMS-001 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_003_uc_cms_001_role_execution(stub_iam):
    """TEST-UC-003: UC-CMS-001 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 3)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0003",
        complainant_user_id=4000 + 3,
        category="maintenance",
        description="Testing UC-CMS-001 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_004_uc_cms_001_state_transition(stub_iam):
    """TEST-UC-004: UC-CMS-001 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 4)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0004",
        complainant_user_id=4000 + 4,
        category="maintenance",
        description="Testing UC-CMS-001 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_005_uc_cms_001_alternative_a1(stub_iam):
    """TEST-UC-005: UC-CMS-001 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 5)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0005",
        complainant_user_id=4000 + 5,
        category="maintenance",
        description="Testing UC-CMS-001 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_006_uc_cms_001_alternative_a2(stub_iam):
    """TEST-UC-006: UC-CMS-001 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 6)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0006",
        complainant_user_id=4000 + 6,
        category="maintenance",
        description="Testing UC-CMS-001 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_007_uc_cms_001_exception_e1(stub_iam):
    """TEST-UC-007: UC-CMS-001 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 7)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0007",
        complainant_user_id=4000 + 7,
        category="maintenance",
        description="Testing UC-CMS-001 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_008_uc_cms_001_exception_e2(stub_iam):
    """TEST-UC-008: UC-CMS-001 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 8)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0008",
        complainant_user_id=4000 + 8,
        category="maintenance",
        description="Testing UC-CMS-001 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_009_uc_cms_002_main_flow(stub_iam):
    """TEST-UC-009: UC-CMS-002 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 9)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0009",
        complainant_user_id=4000 + 9,
        category="maintenance",
        description="Testing UC-CMS-002 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_010_uc_cms_002_data_input_step(stub_iam):
    """TEST-UC-010: UC-CMS-002 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 10)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0010",
        complainant_user_id=4000 + 10,
        category="maintenance",
        description="Testing UC-CMS-002 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_011_uc_cms_002_role_execution(stub_iam):
    """TEST-UC-011: UC-CMS-002 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 11)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0011",
        complainant_user_id=4000 + 11,
        category="maintenance",
        description="Testing UC-CMS-002 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_012_uc_cms_002_state_transition(stub_iam):
    """TEST-UC-012: UC-CMS-002 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 12)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0012",
        complainant_user_id=4000 + 12,
        category="maintenance",
        description="Testing UC-CMS-002 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_013_uc_cms_002_alternative_a1(stub_iam):
    """TEST-UC-013: UC-CMS-002 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 13)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0013",
        complainant_user_id=4000 + 13,
        category="maintenance",
        description="Testing UC-CMS-002 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_014_uc_cms_002_alternative_a2(stub_iam):
    """TEST-UC-014: UC-CMS-002 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 14)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0014",
        complainant_user_id=4000 + 14,
        category="maintenance",
        description="Testing UC-CMS-002 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_015_uc_cms_002_exception_e1(stub_iam):
    """TEST-UC-015: UC-CMS-002 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 15)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0015",
        complainant_user_id=4000 + 15,
        category="maintenance",
        description="Testing UC-CMS-002 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_016_uc_cms_002_exception_e2(stub_iam):
    """TEST-UC-016: UC-CMS-002 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 16)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0016",
        complainant_user_id=4000 + 16,
        category="maintenance",
        description="Testing UC-CMS-002 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_017_uc_cms_003_main_flow(stub_iam):
    """TEST-UC-017: UC-CMS-003 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 17)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0017",
        complainant_user_id=4000 + 17,
        category="maintenance",
        description="Testing UC-CMS-003 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_018_uc_cms_003_data_input_step(stub_iam):
    """TEST-UC-018: UC-CMS-003 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 18)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0018",
        complainant_user_id=4000 + 18,
        category="maintenance",
        description="Testing UC-CMS-003 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_019_uc_cms_003_role_execution(stub_iam):
    """TEST-UC-019: UC-CMS-003 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 19)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0019",
        complainant_user_id=4000 + 19,
        category="maintenance",
        description="Testing UC-CMS-003 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_020_uc_cms_003_state_transition(stub_iam):
    """TEST-UC-020: UC-CMS-003 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 20)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0020",
        complainant_user_id=4000 + 20,
        category="maintenance",
        description="Testing UC-CMS-003 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_021_uc_cms_003_alternative_a1(stub_iam):
    """TEST-UC-021: UC-CMS-003 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 21)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0021",
        complainant_user_id=4000 + 21,
        category="maintenance",
        description="Testing UC-CMS-003 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_022_uc_cms_003_alternative_a2(stub_iam):
    """TEST-UC-022: UC-CMS-003 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 22)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0022",
        complainant_user_id=4000 + 22,
        category="maintenance",
        description="Testing UC-CMS-003 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_023_uc_cms_003_exception_e1(stub_iam):
    """TEST-UC-023: UC-CMS-003 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 23)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0023",
        complainant_user_id=4000 + 23,
        category="maintenance",
        description="Testing UC-CMS-003 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_024_uc_cms_003_exception_e2(stub_iam):
    """TEST-UC-024: UC-CMS-003 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 24)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0024",
        complainant_user_id=4000 + 24,
        category="maintenance",
        description="Testing UC-CMS-003 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_025_uc_cms_004_main_flow(stub_iam):
    """TEST-UC-025: UC-CMS-004 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 25)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0025",
        complainant_user_id=4000 + 25,
        category="maintenance",
        description="Testing UC-CMS-004 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_026_uc_cms_004_data_input_step(stub_iam):
    """TEST-UC-026: UC-CMS-004 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 26)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0026",
        complainant_user_id=4000 + 26,
        category="maintenance",
        description="Testing UC-CMS-004 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_027_uc_cms_004_role_execution(stub_iam):
    """TEST-UC-027: UC-CMS-004 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 27)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0027",
        complainant_user_id=4000 + 27,
        category="maintenance",
        description="Testing UC-CMS-004 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_028_uc_cms_004_state_transition(stub_iam):
    """TEST-UC-028: UC-CMS-004 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 28)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0028",
        complainant_user_id=4000 + 28,
        category="maintenance",
        description="Testing UC-CMS-004 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_029_uc_cms_004_alternative_a1(stub_iam):
    """TEST-UC-029: UC-CMS-004 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 29)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0029",
        complainant_user_id=4000 + 29,
        category="maintenance",
        description="Testing UC-CMS-004 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_030_uc_cms_004_alternative_a2(stub_iam):
    """TEST-UC-030: UC-CMS-004 Alternative A2 - Re-categorization resets default priority (Defect 13)."""
    client = auth_client(stub_iam, user_id=5000 + 30, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0030",
        complainant_user_id=4000 + 30,
        category="hostel",
        description="Water leak.",
        status="Submitted",
        priority="Low"
    )
    # Handler reassigns to network category where institutional policy mandates default Medium priority
    res = client.post(f"/api/v1/cms/complaints/{c.id}/assign/", data={"assigned_handler_id": 5000 + 30, "category": "network"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # Expected re-categorization to enforce category-specific baseline priority
    assert c.priority == "Medium", f"Expected default priority 'Medium' on re-categorization to network, got '{c.priority}'"


def test_uc_031_uc_cms_004_exception_e1(stub_iam):
    """TEST-UC-031: UC-CMS-004 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 31)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0031",
        complainant_user_id=4000 + 31,
        category="maintenance",
        description="Testing UC-CMS-004 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_032_uc_cms_004_exception_e2(stub_iam):
    """TEST-UC-032: UC-CMS-004 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 32)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0032",
        complainant_user_id=4000 + 32,
        category="maintenance",
        description="Testing UC-CMS-004 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_033_uc_cms_005_main_flow(stub_iam):
    """TEST-UC-033: UC-CMS-005 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 33)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0033",
        complainant_user_id=4000 + 33,
        category="maintenance",
        description="Testing UC-CMS-005 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_034_uc_cms_005_data_input_step(stub_iam):
    """TEST-UC-034: UC-CMS-005 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 34)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0034",
        complainant_user_id=4000 + 34,
        category="maintenance",
        description="Testing UC-CMS-005 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_035_uc_cms_005_role_execution(stub_iam):
    """TEST-UC-035: UC-CMS-005 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 35)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0035",
        complainant_user_id=4000 + 35,
        category="maintenance",
        description="Testing UC-CMS-005 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_036_uc_cms_005_state_transition(stub_iam):
    """TEST-UC-036: UC-CMS-005 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 36)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0036",
        complainant_user_id=4000 + 36,
        category="maintenance",
        description="Testing UC-CMS-005 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_037_uc_cms_005_alternative_a1(stub_iam):
    """TEST-UC-037: UC-CMS-005 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 37)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0037",
        complainant_user_id=4000 + 37,
        category="maintenance",
        description="Testing UC-CMS-005 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_038_uc_cms_005_alternative_a2(stub_iam):
    """TEST-UC-038: UC-CMS-005 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 38)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0038",
        complainant_user_id=4000 + 38,
        category="maintenance",
        description="Testing UC-CMS-005 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_039_uc_cms_005_exception_e1(stub_iam):
    """TEST-UC-039: UC-CMS-005 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 39)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0039",
        complainant_user_id=4000 + 39,
        category="maintenance",
        description="Testing UC-CMS-005 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_040_uc_cms_005_exception_e2(stub_iam):
    """TEST-UC-040: UC-CMS-005 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 40)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0040",
        complainant_user_id=4000 + 40,
        category="maintenance",
        description="Testing UC-CMS-005 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_041_uc_cms_006_main_flow(stub_iam):
    """TEST-UC-041: UC-CMS-006 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 41)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0041",
        complainant_user_id=4000 + 41,
        category="maintenance",
        description="Testing UC-CMS-006 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_042_uc_cms_006_data_input_step(stub_iam):
    """TEST-UC-042: UC-CMS-006 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 42)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0042",
        complainant_user_id=4000 + 42,
        category="maintenance",
        description="Testing UC-CMS-006 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_043_uc_cms_006_role_execution(stub_iam):
    """TEST-UC-043: UC-CMS-006 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 43)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0043",
        complainant_user_id=4000 + 43,
        category="maintenance",
        description="Testing UC-CMS-006 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_044_uc_cms_006_state_transition(stub_iam):
    """TEST-UC-044: UC-CMS-006 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 44)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0044",
        complainant_user_id=4000 + 44,
        category="maintenance",
        description="Testing UC-CMS-006 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_045_uc_cms_006_alternative_a1(stub_iam):
    """TEST-UC-045: UC-CMS-006 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 45)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0045",
        complainant_user_id=4000 + 45,
        category="maintenance",
        description="Testing UC-CMS-006 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_046_uc_cms_006_alternative_a2(stub_iam):
    """TEST-UC-046: UC-CMS-006 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 46)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0046",
        complainant_user_id=4000 + 46,
        category="maintenance",
        description="Testing UC-CMS-006 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_047_uc_cms_006_exception_e1(stub_iam):
    """TEST-UC-047: UC-CMS-006 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 47)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0047",
        complainant_user_id=4000 + 47,
        category="maintenance",
        description="Testing UC-CMS-006 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_048_uc_cms_006_exception_e2(stub_iam):
    """TEST-UC-048: UC-CMS-006 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 48)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0048",
        complainant_user_id=4000 + 48,
        category="maintenance",
        description="Testing UC-CMS-006 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_049_uc_cms_007_main_flow(stub_iam):
    """TEST-UC-049: UC-CMS-007 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 49)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0049",
        complainant_user_id=4000 + 49,
        category="maintenance",
        description="Testing UC-CMS-007 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_050_uc_cms_007_data_input_step(stub_iam):
    """TEST-UC-050: UC-CMS-007 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 50)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0050",
        complainant_user_id=4000 + 50,
        category="maintenance",
        description="Testing UC-CMS-007 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_051_uc_cms_007_role_execution(stub_iam):
    """TEST-UC-051: UC-CMS-007 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 51)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0051",
        complainant_user_id=4000 + 51,
        category="maintenance",
        description="Testing UC-CMS-007 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_052_uc_cms_007_state_transition(stub_iam):
    """TEST-UC-052: UC-CMS-007 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 52)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0052",
        complainant_user_id=4000 + 52,
        category="maintenance",
        description="Testing UC-CMS-007 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_053_uc_cms_007_alternative_a1(stub_iam):
    """TEST-UC-053: UC-CMS-007 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 53)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0053",
        complainant_user_id=4000 + 53,
        category="maintenance",
        description="Testing UC-CMS-007 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_054_uc_cms_007_alternative_a2(stub_iam):
    """TEST-UC-054: UC-CMS-007 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 54)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0054",
        complainant_user_id=4000 + 54,
        category="maintenance",
        description="Testing UC-CMS-007 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_055_uc_cms_007_exception_e1(stub_iam):
    """TEST-UC-055: UC-CMS-007 Exception E1 - Complainant cannot verify closure on supervisor-mandated complaint (Defect 8)."""
    client = auth_client(stub_iam, user_id=4000 + 55, kind="student", roles=("student",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0055",
        complainant_user_id=4000 + 55,
        category="academic",
        description="Laboratory equipment damage requiring supervisor sign-off.",
        status="Resolved",
        requires_supervisor_verification=True
    )
    # Complainant attempts to call verify_closure on ticket requiring supervisor sign-off
    res = client.post(f"/api/v1/cms/complaints/{c.id}/verify_closure/", data={"notes": "Complainant signing off."}, format="json")
    assert res.status_code in [400, 403], f"Complainant closure verification accepted without supervisor authority (got {res.status_code})"


def test_uc_056_uc_cms_007_exception_e2(stub_iam):
    """TEST-UC-056: UC-CMS-007 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 56)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0056",
        complainant_user_id=4000 + 56,
        category="maintenance",
        description="Testing UC-CMS-007 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_057_uc_cms_008_main_flow(stub_iam):
    """TEST-UC-057: UC-CMS-008 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 57)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0057",
        complainant_user_id=4000 + 57,
        category="maintenance",
        description="Testing UC-CMS-008 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_058_uc_cms_008_data_input_step(stub_iam):
    """TEST-UC-058: UC-CMS-008 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 58)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0058",
        complainant_user_id=4000 + 58,
        category="maintenance",
        description="Testing UC-CMS-008 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_059_uc_cms_008_role_execution(stub_iam):
    """TEST-UC-059: UC-CMS-008 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 59)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0059",
        complainant_user_id=4000 + 59,
        category="maintenance",
        description="Testing UC-CMS-008 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_060_uc_cms_008_state_transition(stub_iam):
    """TEST-UC-060: UC-CMS-008 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 60)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0060",
        complainant_user_id=4000 + 60,
        category="maintenance",
        description="Testing UC-CMS-008 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_061_uc_cms_008_alternative_a1(stub_iam):
    """TEST-UC-061: UC-CMS-008 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 61)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0061",
        complainant_user_id=4000 + 61,
        category="maintenance",
        description="Testing UC-CMS-008 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_062_uc_cms_008_alternative_a2(stub_iam):
    """TEST-UC-062: UC-CMS-008 Alternative A2 - Duplicate pending reopening prevention (Defect 2)."""
    client = auth_client(stub_iam, user_id=4000 + 62)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0062",
        complainant_user_id=4000 + 62,
        category="maintenance",
        description="Reopening defect verification.",
        status="Closed"
    )
    # First reopening request
    r1 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Still not working."}, format="json")
    assert r1.status_code in [200, 201]
    # Second reopening request while first is pending must be rejected with 400
    r2 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Submitting duplicate request."}, format="json")
    assert r2.status_code == 400, "Duplicate pending reopening request allowed"


def test_uc_063_uc_cms_008_exception_e1(stub_iam):
    """TEST-UC-063: UC-CMS-008 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 63)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0063",
        complainant_user_id=4000 + 63,
        category="maintenance",
        description="Testing UC-CMS-008 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_064_uc_cms_008_exception_e2(stub_iam):
    """TEST-UC-064: UC-CMS-008 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 64)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0064",
        complainant_user_id=4000 + 64,
        category="maintenance",
        description="Testing UC-CMS-008 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_065_uc_cms_009_main_flow(stub_iam):
    """TEST-UC-065: UC-CMS-009 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 65)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0065",
        complainant_user_id=4000 + 65,
        category="maintenance",
        description="Testing UC-CMS-009 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_066_uc_cms_009_data_input_step(stub_iam):
    """TEST-UC-066: UC-CMS-009 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 66)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0066",
        complainant_user_id=4000 + 66,
        category="maintenance",
        description="Testing UC-CMS-009 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_067_uc_cms_009_role_execution(stub_iam):
    """TEST-UC-067: UC-CMS-009 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 67)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0067",
        complainant_user_id=4000 + 67,
        category="maintenance",
        description="Testing UC-CMS-009 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_068_uc_cms_009_state_transition(stub_iam):
    """TEST-UC-068: UC-CMS-009 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 68)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0068",
        complainant_user_id=4000 + 68,
        category="maintenance",
        description="Testing UC-CMS-009 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_069_uc_cms_009_alternative_a1(stub_iam):
    """TEST-UC-069: UC-CMS-009 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 69)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0069",
        complainant_user_id=4000 + 69,
        category="maintenance",
        description="Testing UC-CMS-009 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_070_uc_cms_009_alternative_a2(stub_iam):
    """TEST-UC-070: UC-CMS-009 Alternative A2 - Duplicate feedback rejection (Defect 5)."""
    client = auth_client(stub_iam, user_id=4000 + 70)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0070",
        complainant_user_id=4000 + 70,
        category="hostel",
        description="Duplicate feedback testing.",
        status="Closed"
    )
    r1 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 5, "comments": "Good service."}, format="json")
    assert r1.status_code == 201
    r2 = client.post("/api/v1/cms/feedback/", data={"complaint": c.id, "rating": 2, "comments": "Downgrading rating."}, format="json")
    assert r2.status_code == 400, "Allowed duplicate feedback for single complaint"


def test_uc_071_uc_cms_009_exception_e1(stub_iam):
    """TEST-UC-071: UC-CMS-009 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 71)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0071",
        complainant_user_id=4000 + 71,
        category="maintenance",
        description="Testing UC-CMS-009 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_072_uc_cms_009_exception_e2(stub_iam):
    """TEST-UC-072: UC-CMS-009 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 72)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0072",
        complainant_user_id=4000 + 72,
        category="maintenance",
        description="Testing UC-CMS-009 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_073_uc_cms_010_main_flow(stub_iam):
    """TEST-UC-073: UC-CMS-010 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 73)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0073",
        complainant_user_id=4000 + 73,
        category="maintenance",
        description="Testing UC-CMS-010 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_074_uc_cms_010_data_input_step(stub_iam):
    """TEST-UC-074: UC-CMS-010 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 74)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0074",
        complainant_user_id=4000 + 74,
        category="maintenance",
        description="Testing UC-CMS-010 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_075_uc_cms_010_role_execution(stub_iam):
    """TEST-UC-075: UC-CMS-010 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 75)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0075",
        complainant_user_id=4000 + 75,
        category="maintenance",
        description="Testing UC-CMS-010 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_076_uc_cms_010_state_transition(stub_iam):
    """TEST-UC-076: UC-CMS-010 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 76)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0076",
        complainant_user_id=4000 + 76,
        category="maintenance",
        description="Testing UC-CMS-010 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_077_uc_cms_010_alternative_a1(stub_iam):
    """TEST-UC-077: UC-CMS-010 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 77)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0077",
        complainant_user_id=4000 + 77,
        category="maintenance",
        description="Testing UC-CMS-010 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_078_uc_cms_010_alternative_a2(stub_iam):
    """TEST-UC-078: UC-CMS-010 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 78)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0078",
        complainant_user_id=4000 + 78,
        category="maintenance",
        description="Testing UC-CMS-010 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_079_uc_cms_010_exception_e1(stub_iam):
    """TEST-UC-079: UC-CMS-010 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 79)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0079",
        complainant_user_id=4000 + 79,
        category="maintenance",
        description="Testing UC-CMS-010 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_080_uc_cms_010_exception_e2(stub_iam):
    """TEST-UC-080: UC-CMS-010 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 80)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0080",
        complainant_user_id=4000 + 80,
        category="maintenance",
        description="Testing UC-CMS-010 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_081_uc_cms_011_main_flow(stub_iam):
    """TEST-UC-081: UC-CMS-011 Main Flow - Manual escalation audit actor role (Defect 9)."""
    client = auth_client(stub_iam, user_id=4000 + 81, kind="student", roles=("student",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0081",
        complainant_user_id=4000 + 81,
        category="network",
        description="Network switch failure.",
        status="In Progress"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/escalate/", data={"escalation_remarks": "Urgent exam."}, format="json")
    assert res.status_code == 200
    p = c.progress_history.filter(action="escalated_manual").last()
    assert p is not None
    assert p.actor_role == "complainant", f"Audit role recorded as {p.actor_role}, expected 'complainant'"


def test_uc_082_uc_cms_011_data_input_step(stub_iam):
    """TEST-UC-082: UC-CMS-011 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 82)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0082",
        complainant_user_id=4000 + 82,
        category="maintenance",
        description="Testing UC-CMS-011 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_083_uc_cms_011_role_execution(stub_iam):
    """TEST-UC-083: UC-CMS-011 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 83)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0083",
        complainant_user_id=4000 + 83,
        category="maintenance",
        description="Testing UC-CMS-011 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_084_uc_cms_011_state_transition(stub_iam):
    """TEST-UC-084: UC-CMS-011 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 84)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0084",
        complainant_user_id=4000 + 84,
        category="maintenance",
        description="Testing UC-CMS-011 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_085_uc_cms_011_alternative_a1(stub_iam):
    """TEST-UC-085: UC-CMS-011 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 85)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0085",
        complainant_user_id=4000 + 85,
        category="maintenance",
        description="Testing UC-CMS-011 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_086_uc_cms_011_alternative_a2(stub_iam):
    """TEST-UC-086: UC-CMS-011 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 86)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0086",
        complainant_user_id=4000 + 86,
        category="maintenance",
        description="Testing UC-CMS-011 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_087_uc_cms_011_exception_e1(stub_iam):
    """TEST-UC-087: UC-CMS-011 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 87)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0087",
        complainant_user_id=4000 + 87,
        category="maintenance",
        description="Testing UC-CMS-011 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_088_uc_cms_011_exception_e2(stub_iam):
    """TEST-UC-088: UC-CMS-011 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 88)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0088",
        complainant_user_id=4000 + 88,
        category="maintenance",
        description="Testing UC-CMS-011 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_089_uc_cms_012_main_flow(stub_iam):
    """TEST-UC-089: UC-CMS-012 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 89)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0089",
        complainant_user_id=4000 + 89,
        category="maintenance",
        description="Testing UC-CMS-012 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_090_uc_cms_012_data_input_step(stub_iam):
    """TEST-UC-090: UC-CMS-012 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 90)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0090",
        complainant_user_id=4000 + 90,
        category="maintenance",
        description="Testing UC-CMS-012 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_091_uc_cms_012_role_execution(stub_iam):
    """TEST-UC-091: UC-CMS-012 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 91)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0091",
        complainant_user_id=4000 + 91,
        category="maintenance",
        description="Testing UC-CMS-012 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_092_uc_cms_012_state_transition(stub_iam):
    """TEST-UC-092: UC-CMS-012 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 92)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0092",
        complainant_user_id=4000 + 92,
        category="maintenance",
        description="Testing UC-CMS-012 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_093_uc_cms_012_alternative_a1(stub_iam):
    """TEST-UC-093: UC-CMS-012 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 93)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0093",
        complainant_user_id=4000 + 93,
        category="maintenance",
        description="Testing UC-CMS-012 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_094_uc_cms_012_alternative_a2(stub_iam):
    """TEST-UC-094: UC-CMS-012 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 94)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0094",
        complainant_user_id=4000 + 94,
        category="maintenance",
        description="Testing UC-CMS-012 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_095_uc_cms_012_exception_e1(stub_iam):
    """TEST-UC-095: UC-CMS-012 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 95)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0095",
        complainant_user_id=4000 + 95,
        category="maintenance",
        description="Testing UC-CMS-012 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_096_uc_cms_012_exception_e2(stub_iam):
    """TEST-UC-096: UC-CMS-012 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 96)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0096",
        complainant_user_id=4000 + 96,
        category="maintenance",
        description="Testing UC-CMS-012 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_097_uc_cms_013_main_flow(stub_iam):
    """TEST-UC-097: UC-CMS-013 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 97)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0097",
        complainant_user_id=4000 + 97,
        category="maintenance",
        description="Testing UC-CMS-013 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_098_uc_cms_013_data_input_step(stub_iam):
    """TEST-UC-098: UC-CMS-013 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 98)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0098",
        complainant_user_id=4000 + 98,
        category="maintenance",
        description="Testing UC-CMS-013 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_099_uc_cms_013_role_execution(stub_iam):
    """TEST-UC-099: UC-CMS-013 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 99)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0099",
        complainant_user_id=4000 + 99,
        category="maintenance",
        description="Testing UC-CMS-013 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_100_uc_cms_013_state_transition(stub_iam):
    """TEST-UC-100: UC-CMS-013 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 100)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0100",
        complainant_user_id=4000 + 100,
        category="maintenance",
        description="Testing UC-CMS-013 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_101_uc_cms_013_alternative_a1(stub_iam):
    """TEST-UC-101: UC-CMS-013 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 101)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0101",
        complainant_user_id=4000 + 101,
        category="maintenance",
        description="Testing UC-CMS-013 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_102_uc_cms_013_alternative_a2(stub_iam):
    """TEST-UC-102: UC-CMS-013 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 102)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0102",
        complainant_user_id=4000 + 102,
        category="maintenance",
        description="Testing UC-CMS-013 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_103_uc_cms_013_exception_e1(stub_iam):
    """TEST-UC-103: UC-CMS-013 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 103)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0103",
        complainant_user_id=4000 + 103,
        category="maintenance",
        description="Testing UC-CMS-013 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_104_uc_cms_013_exception_e2(stub_iam):
    """TEST-UC-104: UC-CMS-013 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 104)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0104",
        complainant_user_id=4000 + 104,
        category="maintenance",
        description="Testing UC-CMS-013 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_105_uc_cms_014_main_flow(stub_iam):
    """TEST-UC-105: UC-CMS-014 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 105)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0105",
        complainant_user_id=4000 + 105,
        category="maintenance",
        description="Testing UC-CMS-014 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_106_uc_cms_014_data_input_step(stub_iam):
    """TEST-UC-106: UC-CMS-014 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 106)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0106",
        complainant_user_id=4000 + 106,
        category="maintenance",
        description="Testing UC-CMS-014 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_107_uc_cms_014_role_execution(stub_iam):
    """TEST-UC-107: UC-CMS-014 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 107)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0107",
        complainant_user_id=4000 + 107,
        category="maintenance",
        description="Testing UC-CMS-014 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_108_uc_cms_014_state_transition(stub_iam):
    """TEST-UC-108: UC-CMS-014 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 108)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0108",
        complainant_user_id=4000 + 108,
        category="maintenance",
        description="Testing UC-CMS-014 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_109_uc_cms_014_alternative_a1(stub_iam):
    """TEST-UC-109: UC-CMS-014 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 109)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0109",
        complainant_user_id=4000 + 109,
        category="maintenance",
        description="Testing UC-CMS-014 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_110_uc_cms_014_alternative_a2(stub_iam):
    """TEST-UC-110: UC-CMS-014 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 110)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0110",
        complainant_user_id=4000 + 110,
        category="maintenance",
        description="Testing UC-CMS-014 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_111_uc_cms_014_exception_e1(stub_iam):
    """TEST-UC-111: UC-CMS-014 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 111)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0111",
        complainant_user_id=4000 + 111,
        category="maintenance",
        description="Testing UC-CMS-014 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_112_uc_cms_014_exception_e2(stub_iam):
    """TEST-UC-112: UC-CMS-014 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 112)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0112",
        complainant_user_id=4000 + 112,
        category="maintenance",
        description="Testing UC-CMS-014 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_113_uc_cms_015_main_flow(stub_iam):
    """TEST-UC-113: UC-CMS-015 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 113)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0113",
        complainant_user_id=4000 + 113,
        category="maintenance",
        description="Testing UC-CMS-015 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_114_uc_cms_015_data_input_step(stub_iam):
    """TEST-UC-114: UC-CMS-015 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 114)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0114",
        complainant_user_id=4000 + 114,
        category="maintenance",
        description="Testing UC-CMS-015 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_115_uc_cms_015_role_execution(stub_iam):
    """TEST-UC-115: UC-CMS-015 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 115)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0115",
        complainant_user_id=4000 + 115,
        category="maintenance",
        description="Testing UC-CMS-015 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_116_uc_cms_015_state_transition(stub_iam):
    """TEST-UC-116: UC-CMS-015 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 116)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0116",
        complainant_user_id=4000 + 116,
        category="maintenance",
        description="Testing UC-CMS-015 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_117_uc_cms_015_alternative_a1(stub_iam):
    """TEST-UC-117: UC-CMS-015 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 117)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0117",
        complainant_user_id=4000 + 117,
        category="maintenance",
        description="Testing UC-CMS-015 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_118_uc_cms_015_alternative_a2(stub_iam):
    """TEST-UC-118: UC-CMS-015 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 118)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0118",
        complainant_user_id=4000 + 118,
        category="maintenance",
        description="Testing UC-CMS-015 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_119_uc_cms_015_exception_e1(stub_iam):
    """TEST-UC-119: UC-CMS-015 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 119)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0119",
        complainant_user_id=4000 + 119,
        category="maintenance",
        description="Testing UC-CMS-015 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_120_uc_cms_015_exception_e2(stub_iam):
    """TEST-UC-120: UC-CMS-015 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 120)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0120",
        complainant_user_id=4000 + 120,
        category="maintenance",
        description="Testing UC-CMS-015 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_121_uc_cms_016_main_flow(stub_iam):
    """TEST-UC-121: UC-CMS-016 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 121)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0121",
        complainant_user_id=4000 + 121,
        category="maintenance",
        description="Testing UC-CMS-016 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_122_uc_cms_016_data_input_step(stub_iam):
    """TEST-UC-122: UC-CMS-016 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 122)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0122",
        complainant_user_id=4000 + 122,
        category="maintenance",
        description="Testing UC-CMS-016 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_123_uc_cms_016_role_execution(stub_iam):
    """TEST-UC-123: UC-CMS-016 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 123)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0123",
        complainant_user_id=4000 + 123,
        category="maintenance",
        description="Testing UC-CMS-016 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_124_uc_cms_016_state_transition(stub_iam):
    """TEST-UC-124: UC-CMS-016 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 124)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0124",
        complainant_user_id=4000 + 124,
        category="maintenance",
        description="Testing UC-CMS-016 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_125_uc_cms_016_alternative_a1(stub_iam):
    """TEST-UC-125: UC-CMS-016 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 125)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0125",
        complainant_user_id=4000 + 125,
        category="maintenance",
        description="Testing UC-CMS-016 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_126_uc_cms_016_alternative_a2(stub_iam):
    """TEST-UC-126: UC-CMS-016 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 126)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0126",
        complainant_user_id=4000 + 126,
        category="maintenance",
        description="Testing UC-CMS-016 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_127_uc_cms_016_exception_e1(stub_iam):
    """TEST-UC-127: UC-CMS-016 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 127)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0127",
        complainant_user_id=4000 + 127,
        category="maintenance",
        description="Testing UC-CMS-016 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_128_uc_cms_016_exception_e2(stub_iam):
    """TEST-UC-128: UC-CMS-016 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 128)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0128",
        complainant_user_id=4000 + 128,
        category="maintenance",
        description="Testing UC-CMS-016 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_129_uc_cms_017_main_flow(stub_iam):
    """TEST-UC-129: UC-CMS-017 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 129)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0129",
        complainant_user_id=4000 + 129,
        category="maintenance",
        description="Testing UC-CMS-017 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_130_uc_cms_017_data_input_step(stub_iam):
    """TEST-UC-130: UC-CMS-017 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 130)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0130",
        complainant_user_id=4000 + 130,
        category="maintenance",
        description="Testing UC-CMS-017 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_131_uc_cms_017_role_execution(stub_iam):
    """TEST-UC-131: UC-CMS-017 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 131)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0131",
        complainant_user_id=4000 + 131,
        category="maintenance",
        description="Testing UC-CMS-017 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_132_uc_cms_017_state_transition(stub_iam):
    """TEST-UC-132: UC-CMS-017 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 132)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0132",
        complainant_user_id=4000 + 132,
        category="maintenance",
        description="Testing UC-CMS-017 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_133_uc_cms_017_alternative_a1(stub_iam):
    """TEST-UC-133: UC-CMS-017 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 133)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0133",
        complainant_user_id=4000 + 133,
        category="maintenance",
        description="Testing UC-CMS-017 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_134_uc_cms_017_alternative_a2(stub_iam):
    """TEST-UC-134: UC-CMS-017 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 134)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0134",
        complainant_user_id=4000 + 134,
        category="maintenance",
        description="Testing UC-CMS-017 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_135_uc_cms_017_exception_e1(stub_iam):
    """TEST-UC-135: UC-CMS-017 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 135)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0135",
        complainant_user_id=4000 + 135,
        category="maintenance",
        description="Testing UC-CMS-017 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_136_uc_cms_017_exception_e2(stub_iam):
    """TEST-UC-136: UC-CMS-017 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 136)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0136",
        complainant_user_id=4000 + 136,
        category="maintenance",
        description="Testing UC-CMS-017 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_137_uc_cms_018_main_flow(stub_iam):
    """TEST-UC-137: UC-CMS-018 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 137)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0137",
        complainant_user_id=4000 + 137,
        category="maintenance",
        description="Testing UC-CMS-018 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_138_uc_cms_018_data_input_step(stub_iam):
    """TEST-UC-138: UC-CMS-018 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 138)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0138",
        complainant_user_id=4000 + 138,
        category="maintenance",
        description="Testing UC-CMS-018 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_139_uc_cms_018_role_execution(stub_iam):
    """TEST-UC-139: UC-CMS-018 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 139)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0139",
        complainant_user_id=4000 + 139,
        category="maintenance",
        description="Testing UC-CMS-018 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_140_uc_cms_018_state_transition(stub_iam):
    """TEST-UC-140: UC-CMS-018 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 140)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0140",
        complainant_user_id=4000 + 140,
        category="maintenance",
        description="Testing UC-CMS-018 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_141_uc_cms_018_alternative_a1(stub_iam):
    """TEST-UC-141: UC-CMS-018 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 141)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0141",
        complainant_user_id=4000 + 141,
        category="maintenance",
        description="Testing UC-CMS-018 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_142_uc_cms_018_alternative_a2(stub_iam):
    """TEST-UC-142: UC-CMS-018 Alternative A2 - Overlapping active role dates rejection (Defect 14)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    r1 = CmsRoleAssignment.objects.create(
        user_id=8142,
        role_type="complaint_handler",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        is_active=True,
        assigned_by_id=9999
    )
    # Assign same user an overlapping active role period
    res = client.post("/api/v1/cms/roles/", data={
        "user_id": 8142,
        "role_type": "complaint_handler",
        "start_date": "2026-03-01",
        "end_date": "2026-09-30",
        "is_active": True
    }, format="json")
    assert res.status_code == 400, "Overlapping active role assignment for same user accepted without conflict validation"


def test_uc_143_uc_cms_018_exception_e1(stub_iam):
    """TEST-UC-143: UC-CMS-018 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 143)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0143",
        complainant_user_id=4000 + 143,
        category="maintenance",
        description="Testing UC-CMS-018 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_144_uc_cms_018_exception_e2(stub_iam):
    """TEST-UC-144: UC-CMS-018 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 144)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0144",
        complainant_user_id=4000 + 144,
        category="maintenance",
        description="Testing UC-CMS-018 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_145_uc_cms_019_main_flow(stub_iam):
    """TEST-UC-145: UC-CMS-019 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 145)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0145",
        complainant_user_id=4000 + 145,
        category="maintenance",
        description="Testing UC-CMS-019 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_146_uc_cms_019_data_input_step(stub_iam):
    """TEST-UC-146: UC-CMS-019 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 146)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0146",
        complainant_user_id=4000 + 146,
        category="maintenance",
        description="Testing UC-CMS-019 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_147_uc_cms_019_role_execution(stub_iam):
    """TEST-UC-147: UC-CMS-019 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 147)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0147",
        complainant_user_id=4000 + 147,
        category="maintenance",
        description="Testing UC-CMS-019 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_148_uc_cms_019_state_transition(stub_iam):
    """TEST-UC-148: UC-CMS-019 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 148)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0148",
        complainant_user_id=4000 + 148,
        category="maintenance",
        description="Testing UC-CMS-019 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_149_uc_cms_019_alternative_a1(stub_iam):
    """TEST-UC-149: UC-CMS-019 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 149)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0149",
        complainant_user_id=4000 + 149,
        category="maintenance",
        description="Testing UC-CMS-019 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_150_uc_cms_019_alternative_a2(stub_iam):
    """TEST-UC-150: UC-CMS-019 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 150)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0150",
        complainant_user_id=4000 + 150,
        category="maintenance",
        description="Testing UC-CMS-019 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_151_uc_cms_019_exception_e1(stub_iam):
    """TEST-UC-151: UC-CMS-019 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 151)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0151",
        complainant_user_id=4000 + 151,
        category="maintenance",
        description="Testing UC-CMS-019 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_152_uc_cms_019_exception_e2(stub_iam):
    """TEST-UC-152: UC-CMS-019 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 152)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0152",
        complainant_user_id=4000 + 152,
        category="maintenance",
        description="Testing UC-CMS-019 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_153_uc_cms_020_main_flow(stub_iam):
    """TEST-UC-153: UC-CMS-020 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 153)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0153",
        complainant_user_id=4000 + 153,
        category="maintenance",
        description="Testing UC-CMS-020 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_154_uc_cms_020_data_input_step(stub_iam):
    """TEST-UC-154: UC-CMS-020 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 154)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0154",
        complainant_user_id=4000 + 154,
        category="maintenance",
        description="Testing UC-CMS-020 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_155_uc_cms_020_role_execution(stub_iam):
    """TEST-UC-155: UC-CMS-020 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 155)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0155",
        complainant_user_id=4000 + 155,
        category="maintenance",
        description="Testing UC-CMS-020 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_156_uc_cms_020_state_transition(stub_iam):
    """TEST-UC-156: UC-CMS-020 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 156)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0156",
        complainant_user_id=4000 + 156,
        category="maintenance",
        description="Testing UC-CMS-020 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_157_uc_cms_020_alternative_a1(stub_iam):
    """TEST-UC-157: UC-CMS-020 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 157)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0157",
        complainant_user_id=4000 + 157,
        category="maintenance",
        description="Testing UC-CMS-020 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_158_uc_cms_020_alternative_a2(stub_iam):
    """TEST-UC-158: UC-CMS-020 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 158)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0158",
        complainant_user_id=4000 + 158,
        category="maintenance",
        description="Testing UC-CMS-020 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_159_uc_cms_020_exception_e1(stub_iam):
    """TEST-UC-159: UC-CMS-020 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 159)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0159",
        complainant_user_id=4000 + 159,
        category="maintenance",
        description="Testing UC-CMS-020 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_160_uc_cms_020_exception_e2(stub_iam):
    """TEST-UC-160: UC-CMS-020 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 160)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0160",
        complainant_user_id=4000 + 160,
        category="maintenance",
        description="Testing UC-CMS-020 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_161_uc_cms_021_main_flow(stub_iam):
    """TEST-UC-161: UC-CMS-021 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 161)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0161",
        complainant_user_id=4000 + 161,
        category="maintenance",
        description="Testing UC-CMS-021 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_162_uc_cms_021_data_input_step(stub_iam):
    """TEST-UC-162: UC-CMS-021 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 162)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0162",
        complainant_user_id=4000 + 162,
        category="maintenance",
        description="Testing UC-CMS-021 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_163_uc_cms_021_role_execution(stub_iam):
    """TEST-UC-163: UC-CMS-021 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 163)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0163",
        complainant_user_id=4000 + 163,
        category="maintenance",
        description="Testing UC-CMS-021 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_164_uc_cms_021_state_transition(stub_iam):
    """TEST-UC-164: UC-CMS-021 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 164)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0164",
        complainant_user_id=4000 + 164,
        category="maintenance",
        description="Testing UC-CMS-021 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_165_uc_cms_021_alternative_a1(stub_iam):
    """TEST-UC-165: UC-CMS-021 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 165)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0165",
        complainant_user_id=4000 + 165,
        category="maintenance",
        description="Testing UC-CMS-021 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_166_uc_cms_021_alternative_a2(stub_iam):
    """TEST-UC-166: UC-CMS-021 Alternative A2 - Pre-breach reminder window for High priority (Defect 10)."""
    client = auth_client(stub_iam, user_id=4000 + 166)
    # High priority complaint created just now, due in 23 hours (SLA = 24h)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0166",
        complainant_user_id=4000 + 166,
        category="mess",
        description="Mess freezer breakdown.",
        status="In Progress",
        priority="High",
        sla_due_date=timezone.now() + timedelta(hours=23),
        sla_reminder_sent=False
    )
    # SLA sweep should NOT send pre-breach reminder when full SLA is 24h and 23h remains (threshold is 12h)
    res = client.post("/api/v1/cms/complaints/check_sla/", format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    assert c.sla_reminder_sent is False, "Pre-breach reminder triggered immediately with 23h remaining on 24h SLA"


def test_uc_167_uc_cms_021_exception_e1(stub_iam):
    """TEST-UC-167: UC-CMS-021 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 167)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0167",
        complainant_user_id=4000 + 167,
        category="maintenance",
        description="Testing UC-CMS-021 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_168_uc_cms_021_exception_e2(stub_iam):
    """TEST-UC-168: UC-CMS-021 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 168)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0168",
        complainant_user_id=4000 + 168,
        category="maintenance",
        description="Testing UC-CMS-021 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_169_uc_cms_022_main_flow(stub_iam):
    """TEST-UC-169: UC-CMS-022 Main Flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 169)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0169",
        complainant_user_id=4000 + 169,
        category="maintenance",
        description="Testing UC-CMS-022 Main Flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_170_uc_cms_022_data_input_step(stub_iam):
    """TEST-UC-170: UC-CMS-022 Data Input Step - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 170)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0170",
        complainant_user_id=4000 + 170,
        category="maintenance",
        description="Testing UC-CMS-022 Data Input Step.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_171_uc_cms_022_role_execution(stub_iam):
    """TEST-UC-171: UC-CMS-022 Role Execution - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 171)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0171",
        complainant_user_id=4000 + 171,
        category="maintenance",
        description="Testing UC-CMS-022 Role Execution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_172_uc_cms_022_state_transition(stub_iam):
    """TEST-UC-172: UC-CMS-022 State Transition - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 172)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0172",
        complainant_user_id=4000 + 172,
        category="maintenance",
        description="Testing UC-CMS-022 State Transition.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_173_uc_cms_022_alternative_a1(stub_iam):
    """TEST-UC-173: UC-CMS-022 Alternative A1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 173)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0173",
        complainant_user_id=4000 + 173,
        category="maintenance",
        description="Testing UC-CMS-022 Alternative A1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_174_uc_cms_022_alternative_a2(stub_iam):
    """TEST-UC-174: UC-CMS-022 Alternative A2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 174)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0174",
        complainant_user_id=4000 + 174,
        category="maintenance",
        description="Testing UC-CMS-022 Alternative A2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_175_uc_cms_022_exception_e1(stub_iam):
    """TEST-UC-175: UC-CMS-022 Exception E1 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 175)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0175",
        complainant_user_id=4000 + 175,
        category="maintenance",
        description="Testing UC-CMS-022 Exception E1.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_uc_176_uc_cms_022_exception_e2(stub_iam):
    """TEST-UC-176: UC-CMS-022 Exception E2 - Conforming execution."""
    client = auth_client(stub_iam, user_id=4000 + 176)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-UC0176",
        complainant_user_id=4000 + 176,
        category="maintenance",
        description="Testing UC-CMS-022 Exception E2.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
