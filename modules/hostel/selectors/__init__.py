"""Hostel selectors for RBAC-scoped and filtered data access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

from modules.hostel.models import (
    AccommodationRequest,
    AttendanceRecord,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelInventory,
    HostelLeave,
    HostelNotice,
    HostelNotification,
    HostelRoleBinding,
    HostelStaff,
    Room,
    RoomAllotment,
    SecurityShift,
)

if TYPE_CHECKING:
    from fusion_auth.principal import Principal


def get_assigned_hostel_ids(principal: Principal) -> list[int]:
    """Return hostel IDs assigned to this warden or caretaker."""
    return list(
        HostelRoleBinding.objects.filter(user_id=principal.user_id, is_active=True).values_list(
            "hostel_id", flat=True
        )
    )


def is_super_admin(principal: Principal) -> bool:
    """Check if principal possesses institution-wide administration privileges."""
    return (
        principal.has_permission("hostel.report.view_institution")
        or principal.has_permission("hostel.hostel.manage")
        or "super_admin" in principal.roles
        or "admin" in principal.roles
    )


def visible_hostels(principal: Principal) -> QuerySet[Hostel]:
    """CFR-HM-001, CFR-HM-036: Scoped hostel queryset."""
    if is_super_admin(principal):
        return Hostel.objects.all()

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return Hostel.objects.filter(id__in=assigned_ids)

    # Students see active hostels
    return Hostel.objects.filter(is_active=True)


def visible_rooms(principal: Principal, hostel_id: int | None = None) -> QuerySet[Room]:
    """CFR-HM-006, 008, 034: Scoped rooms."""
    qs = Room.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    # Students see rooms in active hostels
    return qs.filter(hostel__is_active=True)


def visible_accommodation_requests(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[AccommodationRequest]:
    """CFR-HM-003, CFR-HM-035: Scoped accommodation requests."""
    qs = AccommodationRequest.objects.select_related("preferred_hostel")
    if hostel_id:
        qs = qs.filter(preferred_hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(Q(preferred_hostel_id__in=assigned_ids) | Q(preferred_hostel__isnull=True))

    # Student only sees their own requests
    return qs.filter(student_user_id=principal.user_id)


def visible_allotments(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[RoomAllotment]:
    """CFR-HM-004, 005, 035: Scoped room allotments."""
    qs = RoomAllotment.objects.select_related("hostel", "room")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    # Student only sees their own allotments
    return qs.filter(student_user_id=principal.user_id)


def visible_attendance(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[AttendanceRecord]:
    """CFR-HM-009, 010: Scoped attendance records."""
    qs = AttendanceRecord.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_leaves(principal: Principal, hostel_id: int | None = None) -> QuerySet[HostelLeave]:
    """CFR-HM-012..014: Scoped leave requests."""
    qs = HostelLeave.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_complaints(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[HostelComplaint]:
    """CFR-HM-015..018: Scoped complaints."""
    qs = HostelComplaint.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_guest_room_bookings(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[GuestRoomBooking]:
    """CFR-HM-019..021: Scoped guest bookings."""
    qs = GuestRoomBooking.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_extended_stays(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[ExtendedStayRequest]:
    """CFR-HM-022..024: Scoped extended stays."""
    qs = ExtendedStayRequest.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_fines(principal: Principal, hostel_id: int | None = None) -> QuerySet[HostelFine]:
    """CFR-HM-025..027: Scoped fines."""
    qs = HostelFine.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    return qs.filter(student_user_id=principal.user_id)


def visible_inventory(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[HostelInventory]:
    """CFR-HM-028: Scoped inventory items."""
    qs = HostelInventory.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    return qs.filter(hostel_id__in=assigned_ids)


def visible_staff(principal: Principal, hostel_id: int | None = None) -> QuerySet[HostelStaff]:
    """CFR-HM-028: Scoped operational staff."""
    qs = HostelStaff.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    return qs.filter(hostel_id__in=assigned_ids)


def visible_security_shifts(
    principal: Principal, hostel_id: int | None = None
) -> QuerySet[SecurityShift]:
    """CFR-HM-029: Scoped security guard shifts."""
    qs = SecurityShift.objects.select_related("hostel")
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    return qs.filter(hostel_id__in=assigned_ids)


def visible_notices(principal: Principal, hostel_id: int | None = None) -> QuerySet[HostelNotice]:
    """CFR-HM-030: Scoped notices."""
    qs = HostelNotice.objects.select_related("hostel").filter(is_active=True)
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    if is_super_admin(principal):
        return qs

    assigned_ids = get_assigned_hostel_ids(principal)
    if assigned_ids:
        return qs.filter(hostel_id__in=assigned_ids)

    # For students: filter by their assigned hostel
    active_allotment = RoomAllotment.objects.filter(
        student_user_id=principal.user_id, status="active"
    ).first()
    if active_allotment:
        return qs.filter(Q(hostel_id=active_allotment.hostel_id) | Q(target_audience="all"))

    return qs.filter(target_audience="all")


def visible_notifications(principal: Principal) -> QuerySet[HostelNotification]:
    """CFR-HM-033: Personal in-app alerts."""
    return HostelNotification.objects.filter(recipient_user_id=principal.user_id)
