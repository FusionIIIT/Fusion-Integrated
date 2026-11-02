"""Service layer tests: transactional integrity, business rules, DB operations."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.hostel.domain.constants import (
    AttendanceStatus,
    ComplaintCategory,
    ComplaintSeverity,
    ComplaintStatus,
    ExtendedStayReason,
    ExtendedStayStatus,
    FineStatus,
    GuestRoomBookingStatus,
    HostelGender,
    LeaveStatus,
    LeaveType,
    NoticeAudience,
    RoleBindingType,
    RoomStatus,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
    DuplicateAllotmentError,
    ValidationError,
)
from modules.hostel.models import (
    AttendanceRecord,
)
from modules.hostel.services import (
    allotment_service,
    attendance_service,
    complaint_service,
    extended_stay_service,
    fine_service,
    guest_room_service,
    hostel_service,
    leave_service,
    notice_service,
    room_service,
)

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


def test_hostel_and_role_binding_lifecycle(hostel):
    """CFR-HM-001, 002: Create hostel, toggle active, assign role."""
    assert hostel.is_active is True

    # Toggle active
    updated = hostel_service.set_hostel_active_status(hostel.id, is_active=False, actor_user_id=1)
    assert updated.is_active is False

    # Assign warden
    binding = hostel_service.assign_role_binding(
        hostel_id=hostel.id,
        user_id=101,
        role=RoleBindingType.WARDEN,
        assigner_user_id=1,
    )
    assert binding.is_active is True
    assert binding.role == RoleBindingType.WARDEN

    # Deactivate role binding
    deactivated = hostel_service.deactivate_role_binding(binding.id)
    assert deactivated.is_active is False


def test_room_allotment_and_capacity_enforcement(hostel, room):
    """CFR-HM-003, 005, BR-HM-008..010: Capacity bounds and duplicate prevention."""
    # Allot bed 1
    allotment1 = allotment_service.allot_room(
        student_user_id=1001,
        hostel_id=hostel.id,
        room_id=room.id,
        bed_number="1",
    )
    assert allotment1.status == "active"
    room.refresh_from_db()
    assert room.current_occupancy == 1
    assert room.status == RoomStatus.OCCUPIED

    # Duplicate allotment for same student must raise error
    with pytest.raises(DuplicateAllotmentError):
        allotment_service.allot_room(
            student_user_id=1001,
            hostel_id=hostel.id,
            room_id=room.id,
            bed_number="2",
        )

    # Allot bed 2 (fills capacity)
    allotment2 = allotment_service.allot_room(
        student_user_id=1002,
        hostel_id=hostel.id,
        room_id=room.id,
        bed_number="2",
    )
    assert allotment2.status == "active"
    room.refresh_from_db()
    assert room.current_occupancy == 2
    assert room.status == RoomStatus.FULL

    # Allot bed 3 when room is full must fail
    with pytest.raises(CapacityExceededError):
        allotment_service.allot_room(
            student_user_id=1003,
            hostel_id=hostel.id,
            room_id=room.id,
            bed_number="3",
        )

    # Vacate bed 1
    vacated = allotment_service.vacate_room(
        allotment_id=allotment1.id,
        actor_user_id=1,
        vacation_remarks="Vacated for semester end",
    )
    assert vacated.status == "vacated"
    room.refresh_from_db()
    assert room.current_occupancy == 1
    assert room.status == RoomStatus.OCCUPIED


def test_attendance_service(hostel, room):
    """CFR-HM-009..011, BR-HM-011: Daily night attendance."""
    allotment_service.allot_room(
        student_user_id=1001,
        hostel_id=hostel.id,
        room_id=room.id,
        bed_number="1",
    )
    today = date.today()

    records = [
        {"student_user_id": 1001, "status": AttendanceStatus.PRESENT, "remarks": "On time"},
        {"student_user_id": 1002, "status": AttendanceStatus.ABSENT, "remarks": "Unexcused"},
    ]
    created = attendance_service.record_daily_attendance(
        hostel_id=hostel.id,
        attendance_date=today,
        student_attendance_list=records,
        recorded_by_user_id=201,
    )
    assert len(created) == 2
    assert AttendanceRecord.objects.filter(hostel=hostel, date=today).count() == 2


def test_leave_service_lifecycle(hostel):
    """CFR-HM-012..014, BR-HM-012..014, BW-HM-02: Leave submission and decision."""
    start = date.today() + timedelta(days=2)
    end = start + timedelta(days=3)

    leave = leave_service.submit_leave_request(
        student_user_id=1001,
        hostel_id=hostel.id,
        from_date=start,
        to_date=end,
        reason="Family function",
        leave_type=LeaveType.HOME,
        destination="123 Home Street, City",
        emergency_contact="9876543210",
    )
    assert leave.status == LeaveStatus.PENDING

    # Decide approve
    decided = leave_service.decide_leave_request(
        leave_id=leave.id,
        decision="approved",
        caretaker_user_id=201,
        remarks="Approved by caretaker",
    )
    assert decided.status == LeaveStatus.APPROVED


def test_complaint_service_lifecycle(hostel):
    """CFR-HM-015..018, BR-HM-015..017, BW-HM-04: Complaint workflow."""
    complaint = complaint_service.submit_complaint(
        student_user_id=1001,
        hostel_id=hostel.id,
        title="Tube light not functioning",
        description="Flickering continuously in room 101",
        location="Room 101",
        category=ComplaintCategory.ELECTRICAL,
        severity=ComplaintSeverity.MEDIUM,
    )
    assert complaint.status == ComplaintStatus.OPEN

    # Update to in_progress
    in_prog = complaint_service.update_complaint_status(
        complaint_id=complaint.id,
        target_status=ComplaintStatus.IN_PROGRESS,
        actor_user_id=201,
        actor_role="caretaker",
        assigned_worker="Electrician Ramu",
    )
    assert in_prog.status == ComplaintStatus.IN_PROGRESS

    # Escalate to warden
    escalated = complaint_service.update_complaint_status(
        complaint_id=complaint.id,
        target_status=ComplaintStatus.ESCALATED,
        actor_user_id=201,
        actor_role="caretaker",
        resolution_notes="Requires replacement approval",
    )
    assert escalated.status == ComplaintStatus.ESCALATED

    # Warden resolves
    resolved = complaint_service.update_complaint_status(
        complaint_id=complaint.id,
        target_status=ComplaintStatus.RESOLVED,
        actor_user_id=101,
        actor_role="warden",
        resolution_notes="New light installed",
    )
    assert resolved.status == ComplaintStatus.RESOLVED


def test_fine_service_enforcement(hostel):
    """CFR-HM-025..027, BR-HM-025, 026: Fine issuance and paid verification."""
    fine = fine_service.record_fine(
        student_user_id=1001,
        hostel_id=hostel.id,
        amount=Decimal("500.00"),
        reason="Smoking in non-smoking zone",
        imposed_by_user_id=101,
    )
    assert fine.status == FineStatus.PENDING

    # Attempting to mark paid without receipt must raise ValidationError
    with pytest.raises(ValidationError):
        fine_service.update_fine_status(
            fine_id=fine.id,
            status=FineStatus.PAID,
            receipt_reference="",  # empty receipt
        )

    # Marking paid with receipt reference succeeds
    paid = fine_service.update_fine_status(
        fine_id=fine.id,
        status=FineStatus.PAID,
        receipt_reference="SBI-REC-98234",
        remarks="Dues cleared via SBI Collect",
    )
    assert paid.status == FineStatus.PAID
    assert paid.receipt_reference == "SBI-REC-98234"


def test_guest_room_service_lifecycle(hostel):
    """CFR-HM-019..021, BR-HM-018, 019: Guest room booking and check in/out."""
    start = date.today() + timedelta(days=5)
    end = start + timedelta(days=2)

    booking = guest_room_service.submit_guest_room_booking(
        student_user_id=1001,
        hostel_id=hostel.id,
        guest_name="Father of Student",
        relationship="Father",
        num_guests=1,
        check_in_date=start,
        check_out_date=end,
        purpose="Visit campus",
    )
    assert booking.status == GuestRoomBookingStatus.PENDING

    # Caretaker approves
    approved = guest_room_service.decide_guest_room_booking(
        booking_id=booking.id,
        decision="approved",
        allocated_room_number="G-01",
        caretaker_user_id=201,
    )
    assert approved.status == GuestRoomBookingStatus.APPROVED
    assert approved.allocated_room_number == "G-01"


def test_extended_stay_service(hostel):
    """CFR-HM-022..024, BR-HM-020..024: Extended stay vacation request."""
    start = date.today() + timedelta(days=10)
    end = start + timedelta(days=20)

    req = extended_stay_service.submit_extended_stay_request(
        student_user_id=1001,
        hostel_id=hostel.id,
        from_date=start,
        to_date=end,
        reason_type=ExtendedStayReason.INTERNSHIP,
        reason_details="Summer research project on campus",
    )
    assert req.status == ExtendedStayStatus.PENDING

    approved = extended_stay_service.decide_extended_stay_request(
        request_id=req.id,
        decision="approved",
        warden_user_id=101,
        remarks="Permission granted by Warden",
    )
    assert approved.status == ExtendedStayStatus.APPROVED


def test_notice_service(hostel):
    """CFR-HM-030: Digital notice board publication."""
    notice = notice_service.publish_notice(
        hostel_id=hostel.id,
        title="Hostel General Body Meeting",
        content="All residents are requested to assemble in the common room at 8 PM.",
        publisher_user_id=101,
        target_audience=NoticeAudience.ALL,
    )
    assert notice.is_active is True
    assert notice.title == "Hostel General Body Meeting"
