"""API integration and permission tests for Complaint Management System."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.complaints.models import ComplaintCategory
from modules.complaints import services

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), kind="student", uid=101, modules=("complaints",)):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            permissions=permissions,
            modules=modules,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


@pytest.fixture
def category():
    return ComplaintCategory.objects.create(
        name="Hostel Infrastructure",
        description="Room fixtures and amenities",
        default_sla_hours=48,
    )


def test_unauthenticated_request_is_refused():
    c = APIClient()
    res = c.get("/api/v1/complaints/")
    assert res.status_code == 401


def test_ungranted_module_is_refused(stub_iam):
    # User lacks "complaints" module grant
    c = _client(stub_iam, modules=("other_module",))
    res = c.get("/api/v1/complaints/")
    assert res.status_code == 403


def test_submit_complaint_endpoint(stub_iam, category):
    c = _client(
        stub_iam,
        permissions=("complaints.complaint.create", "complaints.complaint.view_self"),
        uid=101,
    )
    payload = {
        "category_id": category.id,
        "location": "Room 101, Hall 4",
        "description": "Window glass cracked and rattling.",
        "priority": "medium",
    }
    res = c.post("/api/v1/complaints/", payload, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body["complaint_id"].startswith("CMP-")
    assert body["status"] == "submitted"
    assert body["location"] == "Room 101, Hall 4"


def test_complainant_only_sees_own_complaints(stub_iam, category):
    # Complainant A submits
    services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Loc A",
        description="Desc A",
    )
    # Complainant B submits
    services.submit_complaint(
        complainant_user_id=102,
        category_id=category.id,
        location="Loc B",
        description="Desc B",
    )

    # Client A logs in
    client_a = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self",),
        uid=101,
    )
    res_a = client_a.get("/api/v1/complaints/").json()
    assert len(res_a) == 1
    assert res_a[0]["location"] == "Loc A"


def test_handler_sees_all_complaints_and_can_assign(stub_iam, category):
    c1 = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Loc 1",
        description="Desc 1",
    )
    services.submit_complaint(
        complainant_user_id=102,
        category_id=category.id,
        location="Loc 2",
        description="Desc 2",
    )

    # Handler client
    handler = _client(
        stub_iam,
        permissions=("complaints.complaint.view", "complaints.complaint.assign"),
        kind="staff",
        uid=201,
    )
    all_complaints = handler.get("/api/v1/complaints/").json()
    assert len(all_complaints) == 2

    # Assign complaint
    assign_res = handler.post(
        f"/api/v1/complaints/{c1.id}/assign/",
        {"worker_name": "Suresh Carpenter", "priority": "high"},
        format="json",
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_worker_name"] == "Suresh Carpenter"
    assert assign_res.json()["priority"] == "high"


def test_progress_resolve_and_verify_close_api(stub_iam, category):
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Hall 3",
        description="Broken lock",
        verification_required="user",
    )

    handler = _client(
        stub_iam,
        permissions=(
            "complaints.complaint.view",
            "complaints.complaint.update",
            "complaints.complaint.resolve",
        ),
        kind="staff",
        uid=201,
    )

    # Update progress
    prog_res = handler.post(
        f"/api/v1/complaints/{c.id}/progress/",
        {"progress_notes": "Lock replacement in progress"},
        format="json",
    )
    assert prog_res.status_code == 200
    assert prog_res.json()["status"] == "in_progress"

    # Resolve complaint
    resolve_res = handler.post(
        f"/api/v1/complaints/{c.id}/resolve/",
        {"resolution_details": "Replaced brass cylinder lock"},
        format="json",
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"

    # User verifies resolution
    complainant = _client(
        stub_iam,
        permissions=("complaints.complaint.close", "complaints.complaint.view_self"),
        uid=101,
    )
    close_res = complainant.post(
        f"/api/v1/complaints/{c.id}/verify-close/",
        {"remarks": "Lock tested and working smoothly"},
        format="json",
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "closed"


def test_reports_summary_api(stub_iam, category):
    services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Hall 1",
        description="Drain clogged",
    )

    admin = _client(
        stub_iam,
        permissions=("complaints.complaint.report",),
        kind="admin",
        uid=1,
    )
    res = admin.get("/api/v1/complaints/reports/summary/")
    assert res.status_code == 200
    body = res.json()
    assert body["total_complaints"] >= 1
    assert "by_status" in body
    assert "by_priority" in body
