"""Transactional services for Hostel Management.

All aggregate state transitions, capacity locking, and audits happen atomically.
"""
from typing import Any
from django.db import transaction
from django.utils import timezone
from modules.hm.models import (
    Hostel,
    HostelRoleBinding,
    Room,
    AccommodationRequest,
    RoomAssignment,
    AttendanceRecord,
    LeaveRequest,
    Complaint,
    ComplaintEvent,
    GuestBooking,
    ExtendedStayRequest,
    FineRecord,
    InventoryItem,
    InventoryEvent,
    GuardShift,
    Notice,
)
from modules.hm.domain.state_machine import (
    validate_room_capacity,
    check_capacity_guard,
    validate_stay_dates,
    transition_state,
    ACCOMMODATION_TRANSITIONS,
    LEAVE_TRANSITIONS,
    COMPLAINT_TRANSITIONS,
    GUEST_BOOKING_TRANSITIONS,
    EXTENDED_STAY_TRANSITIONS,
    NOTICE_TRANSITIONS,
)


@transaction.atomic
def create_hostel(*, name: str, code: str, description: str = "") -> Hostel:
    return Hostel.objects.create(name=name, code=code, description=description)


@transaction.atomic
def update_hostel(*, hostel: Hostel, **kwargs: Any) -> Hostel:
    for attr, val in kwargs.items():
        if hasattr(hostel, attr) and val is not None:
            setattr(hostel, attr, val)
    hostel.save()
    return hostel


@transaction.atomic
def assign_hostel_role_binding(
    *, hostel: Hostel, user_id: int, role_kind: str, assigned_by_user_id: int | None = None, valid_from=None, valid_to=None
) -> HostelRoleBinding:
    return HostelRoleBinding.objects.create(
        hostel=hostel,
        user_id=user_id,
        role_kind=role_kind,
        assigned_by_user_id=assigned_by_user_id,
        valid_from=valid_from,
        valid_to=valid_to,
        is_active=True,
    )


@transaction.atomic
def revoke_hostel_role_binding(*, binding: HostelRoleBinding) -> HostelRoleBinding:
    binding.is_active = False
    binding.save(update_fields=["is_active", "updated_at"])
    return binding


@transaction.atomic
def update_room_capacity(*, room_id: int, new_capacity: int) -> Room:
    validate_room_capacity(new_capacity)
    room = Room.objects.select_for_update().get(id=room_id)
    active_count = room.assignments.filter(status="active").count()
    if new_capacity < active_count:
        raise ValueError("Cannot reduce capacity below currently occupied count")
    room.capacity = new_capacity
    room.save(update_fields=["capacity", "updated_at"])
    return room


@transaction.atomic
def submit_accommodation_request(*, user_id: int, hostel: Hostel | None = None, preferred_room_type: str = "", reason: str = "") -> AccommodationRequest:
    return AccommodationRequest.objects.create(
        user_id=user_id,
        hostel=hostel,
        preferred_room_type=preferred_room_type,
        reason=reason,
        status="submitted",
    )


@transaction.atomic
def allot_room_from_request(*, request_id: int, room_id: int, actor_user_id: int) -> RoomAssignment:
    req = AccommodationRequest.objects.select_for_update().get(id=request_id)
    new_status = transition_state(ACCOMMODATION_TRANSITIONS, req.status, "allot", "admin")

    room = Room.objects.select_for_update().get(id=room_id)
    active_count = room.assignments.filter(status="active").count()
    check_capacity_guard(room.capacity, active_count)

    # Deactivate any previous active assignment for this student
    RoomAssignment.objects.filter(user_id=req.user_id, status="active").update(
        status="vacated", effective_to=timezone.now()
    )

    assignment = RoomAssignment.objects.create(
        user_id=req.user_id,
        room=room,
        status="active",
        assigned_by_user_id=actor_user_id,
        reason=f"Allotted from accommodation request #{req.id}",
    )

    req.status = new_status
    req.save(update_fields=["status", "updated_at"])
    return assignment


@transaction.atomic
def vacate_room_assignment(*, assignment_id: int, reason: str = "") -> RoomAssignment:
    assignment = RoomAssignment.objects.select_for_update().get(id=assignment_id)
    if assignment.status != "active":
        raise ValueError("Only active assignments can be vacated")
    assignment.status = "vacated"
    assignment.effective_to = timezone.now()
    assignment.reason = reason or assignment.reason
    assignment.save(update_fields=["status", "effective_to", "reason", "updated_at"])
    return assignment


@transaction.atomic
def exchange_room_assignments(*, assignment_a_id: int, assignment_b_id: int, actor_user_id: int, reason: str = "") -> tuple[RoomAssignment, RoomAssignment]:
    # Lock both assignments and rooms in deterministic ID order to avoid deadlocks
    ids = sorted([assignment_a_id, assignment_b_id])
    a = RoomAssignment.objects.select_for_update().get(id=ids[0])
    b = RoomAssignment.objects.select_for_update().get(id=ids[1])

    if a.status != "active" or b.status != "active":
        raise ValueError("Both assignments must be active to exchange")
    if a.room.hostel_id != b.room.hostel_id:
        raise ValueError("Can only exchange rooms within the same hostel")

    room_a = a.room
    room_b = b.room

    # Mark current as exchanged
    now = timezone.now()
    a.status = "exchanged"
    a.effective_to = now
    a.save()

    b.status = "exchanged"
    b.effective_to = now
    b.save()

    new_a = RoomAssignment.objects.create(
        user_id=a.user_id,
        room=room_b,
        status="active",
        assigned_by_user_id=actor_user_id,
        reason=f"Exchanged with user {b.user_id}. {reason}".strip(),
    )
    new_b = RoomAssignment.objects.create(
        user_id=b.user_id,
        room=room_a,
        status="active",
        assigned_by_user_id=actor_user_id,
        reason=f"Exchanged with user {a.user_id}. {reason}".strip(),
    )
    return new_a, new_b


@transaction.atomic
def record_attendance(*, user_id: int, hostel: Hostel, date, is_present: bool, recorded_by_user_id: int, remarks: str = "") -> AttendanceRecord:
    return AttendanceRecord.objects.create(
        user_id=user_id,
        hostel=hostel,
        date=date,
        is_present=is_present,
        recorded_by_user_id=recorded_by_user_id,
        remarks=remarks,
    )


@transaction.atomic
def submit_leave_request(*, user_id: int, hostel: Hostel, start_date, end_date, reason: str) -> LeaveRequest:
    validate_stay_dates(start_date, end_date)
    return LeaveRequest.objects.create(
        user_id=user_id,
        hostel=hostel,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="submitted",
    )


@transaction.atomic
def decide_leave_request(*, request_id: int, decision: str, decided_by_user_id: int, remarks: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(id=request_id)
    new_status = transition_state(LEAVE_TRANSITIONS, req.status, decision, "caretaker")
    req.status = new_status
    req.decided_by_user_id = decided_by_user_id
    req.decision_remarks = remarks
    req.save(update_fields=["status", "decided_by_user_id", "decision_remarks", "updated_at"])
    return req


@transaction.atomic
def submit_complaint(*, user_id: int, hostel: Hostel, category: str, description: str) -> Complaint:
    complaint = Complaint.objects.create(
        user_id=user_id,
        hostel=hostel,
        category=category,
        description=description,
        status="submitted",
    )
    ComplaintEvent.objects.create(
        complaint=complaint,
        actor_user_id=user_id,
        actor_kind="student",
        event="submitted",
        remarks="Complaint registered",
    )
    return complaint


@transaction.atomic
def record_complaint_event(*, complaint_id: int, event: str, actor_user_id: int, actor_kind: str, remarks: str = "") -> Complaint:
    complaint = Complaint.objects.select_for_update().get(id=complaint_id)
    new_status = transition_state(COMPLAINT_TRANSITIONS, complaint.status, event, actor_kind)
    complaint.status = new_status
    complaint.save(update_fields=["status", "updated_at"])

    ComplaintEvent.objects.create(
        complaint=complaint,
        actor_user_id=actor_user_id,
        actor_kind=actor_kind,
        event=event,
        remarks=remarks,
    )
    return complaint


@transaction.atomic
def submit_guest_booking(*, user_id: int, hostel: Hostel, guest_name: str, relation: str, start_date, end_date) -> GuestBooking:
    validate_stay_dates(start_date, end_date)
    return GuestBooking.objects.create(
        user_id=user_id,
        hostel=hostel,
        guest_name=guest_name,
        relation=relation,
        start_date=start_date,
        end_date=end_date,
        status="submitted",
    )


@transaction.atomic
def decide_guest_booking(*, booking_id: int, decision: str, decided_by_user_id: int, remarks: str = "") -> GuestBooking:
    booking = GuestBooking.objects.select_for_update().get(id=booking_id)
    new_status = transition_state(GUEST_BOOKING_TRANSITIONS, booking.status, decision, "caretaker")
    booking.status = new_status
    booking.decided_by_user_id = decided_by_user_id
    booking.remarks = remarks
    booking.save(update_fields=["status", "decided_by_user_id", "remarks", "updated_at"])
    return booking


@transaction.atomic
def submit_extended_stay(*, user_id: int, hostel: Hostel, start_date, end_date, reason: str) -> ExtendedStayRequest:
    validate_stay_dates(start_date, end_date)
    return ExtendedStayRequest.objects.create(
        user_id=user_id,
        hostel=hostel,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="submitted",
    )


@transaction.atomic
def decide_extended_stay(*, request_id: int, decision: str, decided_by_user_id: int, remarks: str = "") -> ExtendedStayRequest:
    stay = ExtendedStayRequest.objects.select_for_update().get(id=request_id)
    new_status = transition_state(EXTENDED_STAY_TRANSITIONS, stay.status, decision, "warden")
    stay.status = new_status
    stay.decided_by_user_id = decided_by_user_id
    stay.remarks = remarks
    stay.save(update_fields=["status", "decided_by_user_id", "remarks", "updated_at"])
    return stay


@transaction.atomic
def record_fine(*, user_id: int, hostel: Hostel, amount, reason: str, imposed_by_user_id: int) -> FineRecord:
    return FineRecord.objects.create(
        user_id=user_id,
        hostel=hostel,
        amount=amount,
        reason=reason,
        imposed_by_user_id=imposed_by_user_id,
    )


@transaction.atomic
def create_inventory_item(*, hostel: Hostel, name: str, quantity: int = 0, description: str = "", user_id: int | None = None) -> InventoryItem:
    return InventoryItem.objects.create(
        hostel=hostel,
        name=name,
        quantity=quantity,
        description=description,
        updated_by_user_id=user_id,
    )


@transaction.atomic
def update_inventory_item(*, item_id: int, quantity_change: int, reason: str, user_id: int) -> InventoryItem:
    item = InventoryItem.objects.select_for_update().get(id=item_id)
    new_qty = item.quantity + quantity_change
    if new_qty < 0:
        raise ValueError("Inventory quantity cannot be negative")
    item.quantity = new_qty
    item.updated_by_user_id = user_id
    item.save(update_fields=["quantity", "updated_by_user_id", "updated_at"])

    InventoryEvent.objects.create(
        item=item,
        quantity_change=quantity_change,
        reason=reason,
        recorded_by_user_id=user_id,
    )
    return item


@transaction.atomic
def create_guard_shift(*, hostel: Hostel, guard_name: str, shift_date, shift_type: str, notes: str = "") -> GuardShift:
    return GuardShift.objects.create(
        hostel=hostel,
        guard_name=guard_name,
        shift_date=shift_date,
        shift_type=shift_type,
        notes=notes,
    )


@transaction.atomic
def create_notice(*, hostel: Hostel, title: str, content: str) -> Notice:
    return Notice.objects.create(
        hostel=hostel,
        title=title,
        content=content,
        status="draft",
    )


@transaction.atomic
def publish_notice(*, notice_id: int, user_id: int) -> Notice:
    notice = Notice.objects.select_for_update().get(id=notice_id)
    new_status = transition_state(NOTICE_TRANSITIONS, notice.status, "publish", "authority")
    notice.status = new_status
    notice.published_by_user_id = user_id
    notice.published_at = timezone.now()
    notice.save(update_fields=["status", "published_by_user_id", "published_at", "updated_at"])
    return notice


@transaction.atomic
def withdraw_notice(*, notice_id: int) -> Notice:
    notice = Notice.objects.select_for_update().get(id=notice_id)
    new_status = transition_state(NOTICE_TRANSITIONS, notice.status, "withdraw", "authority")
    notice.status = new_status
    notice.save(update_fields=["status", "updated_at"])
    return notice
