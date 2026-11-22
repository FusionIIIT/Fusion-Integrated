"""Integration & API tests for Hostel Management."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hostel.models import (
    Hostel,
    HostelFine,
    Room,
    RoomAllotment,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def hostel_h1():
    return Hostel.objects.create(
        code="H1", name="Hall of Residence 1", gender_type="boys", capacity=100, is_active=True
    )


@pytest.fixture
def room_101(hostel_h1):
    return Room.objects.create(
        hostel=hostel_h1, room_number="101", floor=1, capacity=2, current_occupancy=0
    )


@pytest.fixture
def room_102(hostel_h1):
    return Room.objects.create(
        hostel=hostel_h1, room_number="102", floor=1, capacity=2, current_occupancy=0
    )


def client_for(stub_iam, user_id=1, roles=("Super Admin",), permissions=(), modules=("hostel",)):
    stub_iam(make_session(user_id=user_id, roles=roles, permissions=permissions, modules=modules))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_super_admin_create_hostel(stub_iam):
    c = client_for(stub_iam, user_id=1, permissions=("hostel.hostel.manage",))
    resp = c.post(
        "/api/v1/hostel/hostels",
        {"code": "H2", "name": "Hall of Residence 2", "gender_type": "girls", "capacity": 150},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "H2"
    assert Hostel.objects.filter(code="H2").exists()


def test_accommodation_request_and_allotment(stub_iam, hostel_h1, room_101):
    # Student submits accommodation request (HM-UC-005)
    c_student = client_for(
        stub_iam, user_id=101, permissions=("hostel.accommodation.create", "hostel.allotment.view")
    )
    req_resp = c_student.post(
        "/api/v1/hostel/requests",
        {
            "preferred_hostel": hostel_h1.id,
            "academic_year": "2026-2027",
            "semester": "Monsoon",
        },
        format="json",
    )
    assert req_resp.status_code == 201
    req_id = req_resp.json()["id"]

    # Super Admin records allotment (HM-UC-006, BW-HM-01)
    c_admin = client_for(stub_iam, user_id=1, permissions=("hostel.allotment.manage",))
    allot_resp = c_admin.post(
        "/api/v1/hostel/allotments/batch",
        {
            "student_user_id": 101,
            "hostel_id": hostel_h1.id,
            "room_id": room_101.id,
            "request_id": req_id,
            "allotment_round": "Round 1",
        },
        format="json",
    )
    assert allot_resp.status_code == 201
    assert RoomAllotment.objects.filter(
        student_user_id=101, room=room_101, status="active"
    ).exists()

    room_101.refresh_from_db()
    assert room_101.current_occupancy == 1

    # Student views own allotment (HM-UC-008)
    view_resp = c_student.get("/api/v1/hostel/allotments")
    assert view_resp.status_code == 200
    assert len(view_resp.json()) == 1
    assert view_resp.json()[0]["student_user_id"] == 101


def test_room_capacity_enforcement(stub_iam, hostel_h1, room_101):
    room_101.current_occupancy = 2
    room_101.capacity = 2
    room_101.save()

    c_admin = client_for(stub_iam, user_id=1, permissions=("hostel.allotment.manage",))
    resp = c_admin.post(
        "/api/v1/hostel/allotments/batch",
        {
            "student_user_id": 105,
            "hostel_id": hostel_h1.id,
            "room_id": room_101.id,
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "capacity" in resp.json()["error"].lower()


def test_leave_workflow(stub_iam, hostel_h1):
    # Student submits leave (HM-UC-014, BW-HM-02)
    c_student = client_for(
        stub_iam, user_id=101, permissions=("hostel.leave.create", "hostel.leave.view_self")
    )
    sub_resp = c_student.post(
        "/api/v1/hostel/leaves",
        {
            "hostel": hostel_h1.id,
            "leave_type": "home",
            "start_date": "2026-11-25",
            "end_date": "2026-11-28",
            "reason": "Family function",
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    leave_id = sub_resp.json()["id"]

    # Caretaker reviews & approves leave (HM-UC-015, CW-HM-01)
    c_caretaker = client_for(stub_iam, user_id=50, permissions=("hostel.leave.review",))
    dec_resp = c_caretaker.post(
        f"/api/v1/hostel/leaves/{leave_id}/decide",
        {
            "decision": "approved",
            "remarks": "Approved by Caretaker",
        },
        format="json",
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "approved"


def test_complaint_escalation_workflow(stub_iam, hostel_h1):
    # Student submits complaint (HM-UC-017, BW-HM-05)
    c_student = client_for(
        stub_iam, user_id=101, permissions=("hostel.complaint.create", "hostel.complaint.view_self")
    )
    sub_resp = c_student.post(
        "/api/v1/hostel/complaints",
        {
            "hostel": hostel_h1.id,
            "category": "electrical",
            "description": "Geyser not working in 1st floor washroom",
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    complaint_id = sub_resp.json()["id"]

    # Caretaker escalates to Warden (HM-UC-018, CW-HM-02)
    c_caretaker = client_for(stub_iam, user_id=50, permissions=("hostel.complaint.manage",))
    esc_resp = c_caretaker.patch(
        f"/api/v1/hostel/complaints/{complaint_id}",
        {
            "status": "escalated",
            "action_taken": "Heating element replacement needed; escalated to Warden",
        },
        format="json",
    )
    assert esc_resp.status_code == 200
    assert esc_resp.json()["status"] == "escalated"


def test_guest_room_booking_workflow(stub_iam, hostel_h1, room_102):
    # Student submits booking (HM-UC-020, BW-HM-06)
    c_student = client_for(
        stub_iam, user_id=101, permissions=("hostel.guestroom.create", "hostel.guestroom.view_self")
    )
    sub_resp = c_student.post(
        "/api/v1/hostel/guest-rooms",
        {
            "hostel": hostel_h1.id,
            "guest_name": "John Doe",
            "guest_relation": "Father",
            "guest_contact": "9876543210",
            "check_in_date": "2026-12-01",
            "check_out_date": "2026-12-03",
        },
        format="json",
    )
    assert sub_resp.status_code == 201
    booking_id = sub_resp.json()["id"]

    # Caretaker approves booking (HM-UC-021, CW-HM-03)
    c_caretaker = client_for(stub_iam, user_id=50, permissions=("hostel.guestroom.manage",))
    dec_resp = c_caretaker.post(
        f"/api/v1/hostel/guest-rooms/{booking_id}/decide",
        {
            "decision": "approved",
            "room_id": room_102.id,
            "remarks": "Guest room 102 reserved",
        },
        format="json",
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "approved"


def test_disciplinary_fine_recording(stub_iam, hostel_h1):
    c_caretaker = client_for(stub_iam, user_id=50, permissions=("hostel.fine.record",))
    resp = c_caretaker.post(
        "/api/v1/hostel/fines",
        {
            "hostel": hostel_h1.id,
            "student_user_id": 101,
            "amount": "500.00",
            "reason": "Hostel quiet hours rule violation",
            "imposed_date": "2026-11-22",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "recorded"
    assert HostelFine.objects.filter(student_user_id=101, amount=Decimal("500.00")).exists()


def test_operational_report(stub_iam, hostel_h1, room_101):
    c_warden = client_for(stub_iam, user_id=20, permissions=("hostel.report.view",))
    resp = c_warden.get(f"/api/v1/hostel/reports/{hostel_h1.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hostel_id"] == hostel_h1.id
    assert "total_rooms" in data
    assert "current_occupancy" in data
