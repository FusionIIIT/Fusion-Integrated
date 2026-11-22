"""Hostel Management domain services.

Encapsulates business operations, transactions, and state changes (HM-UC-001 to HM-UC-034).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    AllotmentStatus,
    AttendanceStatus,
    ComplaintStatus,
    ExtendedStayCompliance,
    ExtendedStayStatus,
    FineStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
    NotificationEventType,
    RoleBindingType,
    RoomExchangeStatus,
    RoomStatus,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
    HostelDomainError,
    RoomNotAvailableError,
    UnauthorizedHostelAccessError,
)
from modules.hostel.domain.rules import (
    validate_caretaker_access,
    validate_complaint_data,
    validate_fine_fields,
    validate_notice_publication,
    validate_room_capacity,
)
from modules.hostel.domain.state_machine import (
    transition_accommodation_request,
    transition_complaint,
    transition_extended_stay,
    transition_guest_room_booking,
    transition_leave_request,
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
    HostelNotification,
    HostelRoleBinding,
    HostelStaffDutyLog,
    LeaveRequest,
    Room,
    RoomAllotment,
    RoomExchange,
    SecurityGuardShift,
)


def notify_user(recipient_user_id: int, event_type: str, title: str, message: str) -> HostelNotification:
    """Issues HM notification (HM-UC-034, BR-HM-034)."""
    return HostelNotification.objects.create(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        title=title,
        message=message,
    )


# --- 1. Hostel Master & Role Bindings (HM-UC-001, HM-UC-002, HM-UC-003, HM-UC-004) ---


@transaction.atomic
def create_hostel(*, code: str, name: str, gender_type: str = "coed", total_floors: int = 1, capacity: int = 0, description: str = "") -> Hostel:
    return Hostel.objects.create(
        code=code,
        name=name,
        gender_type=gender_type,
        total_floors=total_floors,
        capacity=capacity,
        description=description,
        is_active=True,
    )


@transaction.atomic
def set_hostel_active_status(hostel: Hostel, is_active: bool) -> Hostel:
    hostel.is_active = is_active
    hostel.save(update_fields=["is_active", "updated_at"])
    return hostel


@transaction.atomic
def manage_role_binding(
    *,
    hostel: Hostel,
    user_id: int,
    role: str,
    shift: str = "general",
    is_active: bool = True,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> HostelRoleBinding:
    binding, created = HostelRoleBinding.objects.update_or_create(
        hostel=hostel,
        user_id=user_id,
        role=role,
        defaults={
            "shift": shift,
            "is_active": is_active,
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )
    return binding


# --- 2. Accommodation Requests & Allotment (HM-UC-005, HM-UC-006, HM-UC-007) ---


@transaction.atomic
def submit_accommodation_request(
    *, student_user_id: int, preferred_hostel: Hostel | None = None, academic_year: str = "2026-2027", semester: str = "Regular", preferences: dict | None = None, remarks: str = ""
) -> AccommodationRequest:
    return AccommodationRequest.objects.create(
        student_user_id=student_user_id,
        preferred_hostel=preferred_hostel,
        academic_year=academic_year,
        semester=semester,
        preferences=preferences or {},
        status=AccommodationRequestStatus.SUBMITTED.value,
        remarks=remarks,
    )


@transaction.atomic
def record_allotment_decision(
    *,
    accommodation_request: AccommodationRequest | None = None,
    student_user_id: int,
    hostel: Hostel,
    room: Room,
    allotment_round: str = "Round 1",
    allotted_by_user_id: int | None = None,
    notes: str = "",
) -> RoomAllotment:
    validate_room_capacity(room.current_occupancy, room.capacity, adding=1)

    RoomAllotment.objects.filter(
        student_user_id=student_user_id, status=AllotmentStatus.ACTIVE.value
    ).update(status=AllotmentStatus.VACATED.value, vacated_at=timezone.now())

    allotment = RoomAllotment.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        room=room,
        allotment_round=allotment_round,
        allotted_by_user_id=allotted_by_user_id,
        notes=notes,
        status=AllotmentStatus.ACTIVE.value,
    )

    room.current_occupancy += 1
    if room.current_occupancy >= room.capacity:
        room.status = RoomStatus.OCCUPIED.value
    room.save(update_fields=["current_occupancy", "status", "updated_at"])

    if accommodation_request:
        accommodation_request.status = transition_accommodation_request(
            accommodation_request.status, AccommodationRequestStatus.ALLOTTED.value
        )
        accommodation_request.save(update_fields=["status", "updated_at"])

    notify_user(
        recipient_user_id=student_user_id,
        event_type=NotificationEventType.ROOM_ALLOCATION.value,
        title="Hostel Room Allotted",
        message=f"You have been allotted Room {room.room_number} in {hostel.name}.",
    )
    return allotment


@transaction.atomic
def record_room_vacation(*, allotment: RoomAllotment, actor_user_id: int | None = None) -> RoomAllotment:
    allotment.status = AllotmentStatus.VACATED.value
    allotment.vacated_at = timezone.now()
    allotment.save(update_fields=["status", "vacated_at", "updated_at"])

    room = allotment.room
    if room.current_occupancy > 0:
        room.current_occupancy -= 1
        if room.status == RoomStatus.OCCUPIED.value:
            room.status = RoomStatus.AVAILABLE.value
        room.save(update_fields=["current_occupancy", "status", "updated_at"])

    notify_user(
        recipient_user_id=allotment.student_user_id,
        event_type=NotificationEventType.ROOM_ALLOCATION.value,
        title="Hostel Room Vacation",
        message=f"Formal vacation recorded for Room {room.room_number}.",
    )
    return allotment


@transaction.atomic
def record_room_exchange(
    *,
    hostel: Hostel,
    student_a_user_id: int,
    student_b_user_id: int,
    reason: str = "",
    processed_by_user_id: int | None = None,
) -> RoomExchange:
    allotment_a = RoomAllotment.objects.filter(
        student_user_id=student_a_user_id, hostel=hostel, status=AllotmentStatus.ACTIVE.value
    ).first()
    allotment_b = RoomAllotment.objects.filter(
        student_user_id=student_b_user_id, hostel=hostel, status=AllotmentStatus.ACTIVE.value
    ).first()

    if not allotment_a or not allotment_b:
        raise HostelDomainError("Both students must have active allotments in this hostel to exchange.")

    room_a = allotment_a.room
    room_b = allotment_b.room

    allotment_a.status = AllotmentStatus.EXCHANGED.value
    allotment_a.vacated_at = timezone.now()
    allotment_a.save(update_fields=["status", "vacated_at", "updated_at"])

    allotment_b.status = AllotmentStatus.EXCHANGED.value
    allotment_b.vacated_at = timezone.now()
    allotment_b.save(update_fields=["status", "vacated_at", "updated_at"])

    RoomAllotment.objects.create(
        student_user_id=student_a_user_id,
        hostel=hostel,
        room=room_b,
        allotment_round="Room Exchange",
        allotted_by_user_id=processed_by_user_id,
        status=AllotmentStatus.ACTIVE.value,
    )
    RoomAllotment.objects.create(
        student_user_id=student_b_user_id,
        hostel=hostel,
        room=room_a,
        allotment_round="Room Exchange",
        allotted_by_user_id=processed_by_user_id,
        status=AllotmentStatus.ACTIVE.value,
    )

    exchange = RoomExchange.objects.create(
        hostel=hostel,
        student_a_user_id=student_a_user_id,
        room_a=room_a,
        student_b_user_id=student_b_user_id,
        room_b=room_b,
        status=RoomExchangeStatus.COMPLETED.value,
        reason=reason,
        processed_by_user_id=processed_by_user_id,
    )

    notify_user(student_a_user_id, NotificationEventType.ROOM_ALLOCATION.value, "Room Exchanged", f"Exchanged to Room {room_b.room_number}.")
    notify_user(student_b_user_id, NotificationEventType.ROOM_ALLOCATION.value, "Room Exchanged", f"Exchanged to Room {room_a.room_number}.")
    return exchange


# --- 3. Attendance Management (HM-UC-012) ---


@transaction.atomic
def record_attendance(
    *, hostel: Hostel, student_user_id: int, date_val: date, status: str, recorded_by_user_id: int | None = None, remarks: str = ""
) -> AttendanceRecord:
    record, _ = AttendanceRecord.objects.update_or_create(
        student_user_id=student_user_id,
        date=date_val,
        defaults={
            "hostel": hostel,
            "status": status,
            "recorded_by_user_id": recorded_by_user_id,
            "remarks": remarks,
        },
    )
    return record


# --- 4. Leave Management (HM-UC-014, HM-UC-015, CW-HM-01) ---


@transaction.atomic
def submit_leave_request(
    *, hostel: Hostel, student_user_id: int, leave_type: str, start_date: date, end_date: date, reason: str, destination: str = "", supporting_document: str = ""
) -> LeaveRequest:
    req = LeaveRequest.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        destination=destination,
        supporting_document=supporting_document,
        status=LeaveStatus.SUBMITTED.value,
    )
    notify_user(
        student_user_id,
        NotificationEventType.LEAVE_STATUS.value,
        "Leave Request Submitted",
        f"Your leave request from {start_date} to {end_date} has been submitted.",
    )
    return req


@transaction.atomic
def record_leave_decision(
    *, leave_request: LeaveRequest, decision: str, remarks: str = "", decision_by_user_id: int | None = None
) -> LeaveRequest:
    target_status = transition_leave_request(leave_request.status, decision)
    leave_request.status = target_status
    leave_request.decision_remarks = remarks
    leave_request.decision_by_user_id = decision_by_user_id
    leave_request.decision_at = timezone.now()
    leave_request.save(update_fields=["status", "decision_remarks", "decision_by_user_id", "decision_at", "updated_at"])

    notify_user(
        leave_request.student_user_id,
        NotificationEventType.LEAVE_STATUS.value,
        f"Leave Request {target_status.capitalize()}",
        f"Your leave request has been {target_status}. Remarks: {remarks}",
    )
    return leave_request


# --- 5. Complaint Management (HM-UC-017, HM-UC-018, CW-HM-02) ---


@transaction.atomic
def submit_complaint(
    *, hostel: Hostel, student_user_id: int, category: str, description: str, room: Room | None = None, attachment: str = ""
) -> HostelComplaint:
    validate_complaint_data(category, description)
    complaint = HostelComplaint.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        category=category,
        description=description,
        room=room,
        attachment=attachment,
        status=ComplaintStatus.SUBMITTED.value,
    )
    notify_user(
        student_user_id,
        NotificationEventType.COMPLAINT_STATUS.value,
        "Complaint Submitted",
        f"Your complaint regarding {category} has been registered.",
    )
    return complaint


@transaction.atomic
def update_complaint_status(
    *, complaint: HostelComplaint, status: str, action_taken: str = "", actor_user_id: int | None = None, escalate: bool = False
) -> HostelComplaint:
    if escalate:
        status = ComplaintStatus.ESCALATED.value
    target_status = transition_complaint(complaint.status, status)
    complaint.status = target_status
    if action_taken:
        complaint.action_taken = action_taken
    complaint.handled_by_user_id = actor_user_id

    if target_status == ComplaintStatus.RESOLVED.value:
        complaint.resolved_at = timezone.now()
    elif target_status == ComplaintStatus.ESCALATED.value:
        complaint.escalated_at = timezone.now()
        complaint.escalated_to_user_id = actor_user_id

    complaint.save()

    notify_user(
        complaint.student_user_id,
        NotificationEventType.COMPLAINT_STATUS.value,
        f"Complaint Updated: {target_status.capitalize()}",
        f"Your complaint has been marked as {target_status}.",
    )
    return complaint


# --- 6. Guest Room Booking (HM-UC-020, HM-UC-021, CW-HM-03) ---


@transaction.atomic
def submit_guest_room_booking(
    *, hostel: Hostel, student_user_id: int, guest_name: str, guest_relation: str, guest_contact: str, check_in_date: date, check_out_date: date, room: Room | None = None
) -> GuestRoomBooking:
    booking = GuestRoomBooking.objects.create(
        hostel=hostel,
        room=room,
        student_user_id=student_user_id,
        guest_name=guest_name,
        guest_relation=guest_relation,
        guest_contact=guest_contact,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        status=GuestRoomBookingStatus.SUBMITTED.value,
    )
    notify_user(
        student_user_id,
        NotificationEventType.GUEST_ROOM_STATUS.value,
        "Guest Room Booking Submitted",
        f"Request for {guest_name} from {check_in_date} to {check_out_date} submitted.",
    )
    return booking


@transaction.atomic
def record_guest_room_decision(
    *, booking: GuestRoomBooking, decision: str, remarks: str = "", decision_by_user_id: int | None = None, room: Room | None = None
) -> GuestRoomBooking:
    target_status = transition_guest_room_booking(booking.status, decision)
    booking.status = target_status
    booking.decision_remarks = remarks
    booking.decision_by_user_id = decision_by_user_id
    booking.decision_at = timezone.now()
    if room:
        booking.room = room
    booking.save()

    notify_user(
        booking.student_user_id,
        NotificationEventType.GUEST_ROOM_STATUS.value,
        f"Guest Room Booking {target_status.capitalize()}",
        f"Your booking has been {target_status}. {remarks}",
    )
    return booking


# --- 7. Extended Stay Management (HM-UC-023, HM-UC-024, HM-UC-025, CW-HM-04) ---


@transaction.atomic
def submit_extended_stay(
    *, hostel: Hostel, student_user_id: int, stay_reason: str, start_date: date, end_date: date
) -> ExtendedStayRequest:
    stay = ExtendedStayRequest.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        stay_reason=stay_reason,
        start_date=start_date,
        end_date=end_date,
        status=ExtendedStayStatus.SUBMITTED.value,
    )
    notify_user(
        student_user_id,
        NotificationEventType.EXTENDED_STAY_STATUS.value,
        "Extended Stay Requested",
        f"Your extended stay request ({stay_reason}) has been submitted.",
    )
    return stay


@transaction.atomic
def record_extended_stay_decision(
    *,
    stay: ExtendedStayRequest,
    decision: str,
    remarks: str = "",
    charge_amount: Decimal | float = 0.0,
    payment_deadline: date | None = None,
    decision_by_user_id: int | None = None,
) -> ExtendedStayRequest:
    target_status = transition_extended_stay(stay.status, decision)
    stay.status = target_status
    stay.decision_remarks = remarks
    stay.decision_by_user_id = decision_by_user_id
    stay.decision_at = timezone.now()
    stay.charge_amount = charge_amount
    stay.payment_deadline = payment_deadline
    if charge_amount > 0:
        stay.compliance_status = ExtendedStayCompliance.PENDING.value
    else:
        stay.compliance_status = ExtendedStayCompliance.EXEMPT.value
    stay.save()

    notify_user(
        stay.student_user_id,
        NotificationEventType.EXTENDED_STAY_STATUS.value,
        f"Extended Stay {target_status.capitalize()}",
        f"Your request has been {target_status}. Remarks: {remarks}",
    )
    return stay


# --- 8. Disciplinary Fines (HM-UC-026, BR-HM-025) ---


@transaction.atomic
def record_hostel_fine(
    *, hostel: Hostel, student_user_id: int, amount: Decimal | float, reason: str, imposed_date: date, issued_by_user_id: int | None = None, remarks: str = ""
) -> HostelFine:
    validate_fine_fields(student_user_id, amount, reason, imposed_date)
    fine = HostelFine.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        amount=amount,
        reason=reason,
        imposed_date=imposed_date,
        status=FineStatus.RECORDED.value,
        issued_by_user_id=issued_by_user_id,
        remarks=remarks,
    )
    notify_user(
        student_user_id,
        NotificationEventType.FINE_RECORDED.value,
        "Hostel Fine Recorded",
        f"A fine of INR {amount} has been imposed for: {reason}.",
    )
    return fine


# --- 9. Notices & Announcements (HM-UC-031, BR-HM-029, BR-HM-030) ---


@transaction.atomic
def publish_notice(
    *, hostel: Hostel | None, title: str, content: str, priority: str = "normal", published_by_user_id: int, is_super_admin: bool = False
) -> HostelNotice:
    notice = HostelNotice.objects.create(
        hostel=hostel,
        title=title,
        content=content,
        priority=priority,
        published_by_user_id=published_by_user_id,
        is_active=True,
    )
    return notice
