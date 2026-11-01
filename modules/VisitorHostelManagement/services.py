"""Service operations for Visitor Hostel Management System."""
from datetime import date
from decimal import Decimal
from django.utils import timezone
from .models import Booking, Room, Tariff, MealBooking, Bill, InventoryItem, RoleAssignment, Notification
from .domain import compute_cancellation_charge, compute_stay_days, compute_meal_cost, check_date_overlap, is_inventory_low


def send_system_notification(email: str, uid: int | None, ev_type: str, subj: str, msg: str) -> Notification:
    return Notification.objects.create(recipient_email=email, recipient_user_id=uid, event_type=ev_type, subject=subj, message=msg)


def get_applicable_tariff(category: str, room_type: str = "single", check_date: date | None = None) -> Decimal:
    dt = check_date or timezone.now().date()
    t = Tariff.objects.filter(category=category, room_type=room_type, effective_from__lte=dt).order_by("-effective_from").first()
    if t:
        return t.rate_per_day
    defaults = {"A": Decimal("500.00"), "B": Decimal("800.00"), "C": Decimal("1200.00"), "D": Decimal("1500.00")}
    return defaults.get(category, Decimal("1000.00"))


def create_booking(indenter_id: int, visitor_name: str, check_in_date: date, check_out_date: date,
                   visitor_email: str = "", visitor_phone: str = "", visitor_category: str = "A",
                   purpose: str = "", number_of_rooms: int = 1, number_of_occupants: int = 1,
                   billing_responsibility: str = "visitor", is_offline: bool = False) -> Booking:
    if check_out_date <= check_in_date:
        raise ValueError("Check-out date must be after check-in date.")
    ct = RoleAssignment.objects.filter(role="caretaker", is_active=True).first()
    booking = Booking.objects.create(
        indenter_id=indenter_id, visitor_name=visitor_name, visitor_email=visitor_email, visitor_phone=visitor_phone,
        visitor_category=visitor_category, purpose=purpose, check_in_date=check_in_date, check_out_date=check_out_date,
        number_of_rooms=number_of_rooms, number_of_occupants=number_of_occupants, billing_responsibility=billing_responsibility,
        is_offline=is_offline, status="pending", assigned_caretaker_id=ct.user_id if ct else None,
    )
    send_system_notification(visitor_email or "indenter@fusion.local", indenter_id, "booking_created",
                             f"Booking Submitted: #{booking.id}", f"Booking #{booking.id} submitted for {visitor_name}.")
    return booking


def review_booking(booking_id: int, reviewer_id: int, action: str, remarks: str = "") -> Booking:
    b = Booking.objects.get(pk=booking_id)
    if b.status != "pending":
        raise ValueError(f"Cannot review booking in status '{b.status}'.")
    if action == "reject":
        b.status, b.caretaker_remarks = "rejected", remarks
        b.save()
        send_system_notification(b.visitor_email or "indenter@fusion.local", b.indenter_id, "booking_rejected",
                                 f"Booking Rejected: #{b.id}", f"Rejected by caretaker: {remarks}")
    elif action == "forward":
        b.status, b.caretaker_remarks = "forwarded", remarks
        ic = RoleAssignment.objects.filter(role="incharge", is_active=True).first()
        b.assigned_incharge_id = ic.user_id if ic else None
        b.save()
    else:
        raise ValueError("Action must be 'reject' or 'forward'.")
    return b


def decide_booking(booking_id: int, decider_id: int, action: str, remarks: str = "") -> Booking:
    b = Booking.objects.get(pk=booking_id)
    if b.status != "forwarded":
        raise ValueError(f"Cannot decide booking in status '{b.status}'.")
    if action == "approve":
        b.status, b.incharge_remarks = "approved", remarks
        b.save()
        send_system_notification(b.visitor_email or "indenter@fusion.local", b.indenter_id, "booking_approved",
                                 f"Booking Approved: #{b.id}", f"Approved by VH In-Charge.")
    elif action == "reject":
        b.status, b.incharge_remarks = "rejected", remarks
        b.save()
        send_system_notification(b.visitor_email or "indenter@fusion.local", b.indenter_id, "booking_rejected",
                                 f"Booking Rejected: #{b.id}", f"Rejected by VH In-Charge: {remarks}")
    else:
        raise ValueError("Action must be 'approve' or 'reject'.")
    return b


def cancel_booking(booking_id: int, cancelled_by: int, reason: str = "", cancel_date: date | None = None) -> Booking:
    b = Booking.objects.get(pk=booking_id)
    if b.status in ("cancelled", "checked_out"):
        raise ValueError(f"Booking is already in status '{b.status}'.")
    cdate = cancel_date or timezone.now().date()
    rent = get_applicable_tariff(b.visitor_category, check_date=b.check_in_date) * Decimal(str(b.number_of_rooms))
    charge = compute_cancellation_charge(b.check_in_date, cdate, rent)
    b.status, b.cancellation_reason, b.cancellation_charge = "cancelled", reason, charge
    b.save()
    for room in b.rooms.all():
        room.status = "available"
        room.save()
    b.rooms.clear()
    Bill.objects.update_or_create(booking=b, defaults={
        "cancellation_charges": charge, "total_amount": charge,
        "billing_responsibility": b.billing_responsibility, "is_immutable": True
    })
    send_system_notification(b.visitor_email or "indenter@fusion.local", b.indenter_id, "booking_cancelled",
                             f"Booking Cancelled: #{b.id}", f"Booking cancelled. Charge: INR {charge}.")
    return b


def allot_rooms(booking_id: int, room_ids: list[int]) -> Booking:
    b = Booking.objects.get(pk=booking_id)
    if b.status != "approved":
        raise ValueError("Rooms can only be allotted to approved bookings (BR-VH-012).")
    rooms = list(Room.objects.filter(id__in=room_ids))
    if len(rooms) != len(room_ids):
        raise ValueError("One or more room IDs are invalid.")
    for room in rooms:
        for ex in room.bookings.exclude(id=b.id).filter(status__in=["approved", "checked_in"]):
            if check_date_overlap(b.check_in_date, b.check_out_date, ex.check_in_date, ex.check_out_date):
                raise ValueError(f"Room {room.room_number} is booked ({ex.check_in_date} to {ex.check_out_date}).")
    b.rooms.set(rooms)
    return b


def check_in_guest(booking_id: int) -> Booking:
    b = Booking.objects.get(pk=booking_id)
    if b.status != "approved":
        raise ValueError("Only approved bookings can be checked in.")
    if b.rooms.count() == 0:
        raise ValueError("Rooms must be allotted before check-in.")
    b.status, b.actual_check_in = "checked_in", timezone.now()
    b.save()
    b.rooms.all().update(status="occupied")
    return b


def check_out_guest(booking_id: int, verified_by_guest: bool = True) -> Bill:
    b = Booking.objects.get(pk=booking_id)
    if b.status != "checked_in":
        raise ValueError("Only checked-in bookings can be checked out.")
    b.status, b.actual_check_out = "checked_out", timezone.now()
    b.save()
    b.rooms.all().update(status="available")
    stay_days = compute_stay_days(b.check_in_date, b.check_out_date)
    tariff = get_applicable_tariff(b.visitor_category, check_date=b.check_in_date)
    room_rent = tariff * Decimal(str(b.number_of_rooms)) * Decimal(str(stay_days))
    meals_cost = sum((m.cost for m in b.meals.all()), Decimal("0.00"))
    bill, _ = Bill.objects.update_or_create(booking=b, defaults={
        "room_rent": room_rent, "meal_charges": meals_cost, "cancellation_charges": b.cancellation_charge,
        "total_amount": room_rent + meals_cost + b.cancellation_charge, "billing_responsibility": b.billing_responsibility,
        "verified_by_guest": verified_by_guest, "is_immutable": True
    })
    return bill


def book_meal(booking_id: int, meal_date: date, meal_type: str, add_on: str = "none") -> MealBooking:
    b = Booking.objects.get(pk=booking_id)
    if b.status not in ("approved", "checked_in"):
        raise ValueError("Meals can only be booked for approved or checked-in bookings.")
    if not (b.check_in_date <= meal_date <= b.check_out_date):
        raise ValueError("Meal date must be within guest stay duration.")
    return MealBooking.objects.create(booking=b, meal_date=meal_date, meal_type=meal_type, add_on=add_on,
                                      cost=compute_meal_cost(meal_type, add_on))


def settle_bill(bill_id: int) -> Bill:
    bill = Bill.objects.get(pk=bill_id)
    bill.is_settled, bill.settlement_mode, bill.settled_at = True, "cash", timezone.now()
    bill.save()
    return bill


def update_inventory(item_id: int, quantity: int) -> InventoryItem:
    item = InventoryItem.objects.get(pk=item_id)
    item.quantity = quantity
    item.save()
    if is_inventory_low(item.quantity, item.min_threshold):
        ct = RoleAssignment.objects.filter(role="caretaker", is_active=True).first()
        send_system_notification("caretaker@fusion.local", ct.user_id if ct else None, "inventory_threshold_alert",
                                 f"Low Inventory: {item.item_name}", f"Quantity is {item.quantity}.")
    return item


def request_replenishment(item_id: int, quantity: int) -> InventoryItem:
    item = InventoryItem.objects.get(pk=item_id)
    item.replenishment_requested, item.replenishment_qty = True, quantity
    item.save()
    return item


def approve_replenishment(item_id: int) -> InventoryItem:
    item = InventoryItem.objects.get(pk=item_id)
    if not item.replenishment_requested:
        raise ValueError("No replenishment requested for this item.")
    item.quantity += item.replenishment_qty
    item.replenishment_requested, item.replenishment_approved, item.replenishment_qty = False, True, 0
    item.save()
    return item


def reassign_role(role: str, new_user_id: int) -> RoleAssignment:
    if role not in ("caretaker", "incharge"):
        raise ValueError("Role must be 'caretaker' or 'incharge'.")
    today = timezone.now().date()
    RoleAssignment.objects.filter(role=role, is_active=True).update(is_active=False, end_date=today)
    new_assign = RoleAssignment.objects.create(role=role, user_id=new_user_id, is_active=True, start_date=today)
    if role == "caretaker":
        Booking.objects.filter(status__in=["pending", "approved", "checked_in"]).update(assigned_caretaker_id=new_user_id)
    elif role == "incharge":
        Booking.objects.filter(status="forwarded").update(assigned_incharge_id=new_user_id)
    return new_assign
