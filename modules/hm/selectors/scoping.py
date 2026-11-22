"""Scoped selectors for Hostel Management.

Every list and detail query starts here. Cross-student and cross-hostel access
is isolated according to the caller's principal and role bindings.
Invisible objects return 404.
"""
from typing import Any
from django.db.models import QuerySet
from modules.hm.models import (
    Hostel,
    HostelRoleBinding,
    Room,
    AccommodationRequest,
    RoomAssignment,
    AttendanceRecord,
    LeaveRequest,
    Complaint,
    GuestBooking,
    ExtendedStayRequest,
    FineRecord,
    InventoryItem,
    GuardShift,
    Notice,
)


def get_assigned_hostel_ids_for_user(user_id: int) -> list[int]:
    """Find hostels where the user holds an active role binding (warden/caretaker)."""
    return list(
        HostelRoleBinding.objects.filter(user_id=user_id, is_active=True).values_list("hostel_id", flat=True)
    )


def scope_hostels(principal: Any) -> QuerySet[Hostel]:
    return Hostel.objects.all()


def scope_role_bindings(principal: Any, hostel_id: int | None = None) -> QuerySet[HostelRoleBinding]:
    qs = HostelRoleBinding.objects.all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    return qs


def scope_rooms(principal: Any, hostel_id: int | None = None) -> QuerySet[Room]:
    qs = Room.objects.all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)
    return qs


def scope_accommodation_requests(principal: Any) -> QuerySet[AccommodationRequest]:
    if principal.kind == "student":
        return AccommodationRequest.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return AccommodationRequest.objects.filter(hostel_id__in=assigned_hostels)
    return AccommodationRequest.objects.all()


def scope_room_assignments(principal: Any) -> QuerySet[RoomAssignment]:
    if principal.kind == "student":
        return RoomAssignment.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return RoomAssignment.objects.filter(room__hostel_id__in=assigned_hostels)
    return RoomAssignment.objects.all()


def scope_attendance(principal: Any) -> QuerySet[AttendanceRecord]:
    if principal.kind == "student":
        return AttendanceRecord.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return AttendanceRecord.objects.filter(hostel_id__in=assigned_hostels)
    return AttendanceRecord.objects.all()


def scope_leave_requests(principal: Any) -> QuerySet[LeaveRequest]:
    if principal.kind == "student":
        return LeaveRequest.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return LeaveRequest.objects.filter(hostel_id__in=assigned_hostels)
    return LeaveRequest.objects.all()


def scope_complaints(principal: Any) -> QuerySet[Complaint]:
    if principal.kind == "student":
        return Complaint.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return Complaint.objects.filter(hostel_id__in=assigned_hostels)
    return Complaint.objects.all()


def scope_guest_bookings(principal: Any) -> QuerySet[GuestBooking]:
    if principal.kind == "student":
        return GuestBooking.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return GuestBooking.objects.filter(hostel_id__in=assigned_hostels)
    return GuestBooking.objects.all()


def scope_extended_stays(principal: Any) -> QuerySet[ExtendedStayRequest]:
    if principal.kind == "student":
        return ExtendedStayRequest.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return ExtendedStayRequest.objects.filter(hostel_id__in=assigned_hostels)
    return ExtendedStayRequest.objects.all()


def scope_fines(principal: Any) -> QuerySet[FineRecord]:
    if principal.kind == "student":
        return FineRecord.objects.filter(user_id=principal.user_id)
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return FineRecord.objects.filter(hostel_id__in=assigned_hostels)
    return FineRecord.objects.all()


def scope_inventory(principal: Any) -> QuerySet[InventoryItem]:
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return InventoryItem.objects.filter(hostel_id__in=assigned_hostels)
    return InventoryItem.objects.all()


def scope_guard_shifts(principal: Any) -> QuerySet[GuardShift]:
    assigned_hostels = get_assigned_hostel_ids_for_user(principal.user_id)
    if assigned_hostels:
        return GuardShift.objects.filter(hostel_id__in=assigned_hostels)
    return GuardShift.objects.all()


def scope_notices(principal: Any) -> QuerySet[Notice]:
    if principal.kind == "student":
        return Notice.objects.filter(status="published")
    return Notice.objects.all()
