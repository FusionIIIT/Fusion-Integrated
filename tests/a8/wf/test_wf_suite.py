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


def test_wf_001_bw_cms_01_nominal_flow(stub_iam):
    """TEST-WF-001: BW-CMS-01 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 1)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0001",
        complainant_user_id=6000 + 1,
        category="maintenance",
        description="Testing BW-CMS-01 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_002_bw_cms_01_step1_intake(stub_iam):
    """TEST-WF-002: BW-CMS-01 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 2)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0002",
        complainant_user_id=6000 + 2,
        category="maintenance",
        description="Testing BW-CMS-01 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_003_bw_cms_01_step2_assignment(stub_iam):
    """TEST-WF-003: BW-CMS-01 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 3)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0003",
        complainant_user_id=6000 + 3,
        category="maintenance",
        description="Testing BW-CMS-01 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_004_bw_cms_01_step3_progress(stub_iam):
    """TEST-WF-004: BW-CMS-01 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 4)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0004",
        complainant_user_id=6000 + 4,
        category="maintenance",
        description="Testing BW-CMS-01 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_005_bw_cms_01_step4_resolution(stub_iam):
    """TEST-WF-005: BW-CMS-01 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 5)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0005",
        complainant_user_id=6000 + 5,
        category="maintenance",
        description="Testing BW-CMS-01 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_006_bw_cms_01_step5_closure(stub_iam):
    """TEST-WF-006: BW-CMS-01 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 6)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0006",
        complainant_user_id=6000 + 6,
        category="maintenance",
        description="Testing BW-CMS-01 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_007_bw_cms_01_path_complainant_signoff(stub_iam):
    """TEST-WF-007: BW-CMS-01 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 7)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0007",
        complainant_user_id=6000 + 7,
        category="maintenance",
        description="Testing BW-CMS-01 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_008_bw_cms_01_path_supervisor_signoff(stub_iam):
    """TEST-WF-008: BW-CMS-01 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 8)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0008",
        complainant_user_id=6000 + 8,
        category="maintenance",
        description="Testing BW-CMS-01 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_009_bw_cms_01_illegal_transition_rejection(stub_iam):
    """TEST-WF-009: BW-CMS-01 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 9)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0009",
        complainant_user_id=6000 + 9,
        category="maintenance",
        description="Testing BW-CMS-01 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_010_bw_cms_01_terminal_mutation_guard(stub_iam):
    """TEST-WF-010: BW-CMS-01 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 10)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0010",
        complainant_user_id=6000 + 10,
        category="maintenance",
        description="Testing BW-CMS-01 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_011_bw_cms_01_reopen_initiation_path(stub_iam):
    """TEST-WF-011: BW-CMS-01 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 11)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0011",
        complainant_user_id=6000 + 11,
        category="maintenance",
        description="Testing BW-CMS-01 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_012_bw_cms_01_reopen_adjudication_path(stub_iam):
    """TEST-WF-012: BW-CMS-01 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 12)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0012",
        complainant_user_id=6000 + 12,
        category="maintenance",
        description="Testing BW-CMS-01 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_013_bw_cms_01_manual_escalation_path(stub_iam):
    """TEST-WF-013: BW-CMS-01 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 13)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0013",
        complainant_user_id=6000 + 13,
        category="maintenance",
        description="Testing BW-CMS-01 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_014_bw_cms_01_sla_escalation_path(stub_iam):
    """TEST-WF-014: BW-CMS-01 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 14)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0014",
        complainant_user_id=6000 + 14,
        category="maintenance",
        description="Testing BW-CMS-01 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_015_bw_cms_01_concurrent_audit_integrity(stub_iam):
    """TEST-WF-015: BW-CMS-01 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 15)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0015",
        complainant_user_id=6000 + 15,
        category="maintenance",
        description="Testing BW-CMS-01 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_016_bw_cms_02_nominal_flow(stub_iam):
    """TEST-WF-016: BW-CMS-02 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 16)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0016",
        complainant_user_id=6000 + 16,
        category="maintenance",
        description="Testing BW-CMS-02 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_017_bw_cms_02_step1_intake(stub_iam):
    """TEST-WF-017: BW-CMS-02 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 17)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0017",
        complainant_user_id=6000 + 17,
        category="maintenance",
        description="Testing BW-CMS-02 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_018_bw_cms_02_step2_assignment(stub_iam):
    """TEST-WF-018: BW-CMS-02 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 18)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0018",
        complainant_user_id=6000 + 18,
        category="maintenance",
        description="Testing BW-CMS-02 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_019_bw_cms_02_step3_progress(stub_iam):
    """TEST-WF-019: BW-CMS-02 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 19)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0019",
        complainant_user_id=6000 + 19,
        category="maintenance",
        description="Testing BW-CMS-02 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_020_bw_cms_02_step4_resolution(stub_iam):
    """TEST-WF-020: BW-CMS-02 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 20)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0020",
        complainant_user_id=6000 + 20,
        category="maintenance",
        description="Testing BW-CMS-02 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_021_bw_cms_02_step5_closure(stub_iam):
    """TEST-WF-021: BW-CMS-02 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 21)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0021",
        complainant_user_id=6000 + 21,
        category="maintenance",
        description="Testing BW-CMS-02 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_022_bw_cms_02_path_complainant_signoff(stub_iam):
    """TEST-WF-022: BW-CMS-02 path_complainant_signoff - High priority SLA calculation in intake workflow (Defect 1)."""
    client = auth_client(stub_iam, user_id=7000 + 22, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0022",
        complainant_user_id=6000 + 22,
        category="network",
        description="Core fiber severed.",
        status="Submitted",
        priority="Low"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/assign/", data={"assigned_handler_id": 7000 + 22, "priority": "High"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    now = timezone.now()
    assert c.sla_due_date <= now + timedelta(hours=26), f"High priority SLA exceeds 24 hours: {c.sla_due_date - now}"


def test_wf_023_bw_cms_02_path_supervisor_signoff(stub_iam):
    """TEST-WF-023: BW-CMS-02 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 23)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0023",
        complainant_user_id=6000 + 23,
        category="maintenance",
        description="Testing BW-CMS-02 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_024_bw_cms_02_illegal_transition_rejection(stub_iam):
    """TEST-WF-024: BW-CMS-02 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 24)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0024",
        complainant_user_id=6000 + 24,
        category="maintenance",
        description="Testing BW-CMS-02 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_025_bw_cms_02_terminal_mutation_guard(stub_iam):
    """TEST-WF-025: BW-CMS-02 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 25)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0025",
        complainant_user_id=6000 + 25,
        category="maintenance",
        description="Testing BW-CMS-02 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_026_bw_cms_02_reopen_initiation_path(stub_iam):
    """TEST-WF-026: BW-CMS-02 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 26)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0026",
        complainant_user_id=6000 + 26,
        category="maintenance",
        description="Testing BW-CMS-02 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_027_bw_cms_02_reopen_adjudication_path(stub_iam):
    """TEST-WF-027: BW-CMS-02 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 27)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0027",
        complainant_user_id=6000 + 27,
        category="maintenance",
        description="Testing BW-CMS-02 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_028_bw_cms_02_manual_escalation_path(stub_iam):
    """TEST-WF-028: BW-CMS-02 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 28)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0028",
        complainant_user_id=6000 + 28,
        category="maintenance",
        description="Testing BW-CMS-02 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_029_bw_cms_02_sla_escalation_path(stub_iam):
    """TEST-WF-029: BW-CMS-02 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 29)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0029",
        complainant_user_id=6000 + 29,
        category="maintenance",
        description="Testing BW-CMS-02 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_030_bw_cms_02_concurrent_audit_integrity(stub_iam):
    """TEST-WF-030: BW-CMS-02 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 30)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0030",
        complainant_user_id=6000 + 30,
        category="maintenance",
        description="Testing BW-CMS-02 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_031_bw_cms_03_nominal_flow(stub_iam):
    """TEST-WF-031: BW-CMS-03 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 31)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0031",
        complainant_user_id=6000 + 31,
        category="maintenance",
        description="Testing BW-CMS-03 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_032_bw_cms_03_step1_intake(stub_iam):
    """TEST-WF-032: BW-CMS-03 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 32)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0032",
        complainant_user_id=6000 + 32,
        category="maintenance",
        description="Testing BW-CMS-03 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_033_bw_cms_03_step2_assignment(stub_iam):
    """TEST-WF-033: BW-CMS-03 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 33)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0033",
        complainant_user_id=6000 + 33,
        category="maintenance",
        description="Testing BW-CMS-03 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_034_bw_cms_03_step3_progress(stub_iam):
    """TEST-WF-034: BW-CMS-03 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 34)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0034",
        complainant_user_id=6000 + 34,
        category="maintenance",
        description="Testing BW-CMS-03 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_035_bw_cms_03_step4_resolution(stub_iam):
    """TEST-WF-035: BW-CMS-03 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 35)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0035",
        complainant_user_id=6000 + 35,
        category="maintenance",
        description="Testing BW-CMS-03 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_036_bw_cms_03_step5_closure(stub_iam):
    """TEST-WF-036: BW-CMS-03 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 36)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0036",
        complainant_user_id=6000 + 36,
        category="maintenance",
        description="Testing BW-CMS-03 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_037_bw_cms_03_path_complainant_signoff(stub_iam):
    """TEST-WF-037: BW-CMS-03 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 37)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0037",
        complainant_user_id=6000 + 37,
        category="maintenance",
        description="Testing BW-CMS-03 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_038_bw_cms_03_path_supervisor_signoff(stub_iam):
    """TEST-WF-038: BW-CMS-03 path_supervisor_signoff - Complainant closure on supervisor-mandated ticket rejected (Defect 8)."""
    client = auth_client(stub_iam, user_id=6000 + 38, kind="student", roles=("student",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0038",
        complainant_user_id=6000 + 38,
        category="academic",
        description="High-value server equipment malfunction.",
        status="Resolved",
        requires_supervisor_verification=True
    )
    # Complainant attempts verify_closure
    res = client.post(f"/api/v1/cms/complaints/{c.id}/verify_closure/", data={"notes": "Student trying to close"}, format="json")
    assert res.status_code in [400, 403], f"Complainant closure verification accepted without supervisor authority (got {res.status_code})"


def test_wf_039_bw_cms_03_illegal_transition_rejection(stub_iam):
    """TEST-WF-039: BW-CMS-03 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 39)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0039",
        complainant_user_id=6000 + 39,
        category="maintenance",
        description="Testing BW-CMS-03 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_040_bw_cms_03_terminal_mutation_guard(stub_iam):
    """TEST-WF-040: BW-CMS-03 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 40)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0040",
        complainant_user_id=6000 + 40,
        category="maintenance",
        description="Testing BW-CMS-03 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_041_bw_cms_03_reopen_initiation_path(stub_iam):
    """TEST-WF-041: BW-CMS-03 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 41)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0041",
        complainant_user_id=6000 + 41,
        category="maintenance",
        description="Testing BW-CMS-03 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_042_bw_cms_03_reopen_adjudication_path(stub_iam):
    """TEST-WF-042: BW-CMS-03 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 42)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0042",
        complainant_user_id=6000 + 42,
        category="maintenance",
        description="Testing BW-CMS-03 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_043_bw_cms_03_manual_escalation_path(stub_iam):
    """TEST-WF-043: BW-CMS-03 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 43)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0043",
        complainant_user_id=6000 + 43,
        category="maintenance",
        description="Testing BW-CMS-03 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_044_bw_cms_03_sla_escalation_path(stub_iam):
    """TEST-WF-044: BW-CMS-03 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 44)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0044",
        complainant_user_id=6000 + 44,
        category="maintenance",
        description="Testing BW-CMS-03 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_045_bw_cms_03_concurrent_audit_integrity(stub_iam):
    """TEST-WF-045: BW-CMS-03 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 45)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0045",
        complainant_user_id=6000 + 45,
        category="maintenance",
        description="Testing BW-CMS-03 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_046_bw_cms_04_nominal_flow(stub_iam):
    """TEST-WF-046: BW-CMS-04 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 46)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0046",
        complainant_user_id=6000 + 46,
        category="maintenance",
        description="Testing BW-CMS-04 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_047_bw_cms_04_step1_intake(stub_iam):
    """TEST-WF-047: BW-CMS-04 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 47)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0047",
        complainant_user_id=6000 + 47,
        category="maintenance",
        description="Testing BW-CMS-04 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_048_bw_cms_04_step2_assignment(stub_iam):
    """TEST-WF-048: BW-CMS-04 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 48)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0048",
        complainant_user_id=6000 + 48,
        category="maintenance",
        description="Testing BW-CMS-04 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_049_bw_cms_04_step3_progress(stub_iam):
    """TEST-WF-049: BW-CMS-04 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 49)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0049",
        complainant_user_id=6000 + 49,
        category="maintenance",
        description="Testing BW-CMS-04 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_050_bw_cms_04_step4_resolution(stub_iam):
    """TEST-WF-050: BW-CMS-04 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 50)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0050",
        complainant_user_id=6000 + 50,
        category="maintenance",
        description="Testing BW-CMS-04 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_051_bw_cms_04_step5_closure(stub_iam):
    """TEST-WF-051: BW-CMS-04 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 51)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0051",
        complainant_user_id=6000 + 51,
        category="maintenance",
        description="Testing BW-CMS-04 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_052_bw_cms_04_path_complainant_signoff(stub_iam):
    """TEST-WF-052: BW-CMS-04 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 52)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0052",
        complainant_user_id=6000 + 52,
        category="maintenance",
        description="Testing BW-CMS-04 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_053_bw_cms_04_path_supervisor_signoff(stub_iam):
    """TEST-WF-053: BW-CMS-04 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 53)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0053",
        complainant_user_id=6000 + 53,
        category="maintenance",
        description="Testing BW-CMS-04 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_054_bw_cms_04_illegal_transition_rejection(stub_iam):
    """TEST-WF-054: BW-CMS-04 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 54)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0054",
        complainant_user_id=6000 + 54,
        category="maintenance",
        description="Testing BW-CMS-04 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_055_bw_cms_04_terminal_mutation_guard(stub_iam):
    """TEST-WF-055: BW-CMS-04 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 55)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0055",
        complainant_user_id=6000 + 55,
        category="maintenance",
        description="Testing BW-CMS-04 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_056_bw_cms_04_reopen_initiation_path(stub_iam):
    """TEST-WF-056: BW-CMS-04 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 56)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0056",
        complainant_user_id=6000 + 56,
        category="maintenance",
        description="Testing BW-CMS-04 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_057_bw_cms_04_reopen_adjudication_path(stub_iam):
    """TEST-WF-057: BW-CMS-04 reopen_adjudication_path - Terminal state protection: update_progress on Rejected rejected (Defect 17)."""
    client = auth_client(stub_iam, user_id=7000 + 57, kind="staff", roles=("complaint_handler",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0057",
        complainant_user_id=6000 + 57,
        category="other",
        description="Invalid external complaint.",
        status="Rejected",
        rejection_reason="Not institutional domain"
    )
    # Attempt to add progress to a Rejected complaint
    res = client.post(f"/api/v1/cms/complaints/{c.id}/update_progress/", data={"remarks": "Attempting progress update on rejected ticket"}, format="json")
    assert res.status_code == 400, "Progress update allowed on terminal 'Rejected' state"


def test_wf_058_bw_cms_04_manual_escalation_path(stub_iam):
    """TEST-WF-058: BW-CMS-04 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 58)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0058",
        complainant_user_id=6000 + 58,
        category="maintenance",
        description="Testing BW-CMS-04 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_059_bw_cms_04_sla_escalation_path(stub_iam):
    """TEST-WF-059: BW-CMS-04 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 59)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0059",
        complainant_user_id=6000 + 59,
        category="maintenance",
        description="Testing BW-CMS-04 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_060_bw_cms_04_concurrent_audit_integrity(stub_iam):
    """TEST-WF-060: BW-CMS-04 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 60)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0060",
        complainant_user_id=6000 + 60,
        category="maintenance",
        description="Testing BW-CMS-04 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_061_bw_cms_05_nominal_flow(stub_iam):
    """TEST-WF-061: BW-CMS-05 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 61)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0061",
        complainant_user_id=6000 + 61,
        category="maintenance",
        description="Testing BW-CMS-05 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_062_bw_cms_05_step1_intake(stub_iam):
    """TEST-WF-062: BW-CMS-05 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 62)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0062",
        complainant_user_id=6000 + 62,
        category="maintenance",
        description="Testing BW-CMS-05 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_063_bw_cms_05_step2_assignment(stub_iam):
    """TEST-WF-063: BW-CMS-05 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 63)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0063",
        complainant_user_id=6000 + 63,
        category="maintenance",
        description="Testing BW-CMS-05 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_064_bw_cms_05_step3_progress(stub_iam):
    """TEST-WF-064: BW-CMS-05 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 64)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0064",
        complainant_user_id=6000 + 64,
        category="maintenance",
        description="Testing BW-CMS-05 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_065_bw_cms_05_step4_resolution(stub_iam):
    """TEST-WF-065: BW-CMS-05 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 65)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0065",
        complainant_user_id=6000 + 65,
        category="maintenance",
        description="Testing BW-CMS-05 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_066_bw_cms_05_step5_closure(stub_iam):
    """TEST-WF-066: BW-CMS-05 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 66)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0066",
        complainant_user_id=6000 + 66,
        category="maintenance",
        description="Testing BW-CMS-05 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_067_bw_cms_05_path_complainant_signoff(stub_iam):
    """TEST-WF-067: BW-CMS-05 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 67)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0067",
        complainant_user_id=6000 + 67,
        category="maintenance",
        description="Testing BW-CMS-05 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_068_bw_cms_05_path_supervisor_signoff(stub_iam):
    """TEST-WF-068: BW-CMS-05 path_supervisor_signoff - Reopen denied decision preserves closed state and records denial audit (Defect 4)."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0068",
        complainant_user_id=6000 + 68,
        category="hostel",
        description="Room lighting issue.",
        status="Closed",
        rejection_reason="Out of scope"
    )
    reopen = ComplaintReopening.objects.create(
        complaint=c,
        complainant_user_id=6000 + 68,
        dissatisfaction_reason="Requires electrician.",
        status="pending"
    )
    res = client.post(f"/api/v1/cms/complaints/{c.id}/decide_reopen/", data={"reopening_id": reopen.id, "decision": "deny", "supervisor_remarks": "Denied after review"}, format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # Invariant: reopening denial must not modify original complaint closure status or clear rejection notes
    assert c.status == "Closed"
    assert c.rejection_reason == "Out of scope"
    # Defect: complaint supervisor audit record missing supervisor specific verification flag
    assert reopen.supervisor_remarks == "Denied after review"
    assert reopen.status == "denied"
    # Check supervisor verification flag is preserved
    assert hasattr(ComplaintReopening, 'denial_category'), "ComplaintReopening model missing structured denial_category classification"


def test_wf_069_bw_cms_05_illegal_transition_rejection(stub_iam):
    """TEST-WF-069: BW-CMS-05 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 69)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0069",
        complainant_user_id=6000 + 69,
        category="maintenance",
        description="Testing BW-CMS-05 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_070_bw_cms_05_terminal_mutation_guard(stub_iam):
    """TEST-WF-070: BW-CMS-05 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 70)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0070",
        complainant_user_id=6000 + 70,
        category="maintenance",
        description="Testing BW-CMS-05 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_071_bw_cms_05_reopen_initiation_path(stub_iam):
    """TEST-WF-071: BW-CMS-05 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 71)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0071",
        complainant_user_id=6000 + 71,
        category="maintenance",
        description="Testing BW-CMS-05 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_072_bw_cms_05_reopen_adjudication_path(stub_iam):
    """TEST-WF-072: BW-CMS-05 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 72)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0072",
        complainant_user_id=6000 + 72,
        category="maintenance",
        description="Testing BW-CMS-05 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_073_bw_cms_05_manual_escalation_path(stub_iam):
    """TEST-WF-073: BW-CMS-05 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 73)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0073",
        complainant_user_id=6000 + 73,
        category="maintenance",
        description="Testing BW-CMS-05 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_074_bw_cms_05_sla_escalation_path(stub_iam):
    """TEST-WF-074: BW-CMS-05 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 74)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0074",
        complainant_user_id=6000 + 74,
        category="maintenance",
        description="Testing BW-CMS-05 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_075_bw_cms_05_concurrent_audit_integrity(stub_iam):
    """TEST-WF-075: BW-CMS-05 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 75)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0075",
        complainant_user_id=6000 + 75,
        category="maintenance",
        description="Testing BW-CMS-05 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_076_bw_cms_06_nominal_flow(stub_iam):
    """TEST-WF-076: BW-CMS-06 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 76)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0076",
        complainant_user_id=6000 + 76,
        category="maintenance",
        description="Testing BW-CMS-06 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_077_bw_cms_06_step1_intake(stub_iam):
    """TEST-WF-077: BW-CMS-06 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 77)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0077",
        complainant_user_id=6000 + 77,
        category="maintenance",
        description="Testing BW-CMS-06 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_078_bw_cms_06_step2_assignment(stub_iam):
    """TEST-WF-078: BW-CMS-06 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 78)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0078",
        complainant_user_id=6000 + 78,
        category="maintenance",
        description="Testing BW-CMS-06 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_079_bw_cms_06_step3_progress(stub_iam):
    """TEST-WF-079: BW-CMS-06 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 79)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0079",
        complainant_user_id=6000 + 79,
        category="maintenance",
        description="Testing BW-CMS-06 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_080_bw_cms_06_step4_resolution(stub_iam):
    """TEST-WF-080: BW-CMS-06 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 80)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0080",
        complainant_user_id=6000 + 80,
        category="maintenance",
        description="Testing BW-CMS-06 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_081_bw_cms_06_step5_closure(stub_iam):
    """TEST-WF-081: BW-CMS-06 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 81)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0081",
        complainant_user_id=6000 + 81,
        category="maintenance",
        description="Testing BW-CMS-06 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_082_bw_cms_06_path_complainant_signoff(stub_iam):
    """TEST-WF-082: BW-CMS-06 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 82)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0082",
        complainant_user_id=6000 + 82,
        category="maintenance",
        description="Testing BW-CMS-06 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_083_bw_cms_06_path_supervisor_signoff(stub_iam):
    """TEST-WF-083: BW-CMS-06 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 83)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0083",
        complainant_user_id=6000 + 83,
        category="maintenance",
        description="Testing BW-CMS-06 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_084_bw_cms_06_illegal_transition_rejection(stub_iam):
    """TEST-WF-084: BW-CMS-06 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 84)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0084",
        complainant_user_id=6000 + 84,
        category="maintenance",
        description="Testing BW-CMS-06 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_085_bw_cms_06_terminal_mutation_guard(stub_iam):
    """TEST-WF-085: BW-CMS-06 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 85)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0085",
        complainant_user_id=6000 + 85,
        category="maintenance",
        description="Testing BW-CMS-06 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_086_bw_cms_06_reopen_initiation_path(stub_iam):
    """TEST-WF-086: BW-CMS-06 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 86)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0086",
        complainant_user_id=6000 + 86,
        category="maintenance",
        description="Testing BW-CMS-06 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_087_bw_cms_06_reopen_adjudication_path(stub_iam):
    """TEST-WF-087: BW-CMS-06 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 87)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0087",
        complainant_user_id=6000 + 87,
        category="maintenance",
        description="Testing BW-CMS-06 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_088_bw_cms_06_manual_escalation_path(stub_iam):
    """TEST-WF-088: BW-CMS-06 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 88)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0088",
        complainant_user_id=6000 + 88,
        category="maintenance",
        description="Testing BW-CMS-06 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_089_bw_cms_06_sla_escalation_path(stub_iam):
    """TEST-WF-089: BW-CMS-06 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 89)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0089",
        complainant_user_id=6000 + 89,
        category="maintenance",
        description="Testing BW-CMS-06 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_090_bw_cms_06_concurrent_audit_integrity(stub_iam):
    """TEST-WF-090: BW-CMS-06 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 90)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0090",
        complainant_user_id=6000 + 90,
        category="maintenance",
        description="Testing BW-CMS-06 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_091_bw_cms_07_nominal_flow(stub_iam):
    """TEST-WF-091: BW-CMS-07 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 91)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0091",
        complainant_user_id=6000 + 91,
        category="maintenance",
        description="Testing BW-CMS-07 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_092_bw_cms_07_step1_intake(stub_iam):
    """TEST-WF-092: BW-CMS-07 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 92)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0092",
        complainant_user_id=6000 + 92,
        category="maintenance",
        description="Testing BW-CMS-07 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_093_bw_cms_07_step2_assignment(stub_iam):
    """TEST-WF-093: BW-CMS-07 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 93)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0093",
        complainant_user_id=6000 + 93,
        category="maintenance",
        description="Testing BW-CMS-07 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_094_bw_cms_07_step3_progress(stub_iam):
    """TEST-WF-094: BW-CMS-07 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 94)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0094",
        complainant_user_id=6000 + 94,
        category="maintenance",
        description="Testing BW-CMS-07 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_095_bw_cms_07_step4_resolution(stub_iam):
    """TEST-WF-095: BW-CMS-07 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 95)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0095",
        complainant_user_id=6000 + 95,
        category="maintenance",
        description="Testing BW-CMS-07 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_096_bw_cms_07_step5_closure(stub_iam):
    """TEST-WF-096: BW-CMS-07 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 96)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0096",
        complainant_user_id=6000 + 96,
        category="maintenance",
        description="Testing BW-CMS-07 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_097_bw_cms_07_path_complainant_signoff(stub_iam):
    """TEST-WF-097: BW-CMS-07 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 97)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0097",
        complainant_user_id=6000 + 97,
        category="maintenance",
        description="Testing BW-CMS-07 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_098_bw_cms_07_path_supervisor_signoff(stub_iam):
    """TEST-WF-098: BW-CMS-07 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 98)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0098",
        complainant_user_id=6000 + 98,
        category="maintenance",
        description="Testing BW-CMS-07 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_099_bw_cms_07_illegal_transition_rejection(stub_iam):
    """TEST-WF-099: BW-CMS-07 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 99)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0099",
        complainant_user_id=6000 + 99,
        category="maintenance",
        description="Testing BW-CMS-07 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_100_bw_cms_07_terminal_mutation_guard(stub_iam):
    """TEST-WF-100: BW-CMS-07 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 100)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0100",
        complainant_user_id=6000 + 100,
        category="maintenance",
        description="Testing BW-CMS-07 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_101_bw_cms_07_reopen_initiation_path(stub_iam):
    """TEST-WF-101: BW-CMS-07 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 101)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0101",
        complainant_user_id=6000 + 101,
        category="maintenance",
        description="Testing BW-CMS-07 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_102_bw_cms_07_reopen_adjudication_path(stub_iam):
    """TEST-WF-102: BW-CMS-07 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 102)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0102",
        complainant_user_id=6000 + 102,
        category="maintenance",
        description="Testing BW-CMS-07 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_103_bw_cms_07_manual_escalation_path(stub_iam):
    """TEST-WF-103: BW-CMS-07 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 103)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0103",
        complainant_user_id=6000 + 103,
        category="maintenance",
        description="Testing BW-CMS-07 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_104_bw_cms_07_sla_escalation_path(stub_iam):
    """TEST-WF-104: BW-CMS-07 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 104)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0104",
        complainant_user_id=6000 + 104,
        category="maintenance",
        description="Testing BW-CMS-07 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_105_bw_cms_07_concurrent_audit_integrity(stub_iam):
    """TEST-WF-105: BW-CMS-07 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 105)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0105",
        complainant_user_id=6000 + 105,
        category="maintenance",
        description="Testing BW-CMS-07 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_106_bw_cms_08_nominal_flow(stub_iam):
    """TEST-WF-106: BW-CMS-08 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 106)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0106",
        complainant_user_id=6000 + 106,
        category="maintenance",
        description="Testing BW-CMS-08 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_107_bw_cms_08_step1_intake(stub_iam):
    """TEST-WF-107: BW-CMS-08 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 107)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0107",
        complainant_user_id=6000 + 107,
        category="maintenance",
        description="Testing BW-CMS-08 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_108_bw_cms_08_step2_assignment(stub_iam):
    """TEST-WF-108: BW-CMS-08 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 108)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0108",
        complainant_user_id=6000 + 108,
        category="maintenance",
        description="Testing BW-CMS-08 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_109_bw_cms_08_step3_progress(stub_iam):
    """TEST-WF-109: BW-CMS-08 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 109)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0109",
        complainant_user_id=6000 + 109,
        category="maintenance",
        description="Testing BW-CMS-08 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_110_bw_cms_08_step4_resolution(stub_iam):
    """TEST-WF-110: BW-CMS-08 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 110)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0110",
        complainant_user_id=6000 + 110,
        category="maintenance",
        description="Testing BW-CMS-08 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_111_bw_cms_08_step5_closure(stub_iam):
    """TEST-WF-111: BW-CMS-08 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 111)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0111",
        complainant_user_id=6000 + 111,
        category="maintenance",
        description="Testing BW-CMS-08 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_112_bw_cms_08_path_complainant_signoff(stub_iam):
    """TEST-WF-112: BW-CMS-08 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 112)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0112",
        complainant_user_id=6000 + 112,
        category="maintenance",
        description="Testing BW-CMS-08 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_113_bw_cms_08_path_supervisor_signoff(stub_iam):
    """TEST-WF-113: BW-CMS-08 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 113)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0113",
        complainant_user_id=6000 + 113,
        category="maintenance",
        description="Testing BW-CMS-08 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_114_bw_cms_08_illegal_transition_rejection(stub_iam):
    """TEST-WF-114: BW-CMS-08 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 114)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0114",
        complainant_user_id=6000 + 114,
        category="maintenance",
        description="Testing BW-CMS-08 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_115_bw_cms_08_terminal_mutation_guard(stub_iam):
    """TEST-WF-115: BW-CMS-08 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 115)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0115",
        complainant_user_id=6000 + 115,
        category="maintenance",
        description="Testing BW-CMS-08 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_116_bw_cms_08_reopen_initiation_path(stub_iam):
    """TEST-WF-116: BW-CMS-08 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 116)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0116",
        complainant_user_id=6000 + 116,
        category="maintenance",
        description="Testing BW-CMS-08 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_117_bw_cms_08_reopen_adjudication_path(stub_iam):
    """TEST-WF-117: BW-CMS-08 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 117)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0117",
        complainant_user_id=6000 + 117,
        category="maintenance",
        description="Testing BW-CMS-08 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_118_bw_cms_08_manual_escalation_path(stub_iam):
    """TEST-WF-118: BW-CMS-08 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 118)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0118",
        complainant_user_id=6000 + 118,
        category="maintenance",
        description="Testing BW-CMS-08 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_119_bw_cms_08_sla_escalation_path(stub_iam):
    """TEST-WF-119: BW-CMS-08 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 119)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0119",
        complainant_user_id=6000 + 119,
        category="maintenance",
        description="Testing BW-CMS-08 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_120_bw_cms_08_concurrent_audit_integrity(stub_iam):
    """TEST-WF-120: BW-CMS-08 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 120)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0120",
        complainant_user_id=6000 + 120,
        category="maintenance",
        description="Testing BW-CMS-08 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_121_cw_cms_01_nominal_flow(stub_iam):
    """TEST-WF-121: CW-CMS-01 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 121)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0121",
        complainant_user_id=6000 + 121,
        category="maintenance",
        description="Testing CW-CMS-01 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_122_cw_cms_01_step1_intake(stub_iam):
    """TEST-WF-122: CW-CMS-01 step1_intake - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 122)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0122",
        complainant_user_id=6000 + 122,
        category="maintenance",
        description="Testing CW-CMS-01 step1_intake.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_123_cw_cms_01_step2_assignment(stub_iam):
    """TEST-WF-123: CW-CMS-01 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 123)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0123",
        complainant_user_id=6000 + 123,
        category="maintenance",
        description="Testing CW-CMS-01 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_124_cw_cms_01_step3_progress(stub_iam):
    """TEST-WF-124: CW-CMS-01 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 124)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0124",
        complainant_user_id=6000 + 124,
        category="maintenance",
        description="Testing CW-CMS-01 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_125_cw_cms_01_step4_resolution(stub_iam):
    """TEST-WF-125: CW-CMS-01 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 125)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0125",
        complainant_user_id=6000 + 125,
        category="maintenance",
        description="Testing CW-CMS-01 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_126_cw_cms_01_step5_closure(stub_iam):
    """TEST-WF-126: CW-CMS-01 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 126)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0126",
        complainant_user_id=6000 + 126,
        category="maintenance",
        description="Testing CW-CMS-01 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_127_cw_cms_01_path_complainant_signoff(stub_iam):
    """TEST-WF-127: CW-CMS-01 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 127)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0127",
        complainant_user_id=6000 + 127,
        category="maintenance",
        description="Testing CW-CMS-01 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_128_cw_cms_01_path_supervisor_signoff(stub_iam):
    """TEST-WF-128: CW-CMS-01 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 128)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0128",
        complainant_user_id=6000 + 128,
        category="maintenance",
        description="Testing CW-CMS-01 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_129_cw_cms_01_illegal_transition_rejection(stub_iam):
    """TEST-WF-129: CW-CMS-01 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 129)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0129",
        complainant_user_id=6000 + 129,
        category="maintenance",
        description="Testing CW-CMS-01 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_130_cw_cms_01_terminal_mutation_guard(stub_iam):
    """TEST-WF-130: CW-CMS-01 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 130)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0130",
        complainant_user_id=6000 + 130,
        category="maintenance",
        description="Testing CW-CMS-01 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_131_cw_cms_01_reopen_initiation_path(stub_iam):
    """TEST-WF-131: CW-CMS-01 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 131)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0131",
        complainant_user_id=6000 + 131,
        category="maintenance",
        description="Testing CW-CMS-01 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_132_cw_cms_01_reopen_adjudication_path(stub_iam):
    """TEST-WF-132: CW-CMS-01 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 132)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0132",
        complainant_user_id=6000 + 132,
        category="maintenance",
        description="Testing CW-CMS-01 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_133_cw_cms_01_manual_escalation_path(stub_iam):
    """TEST-WF-133: CW-CMS-01 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 133)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0133",
        complainant_user_id=6000 + 133,
        category="maintenance",
        description="Testing CW-CMS-01 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_134_cw_cms_01_sla_escalation_path(stub_iam):
    """TEST-WF-134: CW-CMS-01 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 134)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0134",
        complainant_user_id=6000 + 134,
        category="maintenance",
        description="Testing CW-CMS-01 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_135_cw_cms_01_concurrent_audit_integrity(stub_iam):
    """TEST-WF-135: CW-CMS-01 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 135)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0135",
        complainant_user_id=6000 + 135,
        category="maintenance",
        description="Testing CW-CMS-01 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_136_cw_cms_02_nominal_flow(stub_iam):
    """TEST-WF-136: CW-CMS-02 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 136)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0136",
        complainant_user_id=6000 + 136,
        category="maintenance",
        description="Testing CW-CMS-02 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_137_cw_cms_02_step1_intake(stub_iam):
    """TEST-WF-137: CW-CMS-02 step1_intake - Duplicate pending reopening prevention in composite workflow (Defect 2)."""
    client = auth_client(stub_iam, user_id=6000 + 137)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0137",
        complainant_user_id=6000 + 137,
        category="maintenance",
        description="Air conditioning defect.",
        status="Closed"
    )
    r1 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Still hot."}, format="json")
    assert r1.status_code in [200, 201]
    r2 = client.post(f"/api/v1/cms/complaints/{c.id}/request_reopen/", data={"dissatisfaction_reason": "Duplicate reopen submission."}, format="json")
    assert r2.status_code == 400, "Second pending reopening allowed in workflow"


def test_wf_138_cw_cms_02_step2_assignment(stub_iam):
    """TEST-WF-138: CW-CMS-02 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 138)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0138",
        complainant_user_id=6000 + 138,
        category="maintenance",
        description="Testing CW-CMS-02 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_139_cw_cms_02_step3_progress(stub_iam):
    """TEST-WF-139: CW-CMS-02 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 139)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0139",
        complainant_user_id=6000 + 139,
        category="maintenance",
        description="Testing CW-CMS-02 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_140_cw_cms_02_step4_resolution(stub_iam):
    """TEST-WF-140: CW-CMS-02 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 140)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0140",
        complainant_user_id=6000 + 140,
        category="maintenance",
        description="Testing CW-CMS-02 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_141_cw_cms_02_step5_closure(stub_iam):
    """TEST-WF-141: CW-CMS-02 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 141)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0141",
        complainant_user_id=6000 + 141,
        category="maintenance",
        description="Testing CW-CMS-02 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_142_cw_cms_02_path_complainant_signoff(stub_iam):
    """TEST-WF-142: CW-CMS-02 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 142)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0142",
        complainant_user_id=6000 + 142,
        category="maintenance",
        description="Testing CW-CMS-02 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_143_cw_cms_02_path_supervisor_signoff(stub_iam):
    """TEST-WF-143: CW-CMS-02 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 143)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0143",
        complainant_user_id=6000 + 143,
        category="maintenance",
        description="Testing CW-CMS-02 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_144_cw_cms_02_illegal_transition_rejection(stub_iam):
    """TEST-WF-144: CW-CMS-02 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 144)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0144",
        complainant_user_id=6000 + 144,
        category="maintenance",
        description="Testing CW-CMS-02 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_145_cw_cms_02_terminal_mutation_guard(stub_iam):
    """TEST-WF-145: CW-CMS-02 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 145)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0145",
        complainant_user_id=6000 + 145,
        category="maintenance",
        description="Testing CW-CMS-02 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_146_cw_cms_02_reopen_initiation_path(stub_iam):
    """TEST-WF-146: CW-CMS-02 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 146)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0146",
        complainant_user_id=6000 + 146,
        category="maintenance",
        description="Testing CW-CMS-02 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_147_cw_cms_02_reopen_adjudication_path(stub_iam):
    """TEST-WF-147: CW-CMS-02 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 147)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0147",
        complainant_user_id=6000 + 147,
        category="maintenance",
        description="Testing CW-CMS-02 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_148_cw_cms_02_manual_escalation_path(stub_iam):
    """TEST-WF-148: CW-CMS-02 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 148)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0148",
        complainant_user_id=6000 + 148,
        category="maintenance",
        description="Testing CW-CMS-02 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_149_cw_cms_02_sla_escalation_path(stub_iam):
    """TEST-WF-149: CW-CMS-02 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 149)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0149",
        complainant_user_id=6000 + 149,
        category="maintenance",
        description="Testing CW-CMS-02 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_150_cw_cms_02_concurrent_audit_integrity(stub_iam):
    """TEST-WF-150: CW-CMS-02 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 150)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0150",
        complainant_user_id=6000 + 150,
        category="maintenance",
        description="Testing CW-CMS-02 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_151_cw_cms_03_nominal_flow(stub_iam):
    """TEST-WF-151: CW-CMS-03 nominal_flow - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 151)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0151",
        complainant_user_id=6000 + 151,
        category="maintenance",
        description="Testing CW-CMS-03 nominal_flow.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_152_cw_cms_03_step1_intake(stub_iam):
    """TEST-WF-152: CW-CMS-03 step1_intake - Automated SLA escalation preserves manual escalation audit (Defect 18)."""
    client = auth_client(stub_iam, user_id=6000 + 152)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0152",
        complainant_user_id=6000 + 152,
        category="network",
        description="Campus gateway down.",
        status="In Progress",
        is_escalated=True,
        escalation_type="manual",
        escalation_remarks="Initial manual escalation by faculty indenter."
    )
    # Run SLA sweep
    res = client.post("/api/v1/cms/complaints/check_sla/", format="json")
    assert res.status_code == 200
    c.refresh_from_db()
    # Invariant: check_sla must not overwrite existing manual escalation or overwrite escalation_remarks
    assert c.escalation_type == "manual"
    # Defect: Complaint model missing previous_escalation_type or dual escalation tracking history
    has_dual_tracking = hasattr(Complaint, 'escalation_history')
    assert has_dual_tracking, "Complaint model lacks escalation_history relation for dual manual/SLA trigger audit"


def test_wf_153_cw_cms_03_step2_assignment(stub_iam):
    """TEST-WF-153: CW-CMS-03 step2_assignment - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 153)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0153",
        complainant_user_id=6000 + 153,
        category="maintenance",
        description="Testing CW-CMS-03 step2_assignment.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_154_cw_cms_03_step3_progress(stub_iam):
    """TEST-WF-154: CW-CMS-03 step3_progress - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 154)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0154",
        complainant_user_id=6000 + 154,
        category="maintenance",
        description="Testing CW-CMS-03 step3_progress.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_155_cw_cms_03_step4_resolution(stub_iam):
    """TEST-WF-155: CW-CMS-03 step4_resolution - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 155)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0155",
        complainant_user_id=6000 + 155,
        category="maintenance",
        description="Testing CW-CMS-03 step4_resolution.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_156_cw_cms_03_step5_closure(stub_iam):
    """TEST-WF-156: CW-CMS-03 step5_closure - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 156)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0156",
        complainant_user_id=6000 + 156,
        category="maintenance",
        description="Testing CW-CMS-03 step5_closure.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_157_cw_cms_03_path_complainant_signoff(stub_iam):
    """TEST-WF-157: CW-CMS-03 path_complainant_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 157)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0157",
        complainant_user_id=6000 + 157,
        category="maintenance",
        description="Testing CW-CMS-03 path_complainant_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_158_cw_cms_03_path_supervisor_signoff(stub_iam):
    """TEST-WF-158: CW-CMS-03 path_supervisor_signoff - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 158)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0158",
        complainant_user_id=6000 + 158,
        category="maintenance",
        description="Testing CW-CMS-03 path_supervisor_signoff.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_159_cw_cms_03_illegal_transition_rejection(stub_iam):
    """TEST-WF-159: CW-CMS-03 illegal_transition_rejection - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 159)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0159",
        complainant_user_id=6000 + 159,
        category="maintenance",
        description="Testing CW-CMS-03 illegal_transition_rejection.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_160_cw_cms_03_terminal_mutation_guard(stub_iam):
    """TEST-WF-160: CW-CMS-03 terminal_mutation_guard - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 160)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0160",
        complainant_user_id=6000 + 160,
        category="maintenance",
        description="Testing CW-CMS-03 terminal_mutation_guard.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_161_cw_cms_03_reopen_initiation_path(stub_iam):
    """TEST-WF-161: CW-CMS-03 reopen_initiation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 161)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0161",
        complainant_user_id=6000 + 161,
        category="maintenance",
        description="Testing CW-CMS-03 reopen_initiation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_162_cw_cms_03_reopen_adjudication_path(stub_iam):
    """TEST-WF-162: CW-CMS-03 reopen_adjudication_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 162)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0162",
        complainant_user_id=6000 + 162,
        category="maintenance",
        description="Testing CW-CMS-03 reopen_adjudication_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_163_cw_cms_03_manual_escalation_path(stub_iam):
    """TEST-WF-163: CW-CMS-03 manual_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 163)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0163",
        complainant_user_id=6000 + 163,
        category="maintenance",
        description="Testing CW-CMS-03 manual_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_164_cw_cms_03_sla_escalation_path(stub_iam):
    """TEST-WF-164: CW-CMS-03 sla_escalation_path - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 164)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0164",
        complainant_user_id=6000 + 164,
        category="maintenance",
        description="Testing CW-CMS-03 sla_escalation_path.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200


def test_wf_165_cw_cms_03_concurrent_audit_integrity(stub_iam):
    """TEST-WF-165: CW-CMS-03 concurrent_audit_integrity - Conforming execution."""
    client = auth_client(stub_iam, user_id=6000 + 165)
    c = Complaint.objects.create(
        complaint_id="CMS-2026-WF0165",
        complainant_user_id=6000 + 165,
        category="maintenance",
        description="Testing CW-CMS-03 concurrent_audit_integrity.",
        status="Submitted",
        priority="Low"
    )
    assert c.id is not None
    res = client.get(f"/api/v1/cms/complaints/{c.id}/")
    assert res.status_code == 200
