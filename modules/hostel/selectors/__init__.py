"""Hostel Management query selectors."""

from datetime import date
from django.db.models import Count, Q
from ..models import (
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


def get_user_assigned_hostel_ids(user_id: int, role: str | None = None) -> list[int]:
    """Retrieve IDs of hostels assigned to a specific user (warden or caretaker)."""
    qs = HostelRoleBinding.objects.filter(user_id=user_id, is_active=True)
    if role:
        qs = qs.filter(role=role)
    return list(qs.values_list("hostel_id", flat=True))


def list_hostels(is_active: bool | None = None):
    qs = Hostel.objects.all()
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def get_hostel_by_id(hostel_id: int) -> Hostel | None:
    return Hostel.objects.filter(id=hostel_id).first()


def list_role_bindings(hostel_id: int | None = None, is_active: bool | None = None):
    qs = HostelRoleBinding.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_rooms(hostel_id: int | None = None, floor: int | None = None, is_available: bool | None = None):
    qs = Room.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if floor is not None:
        qs = qs.filter(floor=floor)
    if is_available is not None:
        qs = qs.filter(is_available=is_available)
    return qs


def get_room_by_id(room_id: int) -> Room | None:
    return Room.objects.select_related("hostel").filter(id=room_id).first()


def list_accommodation_requests(hostel_id: int | None = None, student_user_id: int | None = None, status: str | None = None):
    qs = AccommodationRequest.objects.select_related("requested_hostel").all()
    if hostel_id:
        qs = qs.filter(requested_hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def list_allotments(hostel_id: int | None = None, student_user_id: int | None = None, is_active: bool | None = True):
    qs = RoomAllotment.objects.select_related("room", "hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_room_assignment_history(student_user_id: int | None = None, room_id: int | None = None):
    qs = RoomAssignmentHistory.objects.select_related("from_room", "to_room").all()
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if room_id:
        qs = qs.filter(Q(from_room_id=room_id) | Q(to_room_id=room_id))
    return qs


def list_attendance(hostel_id: int | None = None, student_user_id: int | None = None, date_val: date | None = None, from_date: date | None = None, to_date: date | None = None):
    qs = AttendanceRecord.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if date_val:
        qs = qs.filter(date=date_val)
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)
    return qs


def list_leave_requests(hostel_id: int | None = None, student_user_id: int | None = None, status: str | None = None):
    qs = LeaveRequest.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def list_complaints(hostel_id: int | None = None, student_user_id: int | None = None, status: str | None = None, escalated_only: bool = False):
    qs = HostelComplaint.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if status:
        qs = qs.filter(status=status)
    if escalated_only:
        qs = qs.filter(escalated_to_warden=True)
    return qs


def list_guest_bookings(hostel_id: int | None = None, student_user_id: int | None = None, status: str | None = None):
    qs = GuestRoomBooking.objects.select_related("hostel", "assigned_room").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def list_extended_stays(hostel_id: int | None = None, student_user_id: int | None = None, status: str | None = None):
    qs = ExtendedStayRequest.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    if status:
        qs = qs.filter(status=status)
    return qs


def list_fines(hostel_id: int | None = None, student_user_id: int | None = None):
    qs = HostelFine.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if student_user_id:
        qs = qs.filter(student_user_id=student_user_id)
    return qs


def list_inventory(hostel_id: int | None = None, category: str | None = None):
    qs = HostelInventoryItem.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if category:
        qs = qs.filter(category=category)
    return qs


def list_inventory_audits(item_id: int | None = None):
    qs = InventoryAuditLog.objects.select_related("item").all()
    if item_id:
        qs = qs.filter(item_id=item_id)
    return qs


def list_staff_assignments(hostel_id: int | None = None, is_active: bool | None = None):
    qs = StaffAssignment.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def list_security_shifts(hostel_id: int | None = None, shift_date: date | None = None):
    qs = SecurityGuardShift.objects.select_related("hostel").all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    if shift_date:
        qs = qs.filter(shift_date=shift_date)
    return qs


def list_notices(hostel_id: int | None = None, is_active: bool = True):
    qs = HostelNotice.objects.select_related("hostel").all()
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if hostel_id:
        # Notices specific to this hostel OR institution-wide (hostel is None)
        qs = qs.filter(Q(hostel_id=hostel_id) | Q(hostel__isnull=True))
    return qs


def list_notifications(user_id: int, is_read: bool | None = None):
    qs = NotificationRecord.objects.filter(recipient_user_id=user_id)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    return qs
