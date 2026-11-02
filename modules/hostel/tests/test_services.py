"""Unit tests for Hostel Management services and business rules."""

from datetime import date, timedelta
from decimal import Decimal
import pytest
from modules.hostel.domain.constants import (
    AccommodationStatus,
    AttendanceStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import (
    DuplicateActiveAllotmentError,
    HostelDomainError,
    InactiveHostelError,
    MandatoryFieldError,
    RoomCapacityExceededError,
)
from modules.hostel.models import (
    AccommodationRequest,
    AttendanceRecord,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelInventoryItem,
    HostelNotice,
    HostelRoleBinding,
    InventoryAuditLog,
    LeaveRequest,
    NotificationRecord,
    Room,
    RoomAllotment,
    RoomAssignmentHistory,
    SecurityGuardShift,
    StaffAssignment,
)
from modules.hostel.services import (
    create_hostel,
    create_or_update_inventory_item,
    create_or_update_role_binding,
    create_or_update_security_shift,
    create_or_update_staff_assignment,
    create_room,
    generate_operational_report,
    publish_notice,
    record_allotment_decision,
    record_attendance_batch,
    record_charge_and_compliance,
    record_extended_stay_decision,
    record_fine,
    record_guest_room_decision,
    record_individual_room_exchange,
    record_leave_decision,
    record_reallotment,
    record_room_vacation,
    submit_accommodation_request,
    submit_complaint,
    submit_extended_stay_request,
    submit_guest_room_request,
    submit_leave_request,
    toggle_hostel_status,
    update_complaint_status,
    update_hostel,
    update_room,
)


@pytest.mark.django_db
class TestHostelMasterService:
    def test_create_and_update_hostel(self):
        h = create_hostel(name="Hall 4", code="H4", capacity=250, description="Test Hall")
        assert h.id is not None
        assert h.capacity == 250

        # Duplicate check
        with pytest.raises(HostelDomainError):
            create_hostel(name="Hall 4", code="H4X")

        updated = update_hostel(h.id, capacity=300)
        assert updated.capacity == 300

    def test_toggle_active_status(self):
        h = create_hostel(name="Hall 5", code="H5")
        assert h.is_active is True
        toggled = toggle_hostel_status(h.id, is_active=False)
        assert toggled.is_active is False

    def test_role_binding_assignment(self):
        h = create_hostel(name="Hall 1", code="H1")
        binding = create_or_update_role_binding(
            hostel_id=h.id,
            user_id=101,
            role="warden",
            assigned_by_user_id=1,
            notes="Initial warden assignment",
        )
        assert binding.user_id == 101
        assert binding.role == "warden"
        assert binding.is_active is True

        # Notification generated (BR-HM-034)
        notif = NotificationRecord.objects.filter(recipient_user_id=101).first()
        assert notif is not None
        assert "Warden" in notif.message


@pytest.mark.django_db
class TestAllotmentAndRoomService:
    @pytest.fixture
    def setup_data(self):
        h = create_hostel(name="Hall 3", code="H3", capacity=10)
        r1 = create_room(hostel_id=h.id, room_number="101", capacity=1)
        r2 = create_room(hostel_id=h.id, room_number="102", capacity=2)
        return h, r1, r2

    def test_accommodation_request_to_allotment_workflow(self, setup_data):
        h, r1, r2 = setup_data

        # Student submits request (HM-UC-005, BW-HM-01)
        req = submit_accommodation_request(
            student_user_id=501,
            student_roll_number="24BCS001",
            student_name="Alice Smith",
            academic_year="2026-2027",
            semester="Autumn",
            requested_hostel_id=h.id,
        )
        assert req.status == AccommodationStatus.SUBMITTED.value

        # Super Admin records allotment (HM-UC-006, BW-HM-01)
        allotment = record_allotment_decision(
            super_admin_user_id=1,
            request_id=req.id,
            room_id=r1.id,
        )
        assert allotment.is_active is True
        assert allotment.room_id == r1.id

        r1.refresh_from_db()
        assert r1.current_occupancy == 1

        # Check capacity enforcement (BR-HM-010)
        req2 = submit_accommodation_request(
            student_user_id=502,
            student_roll_number="24BCS002",
            student_name="Bob Jones",
            academic_year="2026-2027",
            semester="Autumn",
        )
        with pytest.raises(RoomCapacityExceededError):
            record_allotment_decision(
                super_admin_user_id=1,
                request_id=req2.id,
                room_id=r1.id,  # r1 is already full!
            )

        # Audit history created (BR-HM-009)
        history = RoomAssignmentHistory.objects.filter(student_user_id=501).first()
        assert history is not None
        assert history.action_type == "allotment"
        assert history.to_room_id == r1.id

    def test_individual_room_exchange(self, setup_data):
        h, r1, r2 = setup_data

        req1 = submit_accommodation_request(student_user_id=501, student_roll_number="24BCS001", student_name="Alice", academic_year="2026", semester="1")
        req2 = submit_accommodation_request(student_user_id=502, student_roll_number="24BCS002", student_name="Bob", academic_year="2026", semester="1")

        allot1 = record_allotment_decision(1, req1.id, r1.id)
        allot2 = record_allotment_decision(1, req2.id, r2.id)

        # Caretaker executes mutual exchange (HM-UC-010)
        a1, a2 = record_individual_room_exchange(
            caretaker_user_id=201,
            hostel_id=h.id,
            student_user_id_1=501,
            target_room_id=r2.id,
            student_user_id_2=502,
            reason="Mutual swap agreed",
        )

        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a1.room_id == r2.id
        assert a2.room_id == r1.id

    def test_reallotment_and_vacation(self, setup_data):
        h, r1, r2 = setup_data
        req = submit_accommodation_request(501, "24BCS001", "Alice", "2026", "1")
        allot = record_allotment_decision(1, req.id, r1.id)

        # Central reallotment (HM-UC-007)
        reallot = record_reallotment(1, allot.id, r2.id, reason="Admin reshuffle")
        assert reallot.room_id == r2.id
        r1.refresh_from_db()
        r2.refresh_from_db()
        assert r1.current_occupancy == 0
        assert r2.current_occupancy == 1

        # Vacation (HM-UC-007)
        vacated = record_room_vacation(1, allot.id, vacation_reason="Graduated")
        assert vacated.is_active is False
        assert vacated.vacated_at is not None
        r2.refresh_from_db()
        assert r2.current_occupancy == 0


@pytest.mark.django_db
class TestLeaveAndAttendanceService:
    def test_attendance_batch_recording(self):
        h = create_hostel("Hall A", "HA")
        records = [
            {"student_user_id": 501, "student_roll_number": "24BCS001", "status": "present"},
            {"student_user_id": 502, "student_roll_number": "24BCS002", "status": "absent"},
        ]
        saved = record_attendance_batch(201, h.id, date.today(), records)
        assert len(saved) == 2
        assert AttendanceRecord.objects.filter(hostel=h).count() == 2

    def test_leave_submission_and_decision(self):
        h = create_hostel("Hall B", "HB")
        today = date.today()

        leave = submit_leave_request(
            student_user_id=501,
            student_roll_number="24BCS001",
            student_name="Alice",
            hostel_id=h.id,
            leave_type="home",
            start_date=today,
            end_date=today + timedelta(days=3),
            reason="Family function",
        )
        assert leave.status == LeaveStatus.SUBMITTED.value

        approved = record_leave_decision(201, leave.id, "approved", remarks="Granted")
        assert approved.status == LeaveStatus.APPROVED.value
        assert approved.decision_by_user_id == 201

        # Attendance auto-marked on_leave
        att = AttendanceRecord.objects.filter(student_user_id=501, date=today).first()
        assert att is not None
        assert att.status == AttendanceStatus.ON_LEAVE.value


@pytest.mark.django_db
class TestComplaintsAndGuestRooms:
    def test_complaint_lifecycle_and_escalation(self):
        h = create_hostel("Hall C", "HC")
        comp = submit_complaint(
            student_user_id=501,
            student_roll_number="24BCS001",
            student_name="Alice",
            hostel_id=h.id,
            category="electrical",
            title="Fan regulator broken",
            description="Room 102 fan does not rotate.",
        )
        assert comp.status == ComplaintStatus.SUBMITTED.value

        # Escalation to warden (BW-HM-05, CW-HM-02)
        escalated = update_complaint_status(
            handler_user_id=201,
            complaint_id=comp.id,
            status="escalated",
            escalate_to_warden=True,
            escalation_reason="Specialist contractor needed",
        )
        assert escalated.escalated_to_warden is True
        assert escalated.status == ComplaintStatus.ESCALATED.value

        # Resolve
        resolved = update_complaint_status(
            handler_user_id=101,
            complaint_id=comp.id,
            status="resolved",
            action_taken="Replaced regulator",
        )
        assert resolved.status == ComplaintStatus.RESOLVED.value
        assert resolved.resolved_at is not None

    def test_guest_room_booking_workflow(self):
        h = create_hostel("Hall D", "HD")
        today = date.today()
        booking = submit_guest_room_request(
            student_user_id=501,
            student_roll_number="24BCS001",
            student_name="Alice",
            hostel_id=h.id,
            guest_name="Mr. Smith",
            guest_relation="Father",
            guest_gender="Male",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            number_of_guests=1,
        )
        assert booking.status == GuestRoomStatus.REQUESTED.value

        approved = record_guest_room_decision(201, booking.id, "approved", remarks="Confirmed")
        assert approved.status == GuestRoomStatus.APPROVED.value


@pytest.mark.django_db
class TestFinesInventoryAndNotices:
    def test_fine_recording_and_mandatory_fields(self):
        h = create_hostel("Hall E", "HE")

        # Missing reason fails under BR-HM-025
        with pytest.raises(MandatoryFieldError):
            record_fine(201, h.id, 501, "24BCS001", "Alice", reason="", amount=500, date_val=date.today())

        fine = record_fine(
            201, h.id, 501, "24BCS001", "Alice",
            reason="Damaged table in reading room",
            amount=750,
            date_val=date.today(),
            fine_type="damage",
        )
        assert fine.id is not None
        assert fine.amount == Decimal("750")

    def test_inventory_and_audit_log(self):
        h = create_hostel("Hall F", "HF")
        item = create_or_update_inventory_item(
            user_id=201,
            hostel_id=h.id,
            item_name="Study Chair",
            category="furniture",
            total_quantity=50,
            in_use_quantity=45,
            condition="good",
        )
        assert item.available_quantity == 5

        # Audit log written (BR-HM-027)
        assert InventoryAuditLog.objects.filter(item=item).count() == 1

        # Update item
        updated = create_or_update_inventory_item(
            user_id=201,
            hostel_id=h.id,
            item_name="Study Chair",
            total_quantity=50,
            in_use_quantity=48,
            condition="fair",
            item_id=item.id,
        )
        assert updated.available_quantity == 2
        assert InventoryAuditLog.objects.filter(item=item).count() == 2

    def test_notice_publishing(self):
        h = create_hostel("Hall G", "HG")
        notice = publish_notice(
            publisher_user_id=101,
            publisher_role="warden",
            title="Hostel Meeting",
            body="All residents are requested to attend the floor meeting at 7 PM.",
            hostel_id=h.id,
            is_pinned=True,
        )
        assert notice.id is not None
        assert notice.is_pinned is True

    def test_operational_report_generation(self):
        h = create_hostel("Hall H", "HH")
        create_room(h.id, "101", capacity=2)
        rep = generate_operational_report("occupancy", hostel_id=h.id)
        assert rep["report_type"] == "occupancy"
        assert rep["summary"]["total_capacity"] == 2
