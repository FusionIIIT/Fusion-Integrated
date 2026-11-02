from datetime import date
from django.utils import timezone
try:
    from hostel_management.models import (
        Hostel, HostelRoleBinding, Room, AccommodationRequest,
        RoomAllocationHistory, AttendanceRecord, LeaveRequest,
        HostelComplaint, GuestRoomBooking, ExtendedStayRequest,
        HostelFine, HostelInventory, InventoryLog, SecurityGuardShift,
        HostelNotice, Notification
    )
except ImportError:
    from .models import (
        Hostel, HostelRoleBinding, Room, AccommodationRequest,
        RoomAllocationHistory, AttendanceRecord, LeaveRequest,
        HostelComplaint, GuestRoomBooking, ExtendedStayRequest,
        HostelFine, HostelInventory, InventoryLog, SecurityGuardShift,
        HostelNotice, Notification
    )


# Notification Helper (BR-HM-034 / HM-UC-034)
def send_notification(recipient_id, event_type, message):
    return Notification.objects.create(
        recipient_id=recipient_id,
        event_type=event_type,
        message=message
    )


# 1. Hostel Master & Role Assignment Administration (HM-UC-001 to HM-UC-004)
def create_hostel(name, code, total_capacity=100):
    return Hostel.objects.create(name=name, code=code, total_capacity=total_capacity)


def set_hostel_active(hostel_id, is_active):
    hostel = Hostel.objects.get(id=hostel_id)
    hostel.is_active = is_active
    hostel.save()
    return hostel


def assign_hostel_role(hostel_id, user_id, role, start_date=None, end_date=None):
    if role not in ["warden", "caretaker"]:
        raise ValueError("Role must be 'warden' or 'caretaker'")
    binding, _ = HostelRoleBinding.objects.update_or_create(
        hostel_id=hostel_id,
        user_id=user_id,
        role=role,
        defaults={"is_active": True, "start_date": start_date, "end_date": end_date}
    )
    return binding


def deactivate_hostel_role(binding_id):
    binding = HostelRoleBinding.objects.get(id=binding_id)
    binding.is_active = False
    binding.save()
    return binding


# 2. Room Allocation and Occupancy (HM-UC-005 to HM-UC-011, BW-HM-01)
def create_room(hostel_id, room_number, capacity=2):
    return Room.objects.create(hostel_id=hostel_id, room_number=room_number, capacity=capacity)


def submit_accommodation_request(student_id, hostel_id, preferred_room_type=""):
    req = AccommodationRequest.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        preferred_room_type=preferred_room_type,
        status="submitted"
    )
    send_notification(student_id, "accommodation_submitted", f"Hostel request submitted for hostel #{hostel_id}.")
    return req


def allot_room(request_id, room_id, admin_id):
    req = AccommodationRequest.objects.get(id=request_id)
    room = Room.objects.get(id=room_id)

    # BR-HM-010: Room Capacity Limit Enforcement
    if room.current_occupancy >= room.capacity:
        raise ValueError("Room capacity limit exceeded")

    room.current_occupancy += 1
    if room.current_occupancy >= room.capacity:
        room.status = "full"
    room.save()

    req.status = "allotted"
    req.allotted_room = room
    req.decided_at = timezone.now()
    req.save()

    # BR-HM-009: Room Assignment History Retention
    RoomAllocationHistory.objects.create(
        student_id=req.student_id,
        hostel=req.hostel,
        room=room,
        action="allotment",
        remarks="Initial allotment round"
    )

    send_notification(req.student_id, "room_allotted", f"Room {room.room_number} allotted in {req.hostel.name}.")
    return req


def reallot_room(student_id, current_room_id, new_room_id, admin_id):
    old_room = Room.objects.get(id=current_room_id)
    new_room = Room.objects.get(id=new_room_id)

    if new_room.current_occupancy >= new_room.capacity:
        raise ValueError("New room is at full capacity")

    if old_room.current_occupancy > 0:
        old_room.current_occupancy -= 1
        old_room.status = "available"
        old_room.save()

    new_room.current_occupancy += 1
    if new_room.current_occupancy >= new_room.capacity:
        new_room.status = "full"
    new_room.save()

    RoomAllocationHistory.objects.create(
        student_id=student_id,
        hostel=new_room.hostel,
        room=new_room,
        action="reallotment",
        remarks=f"Reallotted from Room {old_room.room_number}"
    )

    send_notification(student_id, "room_reallotted", f"Reallotted to Room {new_room.room_number}.")
    return new_room


def vacate_room(student_id, room_id, admin_id):
    room = Room.objects.get(id=room_id)
    if room.current_occupancy > 0:
        room.current_occupancy -= 1
        room.status = "available"
        room.save()

    RoomAllocationHistory.objects.create(
        student_id=student_id,
        hostel=room.hostel,
        room=room,
        action="vacation",
        remarks="Room formally vacated"
    )

    send_notification(student_id, "room_vacated", f"Room {room.room_number} formal vacation recorded.")
    return room


def exchange_rooms(student1_id, room1_id, student2_id, room2_id, caretaker_id):
    room1 = Room.objects.get(id=room1_id)
    room2 = Room.objects.get(id=room2_id)

    if room1.hostel_id != room2.hostel_id:
        raise ValueError("Room exchanges must be within the same hostel")

    RoomAllocationHistory.objects.create(
        student_id=student1_id, hostel=room2.hostel, room=room2,
        action="exchange", remarks=f"Exchanged with student {student2_id}"
    )
    RoomAllocationHistory.objects.create(
        student_id=student2_id, hostel=room1.hostel, room=room1,
        action="exchange", remarks=f"Exchanged with student {student1_id}"
    )

    send_notification(student1_id, "room_exchanged", f"Exchanged to Room {room2.room_number}.")
    send_notification(student2_id, "room_exchanged", f"Exchanged to Room {room1.room_number}.")
    return True


# 3. Attendance Management (HM-UC-012, HM-UC-013, HM-UC-036)
def record_student_attendance(student_id, hostel_id, att_date, status, caretaker_id):
    # BR-HM-011: Attendance Record Retention
    record, _ = AttendanceRecord.objects.update_or_create(
        student_id=student_id,
        hostel_id=hostel_id,
        date=att_date,
        defaults={"status": status, "marked_by_id": caretaker_id}
    )
    return record


def get_student_attendance(student_id):
    return AttendanceRecord.objects.filter(student_id=student_id).order_by("-date")


# 4. Leave Management (HM-UC-014 to HM-UC-016, HM-UC-037, BW-HM-02, BW-HM-03, CW-HM-01)
def submit_leave_request(student_id, hostel_id, start_date, end_date, reason, supporting_info=""):
    req = LeaveRequest.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        supporting_info=supporting_info,
        status="submitted"
    )
    send_notification(student_id, "leave_submitted", "Leave request submitted for review.")
    return req


def review_leave_request(leave_id, decision, caretaker_id, note=""):
    if decision not in ["approved", "rejected"]:
        raise ValueError("Decision must be 'approved' or 'rejected'")
    req = LeaveRequest.objects.get(id=leave_id)
    req.status = decision
    req.reviewed_by_id = caretaker_id
    req.decision_note = note
    req.decided_at = timezone.now()
    req.save()

    send_notification(req.student_id, f"leave_{decision}", f"Your leave request has been {decision}.")
    return req


# 5. Complaint Management (HM-UC-017 to HM-UC-019, BW-HM-04, BW-HM-05, CW-HM-02)
def submit_hostel_complaint(student_id, hostel_id, category, description, attachment_url=""):
    # BR-HM-015: Complaint Core Data Capture
    if not category or not description:
        raise ValueError("Complaint category and description are required")
    complaint = HostelComplaint.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        category=category,
        description=description,
        attachment_url=attachment_url,
        status="submitted"
    )
    send_notification(student_id, "complaint_submitted", "Complaint submitted successfully.")
    return complaint


def update_complaint_status(complaint_id, status, action_taken, updater_id):
    if status not in ["resolved", "escalated_to_warden"]:
        raise ValueError("Status must be 'resolved' or 'escalated_to_warden'")
    complaint = HostelComplaint.objects.get(id=complaint_id)
    complaint.status = status
    complaint.action_taken = action_taken
    complaint.updated_by_id = updater_id
    complaint.save()

    send_notification(complaint.student_id, f"complaint_{status}", f"Complaint status updated to {status}.")
    return complaint


# 6. Guest Room Booking (HM-UC-020 to HM-UC-022, BW-HM-06, BW-HM-07, CW-HM-03)
def submit_guest_room_booking(student_id, hostel_id, guest_name, room_number, start_date, end_date):
    booking = GuestRoomBooking.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        guest_name=guest_name,
        room_number=room_number,
        start_date=start_date,
        end_date=end_date,
        status="submitted"
    )
    send_notification(student_id, "guest_booking_submitted", "Guest room booking requested.")
    return booking


def review_guest_room_booking(booking_id, decision, caretaker_id):
    if decision not in ["approved", "rejected"]:
        raise ValueError("Decision must be 'approved' or 'rejected'")
    booking = GuestRoomBooking.objects.get(id=booking_id)
    booking.status = decision
    booking.reviewed_by_id = caretaker_id
    booking.decided_at = timezone.now()
    booking.save()

    send_notification(booking.student_id, f"guest_booking_{decision}", f"Guest room booking {decision}.")
    return booking


# 7. Extended-Stay Management (HM-UC-023 to HM-UC-025, BW-HM-08, BW-HM-09, CW-HM-04)
def submit_extended_stay_request(student_id, hostel_id, start_date, end_date, reason):
    req = ExtendedStayRequest.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="submitted"
    )
    send_notification(student_id, "extended_stay_submitted", "Extended stay request submitted.")
    return req


def record_extended_stay_compliance(request_id, fee_amount, payment_deadline, compliance_status):
    # BR-HM-020 & BR-HM-021: Charge and Compliance Recording
    req = ExtendedStayRequest.objects.get(id=request_id)
    req.fee_amount = fee_amount
    req.payment_deadline = payment_deadline
    req.compliance_status = compliance_status
    req.save()
    return req


def review_extended_stay_request(request_id, decision, warden_id):
    if decision not in ["approved", "rejected"]:
        raise ValueError("Decision must be 'approved' or 'rejected'")
    req = ExtendedStayRequest.objects.get(id=request_id)
    req.status = decision
    req.reviewed_by_id = warden_id
    req.decided_at = timezone.now()
    req.save()

    send_notification(req.student_id, f"extended_stay_{decision}", f"Extended stay request {decision}.")
    return req


# 8. Fine Management (HM-UC-026, HM-UC-027, HM-UC-038)
def record_hostel_fine(student_id, hostel_id, reason, amount, fine_date, caretaker_id):
    # BR-HM-025: Fine Mandatory Data Fields
    if not student_id or not reason or amount is None or not fine_date:
        raise ValueError("Reason, amount, date, and student reference are mandatory for fines")
    fine = HostelFine.objects.create(
        student_id=student_id,
        hostel_id=hostel_id,
        reason=reason,
        amount=amount,
        date=fine_date,
        imposed_by_id=caretaker_id
    )
    send_notification(student_id, "fine_imposed", f"Fine of Rs.{amount} imposed: {reason}.")
    return fine


# 9. Inventory and Staff Coordination (HM-UC-028, HM-UC-029, HM-UC-039)
def update_hostel_inventory(hostel_id, item_name, quantity_change, action, updater_id, condition="good"):
    # BR-HM-027: Inventory Maintenance and Accountability Logging
    item, _ = HostelInventory.objects.get_or_create(
        hostel_id=hostel_id,
        item_name=item_name,
        defaults={"quantity": 0, "condition": condition, "last_updated_by_id": updater_id}
    )
    item.quantity = max(0, item.quantity + quantity_change)
    item.condition = condition
    item.last_updated_by_id = updater_id
    item.save()

    InventoryLog.objects.create(
        inventory=item,
        action=action,
        quantity_change=quantity_change,
        logged_by_id=updater_id
    )
    return item


# 10. Security Guard Shift Management (HM-UC-030)
def schedule_guard_shift(hostel_id, guard_name, shift, shift_date, warden_id):
    return SecurityGuardShift.objects.create(
        hostel_id=hostel_id,
        guard_name=guard_name,
        shift=shift,
        date=shift_date,
        assigned_by_id=warden_id
    )


# 11. Notices and Announcements (HM-UC-031, HM-UC-032)
def publish_hostel_notice(hostel_id, title, content, poster_id, role):
    # BR-HM-029 & BR-HM-030: Notice Publishing and Retention
    notice = HostelNotice.objects.create(
        hostel_id=hostel_id,
        title=title,
        content=content,
        posted_by_id=poster_id,
        posted_by_role=role
    )
    return notice


def get_hostel_notices(hostel_id):
    # BR-HM-031: Notice Board Visibility
    return HostelNotice.objects.filter(hostel_id=hostel_id).order_by("-created_at")


# 12. Reports & Operational Summaries (HM-UC-033, BR-HM-032)
def generate_hostel_summary_report(hostel_id):
    hostel = Hostel.objects.get(id=hostel_id)
    rooms = Room.objects.filter(hostel=hostel)
    total_capacity = sum(r.capacity for r in rooms)
    total_occupancy = sum(r.current_occupancy for r in rooms)
    complaints_count = HostelComplaint.objects.filter(hostel=hostel).count()
    pending_complaints = HostelComplaint.objects.filter(hostel=hostel, status="submitted").count()
    fines_total = sum(f.amount for f in HostelFine.objects.filter(hostel=hostel))

    return {
        "hostel_name": hostel.name,
        "hostel_code": hostel.code,
        "total_rooms": rooms.count(),
        "total_capacity": total_capacity,
        "total_occupancy": total_occupancy,
        "occupancy_rate": f"{(total_occupancy / total_capacity * 100):.1f}%" if total_capacity > 0 else "0.0%",
        "total_complaints": complaints_count,
        "pending_complaints": pending_complaints,
        "total_fines_amount": float(fines_total),
    }
