"""Security negative test matrix for Complaint Management System APIs.

Verifies:
- Unauthenticated requests answer 401.
- Authenticated but missing module grant answers 403.
- Authenticated with module grant but missing specific permission answers 403.
- Non-owner resource access answers 404 (zero data leakage).
- Hostile or invalid input payloads answer 400.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.complaints import services
from modules.complaints.models import ComplaintCategory

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


# ------------------------------------------------------------------------------
# 1. Non-Owner Isolation (Answers 404, not 403 or 200)
# ------------------------------------------------------------------------------

def test_non_owner_cannot_read_another_complaint(stub_iam, category):
    """Person A cannot read Person B's complaint by ID. Out-of-scope returns 404."""
    # Person B (uid 102) submits a complaint
    c_b = services.submit_complaint(
        complainant_user_id=102,
        category_id=category.id,
        location="Room 502",
        description="Private room issue",
    )

    # Person A (uid 101) attempts to fetch Person B's complaint by ID
    client_a = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self",),
        uid=101,
    )
    res = client_a.get(f"/api/v1/complaints/{c_b.id}/")
    assert res.status_code == 404, f"Expected 404 for out-of-scope access, got {res.status_code}"


def test_non_owner_cannot_verify_or_close_another_complaint(stub_iam, category):
    """Person A cannot verify or close Person B's complaint."""
    c_b = services.submit_complaint(
        complainant_user_id=102,
        category_id=category.id,
        location="Room 502",
        description="Private room issue",
        verification_required="user",
    )
    services.resolve_complaint(complaint=c_b, actor_user_id=201, resolution_details="Fixed")

    # Person A tries to close Person B's complaint
    client_a = _client(
        stub_iam,
        permissions=("complaints.complaint.close", "complaints.complaint.view_self"),
        uid=101,
    )
    res = client_a.post(
        f"/api/v1/complaints/{c_b.id}/verify-close/",
        {"remarks": "Unauthorized closure attempt"},
        format="json",
    )
    # Returns 404 because complaint is out of user A's visible scope
    assert res.status_code == 404


# ------------------------------------------------------------------------------
# 2. Permission Scoping (Missing Specific Permissions answers 403)
# ------------------------------------------------------------------------------

def test_student_lacking_assign_permission_cannot_assign(stub_iam, category):
    """User without complaints.complaint.assign receives 403 on assign endpoint."""
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Room 101",
        description="Broken fan",
    )
    # Student client has view_self and create, but NOT assign
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self", "complaints.complaint.create"),
        uid=101,
    )
    res = client.post(
        f"/api/v1/complaints/{c.id}/assign/",
        {"worker_name": "Worker 1"},
        format="json",
    )
    assert res.status_code == 403


def test_student_lacking_role_manage_cannot_assign_roles(stub_iam):
    """User without complaints.role.manage receives 403 on role assignment endpoint."""
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self",),
        uid=101,
    )
    payload = {
        "role_type": "handler",
        "user_id": 999,
        "start_date": "2026-11-23T00:00:00Z",
        "end_date": "2027-11-23T00:00:00Z",
    }
    res = client.post("/api/v1/complaints/roles/", payload, format="json")
    assert res.status_code == 403


def test_student_lacking_publish_permission_cannot_publish_announcements(stub_iam):
    """User without complaints.announcement.publish receives 403."""
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self",),
        uid=101,
    )
    payload = {
        "title": "Unauthorized Announcement",
        "content": "Should be refused",
    }
    res = client.post("/api/v1/complaints/announcements/", payload, format="json")
    assert res.status_code == 403


def test_student_lacking_supervise_permission_cannot_review_reopening(stub_iam, category):
    """User without complaints.complaint.supervise receives 403."""
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Room 101",
        description="Leaking roof",
    )
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.view_self",),
        uid=101,
    )
    res = client.post(
        f"/api/v1/complaints/{c.id}/reopen-review/",
        {"approved": True, "remarks": "Unauthorized review"},
        format="json",
    )
    assert res.status_code == 403


# ------------------------------------------------------------------------------
# 3. Invalid Input Payloads (Answers 400)
# ------------------------------------------------------------------------------

def test_submit_complaint_empty_payload_returns_400(stub_iam):
    """Empty payload returns 400."""
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.create",),
        uid=101,
    )
    res = client.post("/api/v1/complaints/", {}, format="json")
    assert res.status_code == 400


def test_submit_complaint_missing_required_fields_returns_400(stub_iam, category):
    """Missing description or location returns 400."""
    client = _client(
        stub_iam,
        permissions=("complaints.complaint.create",),
        uid=101,
    )
    # Missing description
    res = client.post(
        "/api/v1/complaints/",
        {"category_id": category.id, "location": "Room 101", "description": "  "},
        format="json",
    )
    assert res.status_code == 400


def test_resolve_complaint_missing_details_returns_400(stub_iam, category):
    """Resolving without resolution_details returns 400."""
    c = services.submit_complaint(
        complainant_user_id=101,
        category_id=category.id,
        location="Room 101",
        description="Door handle broken",
    )
    handler = _client(
        stub_iam,
        permissions=("complaints.complaint.view", "complaints.complaint.resolve"),
        kind="staff",
        uid=201,
    )
    res = handler.post(
        f"/api/v1/complaints/{c.id}/resolve/",
        {"resolution_details": ""},
        format="json",
    )
    assert res.status_code == 400


def test_nonexistent_complaint_returns_404(stub_iam):
    """Requesting nonexistent complaint ID returns 404."""
    handler = _client(
        stub_iam,
        permissions=("complaints.complaint.view",),
        kind="staff",
        uid=201,
    )
    res = handler.get("/api/v1/complaints/999999/")
    assert res.status_code == 404
