import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.hm.models import (
    Hostel,
    Room,
    AccommodationRequest,
    RoomAssignment,
    LeaveRequest,
    Complaint,
    GuestBooking,
    ExtendedStayRequest,
    FineRecord,
    InventoryItem,
    Notice,
    HostelRoleBinding,
)
from modules.hm.services import (
    create_hostel,
    assign_hostel_role_binding,
    update_room_capacity,
    submit_accommodation_request,
    allot_room_from_request,
    vacate_room_assignment,
    exchange_room_assignments,
    submit_leave_request,
    decide_leave_request,
    submit_complaint,
    record_complaint_event,
    submit_guest_booking,
    decide_guest_booking,
    submit_extended_stay,
    decide_extended_stay,
    record_fine,
    create_inventory_item,
    update_inventory_item,
    publish_notice,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def hostel():
    return Hostel.objects.create(name="Aryabhatta", code="BH-1", is_active=True)


@pytest.fixture
def room(hostel):
    return Room.objects.create(hostel=hostel, room_number="101", capacity=2, is_active=True)


def test_services_hostel_and_capacity(hostel, room):
    assert room.occupied_count == 0
    assert room.available_capacity == 2

    # Update capacity
    updated_room = update_room_capacity(room_id=room.id, new_capacity=3)
    assert updated_room.capacity == 3

    with pytest.raises(ValueError, match="Room capacity must be greater than zero"):
        update_room_capacity(room_id=room.id, new_capacity=0)


def test_services_allotment_and_capacity_guard(hostel, room):
    # Student 1 applies
    req1 = submit_accommodation_request(user_id=101, hostel=hostel, preferred_room_type="Double")
    assert req1.status == "submitted"

    # Allot to room
    assign1 = allot_room_from_request(request_id=req1.id, room_id=room.id, actor_user_id=1)
    assert assign1.status == "active"
    req1.refresh_from_db()
    assert req1.status == "allotted"
    room.refresh_from_db()
    assert room.occupied_count == 1
    assert room.available_capacity == 1

    # Student 2 applies & gets allotted
    req2 = submit_accommodation_request(user_id=102, hostel=hostel)
    assign2 = allot_room_from_request(request_id=req2.id, room_id=room.id, actor_user_id=1)
    assert assign2.status == "active"
    room.refresh_from_db()
    assert room.occupied_count == 2
    assert room.available_capacity == 0

    # Student 3 applies & tries to allot to full room -> fails with guard
    req3 = submit_accommodation_request(user_id=103, hostel=hostel)
    with pytest.raises(ValueError, match="Room capacity exceeded"):
        allot_room_from_request(request_id=req3.id, room_id=room.id, actor_user_id=1)

    # Vacate student 1
    vacated = vacate_room_assignment(assignment_id=assign1.id, reason="Graduated")
    assert vacated.status == "vacated"
    room.refresh_from_db()
    assert room.occupied_count == 1
    assert room.available_capacity == 1

    # Now student 3 can be allotted
    assign3 = allot_room_from_request(request_id=req3.id, room_id=room.id, actor_user_id=1)
    assert assign3.status == "active"


def test_services_exchange_assignments(hostel):
    r1 = Room.objects.create(hostel=hostel, room_number="101", capacity=1)
    r2 = Room.objects.create(hostel=hostel, room_number="102", capacity=1)
    a1 = RoomAssignment.objects.create(user_id=101, room=r1, status="active")
    a2 = RoomAssignment.objects.create(user_id=102, room=r2, status="active")

    new_a1, new_a2 = exchange_room_assignments(
        assignment_a_id=a1.id,
        assignment_b_id=a2.id,
        actor_user_id=1,
        reason="Mutual swap",
    )
    a1.refresh_from_db()
    a2.refresh_from_db()
    assert a1.status == "exchanged"
    assert a2.status == "exchanged"
    assert new_a1.user_id == 101 and new_a1.room == r2
    assert new_a2.user_id == 102 and new_a2.room == r1


def test_services_leave_and_complaint(hostel):
    # Leave workflow
    from datetime import date
    leave = submit_leave_request(
        user_id=101, hostel=hostel, start_date=date(2026, 11, 25), end_date=date(2026, 11, 28), reason="Family event"
    )
    assert leave.status == "submitted"
    decided = decide_leave_request(request_id=leave.id, decision="approve", decided_by_user_id=2, remarks="Granted")
    assert decided.status == "approved"

    # Complaint workflow
    complaint = submit_complaint(user_id=101, hostel=hostel, category="Plumbing", description="Tap leakage")
    assert complaint.status == "submitted"
    assert complaint.events.count() == 1

    updated = record_complaint_event(
        complaint_id=complaint.id, event="update", actor_user_id=2, actor_kind="caretaker", remarks="Plumber dispatched"
    )
    assert updated.status == "updated"
    assert updated.events.count() == 2

    resolved = record_complaint_event(
        complaint_id=complaint.id, event="resolve", actor_user_id=2, actor_kind="caretaker", remarks="Fixed"
    )
    assert resolved.status == "resolved"
    assert resolved.events.count() == 3


def test_api_scoping_student_vs_staff(stub_iam, hostel, room):
    # Student 101 creates accommodation request
    AccommodationRequest.objects.create(user_id=101, hostel=hostel, reason="Student 101 req")
    AccommodationRequest.objects.create(user_id=202, hostel=hostel, reason="Student 202 req")

    # Student 101 gets only their own request
    stub_iam(make_session(user_id=101, kind="student", modules=("hm",), permissions=("hm.accommodation_request.view",)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-token")

    res = client.get("/api/v1/hm/accommodation-requests")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 101

    # Permission denial Twin: student without permission gets 403
    stub_iam(make_session(user_id=101, kind="student", modules=("hm",), permissions=()))
    res = client.get("/api/v1/hm/accommodation-requests")
    assert res.status_code == 403

    # Module grant denial: student without hm module grant gets 403
    stub_iam(make_session(user_id=101, kind="student", modules=(), permissions=("hm.accommodation_request.view",)))
    res = client.get("/api/v1/hm/accommodation-requests")
    assert res.status_code == 403
