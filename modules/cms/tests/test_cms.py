import pytest
from datetime import timedelta
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


def test_submit_complaint_mandatory_validation(stub_iam):
    """CFR-CMS-001 & CFR-CMS-002: Submission with mandatory validation and unique ID generation."""
    client = auth_client(stub_iam, user_id=1001)

    # Successful submission
    payload = {
        "category": "hostel",
        "description": "Ceiling fan not working in Room 102.",
        "priority": "Medium",
    }
    response = client.post("/api/v1/cms/complaints/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["complaint_id"].startswith("CMS-2026-")
    assert data["category"] == "hostel"
    assert data["status"] == "Submitted"
    assert data["complainant_user_id"] == 1001

    # Missing mandatory description
    bad_payload_1 = {"category": "hostel"}
    res_bad_1 = client.post("/api/v1/cms/complaints/", data=bad_payload_1, format="json")
    assert res_bad_1.status_code == 400

    # Missing mandatory category
    bad_payload_2 = {"description": "Water cooler leaking"}
    res_bad_2 = client.post("/api/v1/cms/complaints/", data=bad_payload_2, format="json")
    assert res_bad_2.status_code == 400


def test_handler_assignment_and_sla_calculation(stub_iam):
    """BW-CMS-02 & BR-CMS-004: Assignment to handler calculates SLA due date based on priority."""
    client = auth_client(stub_iam, user_id=5001, kind="staff", roles=("complaint_handler",))

    complaint = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="network",
        description="Wi-Fi connectivity drops repeatedly.",
        status="Submitted",
        priority="Low",
    )

    assign_payload = {
        "handler_id": 5001,
        "priority": "High",
    }
    response = client.post(f"/api/v1/cms/complaints/{complaint.id}/assign/", data=assign_payload, format="json")
    assert response.status_code == 200

    complaint.refresh_from_db()
    assert complaint.assigned_handler_id == 5001
    assert complaint.priority == "High"
    assert complaint.sla_due_date is not None

    # Check progress trail
    progress_entries = complaint.progress_history.all()
    assert progress_entries.count() >= 1
    assert any("assign" in p.action.lower() for p in progress_entries)


def test_progress_update_workflow(stub_iam):
    """BW-CMS-03: Progress updates move status to In Progress and log remarks."""
    client = auth_client(stub_iam, user_id=5001, kind="staff", roles=("complaint_handler",))

    complaint = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="maintenance",
        description="Broken lock on main laboratory door.",
        status="Submitted",
    )

    progress_payload = {
        "remarks": "Carpentry team dispatched with replacement hardware.",
        "action": "WORK_UNDERWAY",
    }
    response = client.post(f"/api/v1/cms/complaints/{complaint.id}/update_progress/", data=progress_payload, format="json")
    assert response.status_code == 200

    complaint.refresh_from_db()
    assert complaint.status == "In Progress"
    latest_progress = complaint.progress_history.last()
    assert latest_progress.remarks == "Carpentry team dispatched with replacement hardware."


def test_resolve_and_reject_validation(stub_iam):
    """BW-CMS-04 & BW-CMS-05: Validation of resolution details and rejection reason."""
    client = auth_client(stub_iam, user_id=5001, kind="staff", roles=("complaint_handler",))

    complaint1 = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="maintenance",
        description="AC remote missing in conference room.",
        status="In Progress",
    )

    # Resolve without required details -> 400
    res_fail = client.post(f"/api/v1/cms/complaints/{complaint1.id}/resolve/", data={}, format="json")
    assert res_fail.status_code == 400

    # Resolve with details -> 200
    res_ok = client.post(f"/api/v1/cms/complaints/{complaint1.id}/resolve/", data={"resolution_details": "Provided new universal remote and tested."}, format="json")
    assert res_ok.status_code == 200
    complaint1.refresh_from_db()
    assert complaint1.status == "Resolved"
    assert "Provided new universal remote" in complaint1.resolution_details

    # Rejection workflow
    complaint2 = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1002,
        category="academic",
        description="Request private tutoring.",
        status="Submitted",
    )
    # Reject without reason -> 400
    res_rej_fail = client.post(f"/api/v1/cms/complaints/{complaint2.id}/reject/", data={}, format="json")
    assert res_rej_fail.status_code == 400

    # Reject with reason -> 200
    res_rej_ok = client.post(f"/api/v1/cms/complaints/{complaint2.id}/reject/", data={"rejection_reason": "Out of CMS operational scope."}, format="json")
    assert res_rej_ok.status_code == 200
    complaint2.refresh_from_db()
    assert complaint2.status == "Rejected"


def test_closure_verification_dual_path(stub_iam):
    """BW-CMS-06: Verification paths for standard closure and supervisor-mandated closure."""
    # Path A: Standard complaint verified by user
    client_user = auth_client(stub_iam, user_id=1001, kind="student", roles=("student",))
    complaint_std = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="mess",
        description="Water filter cartridge needs cleaning.",
        status="Resolved",
        requires_supervisor_verification=False,
    )
    res_verify = client_user.post(f"/api/v1/cms/complaints/{complaint_std.id}/verify_closure/", data={"user_satisfied": True, "remarks": "Confirmed clean."}, format="json")
    assert res_verify.status_code == 200
    complaint_std.refresh_from_db()
    assert complaint_std.status == "Closed"
    assert complaint_std.user_verified is True
    assert complaint_std.closure_timestamp is not None

    # Path B: Critical complaint requiring supervisor verification
    complaint_crit = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="hostel",
        description="Power failure in block A.",
        status="Resolved",
        requires_supervisor_verification=True,
    )
    # Step 1: Complainant signs off
    client_u = auth_client(stub_iam, user_id=1001, kind="student", roles=("student",))
    res_u = client_u.post(f"/api/v1/cms/complaints/{complaint_crit.id}/verify_closure/", data={"user_satisfied": True}, format="json")
    assert res_u.status_code == 200
    complaint_crit.refresh_from_db()
    # Still Resolved because supervisor verification is required
    assert complaint_crit.status == "Resolved"
    assert complaint_crit.user_verified is True

    # Step 2: Supervisor verifies and closes
    client_s = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    res_s = client_s.post(f"/api/v1/cms/complaints/{complaint_crit.id}/verify_closure/", data={"user_satisfied": True, "remarks": "Electrical engineer sign-off verified."}, format="json")
    assert res_s.status_code == 200
    complaint_crit.refresh_from_db()
    assert complaint_crit.status == "Closed"
    assert complaint_crit.supervisor_verified is True
    assert complaint_crit.closure_timestamp is not None


def test_reopening_lifecycle(stub_iam):
    """BW-CMS-07 & BR-CMS-013: Reopening request lifecycle with supervisor adjudication."""
    complaint = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="hostel",
        description="Leaking shower in bathroom 4.",
        status="Closed",
        closure_timestamp=timezone.now() - timedelta(days=2),
    )

    # 1. Complainant requests reopen
    user_c = auth_client(stub_iam, user_id=1001, kind="student", roles=("student",))
    req_res = user_c.post(
        f"/api/v1/cms/complaints/{complaint.id}/request_reopen/",
        data={"dissatisfaction_reason": "Still dripping after initial plumber visit."},
        format="json",
    )
    assert req_res.status_code in [200, 201]
    reopening = complaint.reopenings.last()
    assert reopening.status == "pending"

    # 2. Supervisor approves
    sup_c = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))
    dec_res = sup_c.post(
        f"/api/v1/cms/complaints/{complaint.id}/decide_reopen/",
        data={
            "reopening_id": reopening.id,
            "decision": "approved",
            "supervisor_remarks": "Approved. Senior plumbing specialist assigned.",
        },
        format="json",
    )
    assert dec_res.status_code == 200
    complaint.refresh_from_db()
    reopening.refresh_from_db()
    assert reopening.status == "approved"
    assert complaint.status == "In Progress"


def test_manual_and_sla_escalation(stub_iam):
    """BW-CMS-08 & BR-CMS-007: Manual escalation and automated SLA breach detection."""
    client = auth_client(stub_iam, user_id=1001, kind="student", roles=("student",))

    # Manual escalation
    comp_manual = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="academic",
        description="Smartboard in lecture hall LH-1 projector flicker.",
        status="In Progress",
    )
    res_esc = client.post(
        f"/api/v1/cms/complaints/{comp_manual.id}/escalate/",
        data={"escalation_remarks": "Upcoming keynote lecture requires immediate resolution."},
        format="json",
    )
    assert res_esc.status_code == 200
    comp_manual.refresh_from_db()
    assert comp_manual.is_escalated is True
    assert comp_manual.escalation_type == "manual"

    # Automated SLA breach service
    comp_overdue = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="network",
        description="Server rack switch outage.",
        status="In Progress",
        sla_due_date=timezone.now() - timedelta(hours=3),
        is_escalated=False,
    )
    res_sla = client.post("/api/v1/cms/complaints/check_sla/", format="json")
    assert res_sla.status_code == 200
    sla_data = res_sla.json()
    assert sla_data.get("breached_escalated", 0) >= 1

    comp_overdue.refresh_from_db()
    assert comp_overdue.is_escalated is True
    assert comp_overdue.escalation_type == "automatic_sla"


def test_feedback_and_reports(stub_iam):
    """AFR-041 to AFR-045 & AFR-061: Complainant feedback and administrative SLA reporting."""
    client = auth_client(stub_iam, user_id=1001, kind="student", roles=("student",))

    complaint = Complaint.objects.create(
        complaint_id=Complaint.generate_unique_complaint_id(),
        complainant_user_id=1001,
        category="hostel",
        description="Broken chair in study room.",
        status="Closed",
    )

    fb_res = client.post(
        "/api/v1/cms/feedback/",
        data={
            "complaint": complaint.id,
            "rating": 5,
            "comments": "Replaced within 30 minutes! Excellent service.",
        },
        format="json",
    )
    assert fb_res.status_code == 201
    assert complaint.feedbacks.count() == 1

    # Analytics report
    rep_res = client.get("/api/v1/cms/complaints/reports/")
    assert rep_res.status_code == 200
    rep = rep_res.json()
    assert "total" in rep
    assert "by_status" in rep
    assert "by_category" in rep
    assert "average_rating" in rep
    assert rep["total"] >= 1


def test_announcements_and_role_management(stub_iam):
    """AFR-051 & AFR-071: Broad announcements and handler/supervisor role assignments."""
    client = auth_client(stub_iam, user_id=9999, kind="staff", roles=("complaint_supervisor",))

    # Announcement
    ann_res = client.post(
        "/api/v1/cms/announcements/",
        data={
            "title": "Scheduled Campus Water Supply Maintenance",
            "content": "Water supply will be suspended between 2 PM and 5 PM for tank cleaning.",
            "author_role": "complaint_supervisor",
        },
        format="json",
    )
    assert ann_res.status_code == 201
    assert ComplaintAnnouncement.objects.filter(title__contains="Water Supply").exists()

    # Role assignment
    role_res = client.post(
        "/api/v1/cms/roles/",
        data={
            "user_id": 7001,
            "role_type": "complaint_handler",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "is_active": True,
        },
        format="json",
    )
    assert role_res.status_code == 201
    assert CmsRoleAssignment.objects.filter(user_id=7001, role_type="complaint_handler").exists()
