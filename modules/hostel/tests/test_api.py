"""API endpoint integration tests: RBAC enforcement, serializer validation, HTTP contracts."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hostel.domain.constants import HostelGender
from modules.hostel.services import hostel_service, room_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def hostel():
    return hostel_service.create_hostel(
        name="Aryabhatta Hostel",
        code="BH-1",
        capacity=100,
        gender=HostelGender.BOYS,
        creator_user_id=1,
    )


@pytest.fixture
def room(hostel):
    return room_service.create_room(
        hostel_id=hostel.id,
        room_number="101",
        floor=1,
        capacity=2,
    )


def test_super_admin_can_list_and_create_hostels(stub_iam):
    """CFR-HM-001: Super admin manages hostel master."""
    stub_iam(
        make_session(
            user_id=1,
            modules=("hostel",),
            permissions=("hostel.hostel.view", "hostel.hostel.manage"),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-1")

    # Create new hostel
    resp = client.post(
        "/api/v1/hostel/hostels/",
        {
            "name": "Nagarjuna Hostel",
            "code": "BH-3",
            "capacity": 120,
            "gender": "boys",
            "description": "B.Tech Boys Hostel",
            "is_active": True,
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["code"] == "BH-3"

    # List hostels
    list_resp = client.get("/api/v1/hostel/hostels/")
    assert list_resp.status_code == 200
    assert any(h["code"] == "BH-3" for h in list_resp.data["results"])


def test_student_cannot_create_hostel(stub_iam):
    """Student with view_self cannot create hostel -> 403."""
    stub_iam(
        make_session(
            user_id=2001,
            modules=("hostel",),
            permissions=("hostel.hostel.view_self",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token student-token")

    resp = client.post(
        "/api/v1/hostel/hostels/",
        {
            "name": "Unauthorized Hostel",
            "code": "BH-X",
            "capacity": 50,
            "gender": "boys",
        },
        format="json",
    )
    assert resp.status_code == 403


def test_student_dashboard_endpoint(stub_iam, hostel, room):
    """CFR-HM-033: Dashboard statistics."""
    stub_iam(
        make_session(
            user_id=3001,
            modules=("hostel",),
            permissions=("hostel.hostel.view_self",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token student-token")

    resp = client.get("/api/v1/hostel/dashboard/stats/")
    assert resp.status_code == 200
    assert "is_admin" in resp.data
    assert resp.data["is_admin"] is False
    assert resp.data["my_open_complaints"] == 0
    assert resp.data["my_pending_fines"] == 0


def test_student_can_submit_complaint(stub_iam, hostel):
    """CFR-HM-015: Student lodges a maintenance complaint."""
    stub_iam(
        make_session(
            user_id=4001,
            modules=("hostel",),
            permissions=("hostel.complaint.submit",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token student-token")

    resp = client.post(
        "/api/v1/hostel/complaints/",
        {
            "hostel": hostel.id,
            "title": "Water leakage in washroom",
            "description": "Floor 1 washroom pipe leaking continuously",
            "location": "1st Floor Wing A",
            "category": "plumbing",
            "severity": "high",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["category"] == "plumbing"
    assert resp.data["status"] == "open"


def test_warden_reports_endpoint(stub_iam, hostel, room):
    """CFR-HM-031, 032: Executive reports."""
    stub_iam(
        make_session(
            user_id=101,
            modules=("hostel",),
            permissions=("hostel.report.view",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token warden-token")

    resp = client.get(f"/api/v1/hostel/reports/?type=occupancy&hostel_id={hostel.id}")
    assert resp.status_code == 200
    assert "occupancy" in resp.data
    assert resp.data["occupancy"][0]["total_capacity"] == 2
