"""Scoping selectors for row-level authorization in Hostel Management.

Returns querysets narrowed by the caller's role, never 403 on single gets.
"""
from django.db.models import QuerySet

from modules.hostel.models import (
    AccommodationRequest,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelNotice,
    HostelRoleBinding,
    LeaveRequest,
)


def visible_hostels(user, active_role: str) -> QuerySet[Hostel]:
    if active_role in ("Super Admin", "admin"):
        return Hostel.objects.all()
    if active_role in ("warden", "caretaker"):
        bindings = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        )
        return Hostel.objects.filter(id__in=bindings.values_list("hostel_id", flat=True))
    # Student sees active hostels
    return Hostel.objects.filter(is_active=True)


def visible_accommodations(user, active_role: str) -> QuerySet[AccommodationRequest]:
    if active_role in ("Super Admin", "admin"):
        return AccommodationRequest.objects.all()
    return AccommodationRequest.objects.filter(user_id=user.id)


def visible_leaves(user, active_role: str) -> QuerySet[LeaveRequest]:
    if active_role in ("Super Admin", "admin"):
        return LeaveRequest.objects.all()
    if active_role in ("warden", "caretaker"):
        hostel_ids = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        ).values_list("hostel_id", flat=True)
        return LeaveRequest.objects.filter(hostel_id__in=hostel_ids)
    return LeaveRequest.objects.filter(user_id=user.id)


def visible_complaints(user, active_role: str) -> QuerySet[HostelComplaint]:
    if active_role in ("Super Admin", "admin"):
        return HostelComplaint.objects.all()
    if active_role in ("warden", "caretaker"):
        hostel_ids = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        ).values_list("hostel_id", flat=True)
        return HostelComplaint.objects.filter(hostel_id__in=hostel_ids)
    return HostelComplaint.objects.filter(user_id=user.id)


def visible_guest_bookings(user, active_role: str) -> QuerySet[GuestRoomBooking]:
    if active_role in ("Super Admin", "admin"):
        return GuestRoomBooking.objects.all()
    if active_role in ("warden", "caretaker"):
        hostel_ids = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        ).values_list("hostel_id", flat=True)
        return GuestRoomBooking.objects.filter(hostel_id__in=hostel_ids)
    return GuestRoomBooking.objects.filter(user_id=user.id)


def visible_extended_stays(user, active_role: str) -> QuerySet[ExtendedStayRequest]:
    if active_role in ("Super Admin", "admin"):
        return ExtendedStayRequest.objects.all()
    if active_role in ("warden", "caretaker"):
        hostel_ids = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        ).values_list("hostel_id", flat=True)
        return ExtendedStayRequest.objects.filter(hostel_id__in=hostel_ids)
    return ExtendedStayRequest.objects.filter(user_id=user.id)


def visible_fines(user, active_role: str) -> QuerySet[HostelFine]:
    if active_role in ("Super Admin", "admin"):
        return HostelFine.objects.all()
    if active_role in ("warden", "caretaker"):
        hostel_ids = HostelRoleBinding.objects.filter(
            user_id=user.id, role=active_role, is_active=True
        ).values_list("hostel_id", flat=True)
        return HostelFine.objects.filter(hostel_id__in=hostel_ids)
    return HostelFine.objects.filter(user_id=user.id)


def visible_notices(user, active_role: str) -> QuerySet[HostelNotice]:
    return HostelNotice.objects.all().order_by("-created_at")
