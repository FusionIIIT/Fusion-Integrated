"""Hostel Management selectors.

Ownership, scoping, and RBAC visibility live here
(BR-HM-001, BR-HM-002, BR-HM-003, BR-HM-005, BR-HM-006, BR-HM-035).
"""

from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from modules.hostel.domain.enums import (
    AllotmentStatus,
    ComplaintStatus,
    LeaveStatus,
    RoleBindingType,
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
    SecurityGuardShift,
)


def is_super_admin(principal) -> bool:
    """Super Admin check."""
    if not principal:
        return False
    return (
        principal.has_permission("hostel.hostel.manage")
        or "Super Admin" in principal.roles
        or "admin" in principal.roles
    )


def get_user_role_binding_hostels(user_id: int, role: str) -> list[int]:
    """Returns active hostel IDs for a user with the specified role."""
    return list(
        HostelRoleBinding.objects.filter(user_id=user_id, role=role, is_active=True).values_list(
            "hostel_id", flat=True
        )
    )


def get_student_active_allotment(student_user_id: int) -> RoomAllotment | None:
    """Returns current active room allotment for a student."""
    return (
        RoomAllotment.objects.filter(
            student_user_id=student_user_id, status=AllotmentStatus.ACTIVE.value
        )
        .select_related("hostel", "room")
        .first()
    )


def get_assigned_hostel_ids(principal) -> list[int]:
    """Returns accessible hostel IDs according to RBAC context (BR-HM-002, BR-HM-003, BR-HM-005)."""
    if is_super_admin(principal):
        return list(Hostel.objects.values_list("id", flat=True))

    user_id = principal.user_id
    hostel_ids = set()

    # Warden role bindings
    if principal.has_permission("hostel.occupancy.view") or principal.has_permission(
        "hostel.leave.oversight"
    ):
        hostel_ids.update(get_user_role_binding_hostels(user_id, RoleBindingType.WARDEN.value))

    # Caretaker role bindings
    if principal.has_permission("hostel.occupancy.manage") or principal.has_permission(
        "hostel.leave.review"
    ):
        hostel_ids.update(get_user_role_binding_hostels(user_id, RoleBindingType.CARETAKER.value))

    # Student active allotment (BR-HM-002)
    if not hostel_ids:
        allotment = get_student_active_allotment(user_id)
        if allotment:
            hostel_ids.add(allotment.hostel_id)

    return list(hostel_ids)


def visible_hostels(principal) -> QuerySet[Hostel]:
    """Hostels visible to the current principal."""
    if is_super_admin(principal):
        return Hostel.objects.all()
    assigned = get_assigned_hostel_ids(principal)
    return Hostel.objects.filter(id__in=assigned, is_active=True)


def visible_rooms(principal, hostel_id: int | None = None) -> QuerySet[Room]:
    """Rooms visible within permitted scope."""
    qs = Room.objects.select_related("hostel")
    if is_super_admin(principal):
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        return qs

    assigned = get_assigned_hostel_ids(principal)
    if hostel_id:
        if hostel_id not in assigned:
            return Room.objects.none()
        return qs.filter(hostel_id=hostel_id)
    return qs.filter(hostel_id__in=assigned)


def visible_accommodation_requests(principal) -> QuerySet[AccommodationRequest]:
    """Accommodation requests visible to principal (HM-UC-005, HM-UC-006)."""
    qs = AccommodationRequest.objects.select_related("preferred_hostel")
    if is_super_admin(principal) or principal.has_permission("hostel.allotment.manage"):
        return qs
    return qs.filter(student_user_id=principal.user_id)


def visible_allotments(principal) -> QuerySet[RoomAllotment]:
    """Room allotments visible to principal (HM-UC-008, HM-UC-011)."""
    qs = RoomAllotment.objects.select_related("hostel", "room")
    if is_super_admin(principal) or principal.has_permission("hostel.allotment.manage"):
        return qs
    if principal.has_permission("hostel.occupancy.view") or principal.has_permission(
        "hostel.occupancy.manage"
    ):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_attendance(principal, date_val: date | None = None) -> QuerySet[AttendanceRecord]:
    """Attendance records visible to principal (HM-UC-012, HM-UC-013, HM-UC-036)."""
    qs = AttendanceRecord.objects.select_related("hostel")
    if date_val:
        qs = qs.filter(date=date_val)
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.attendance.record") or principal.has_permission(
        "hostel.attendance.review"
    ):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_leaves(principal) -> QuerySet[LeaveRequest]:
    """Leave requests visible to principal (HM-UC-014, HM-UC-015, HM-UC-016, HM-UC-037)."""
    qs = LeaveRequest.objects.select_related("hostel")
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.leave.review") or principal.has_permission(
        "hostel.leave.oversight"
    ):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_complaints(principal) -> QuerySet[HostelComplaint]:
    """Hostel complaints visible to principal (HM-UC-017, HM-UC-018, HM-UC-019)."""
    qs = HostelComplaint.objects.select_related("hostel", "room")
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.complaint.manage") or principal.has_permission(
        "hostel.complaint.oversight"
    ):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_guest_bookings(principal) -> QuerySet[GuestRoomBooking]:
    """Guest-room booking requests visible to principal (HM-UC-020, HM-UC-021, HM-UC-022)."""
    qs = GuestRoomBooking.objects.select_related("hostel", "room")
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.guestroom.manage"):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_extended_stays(principal) -> QuerySet[ExtendedStayRequest]:
    """Extended stay requests visible to principal (HM-UC-023, HM-UC-024)."""
    qs = ExtendedStayRequest.objects.select_related("hostel")
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.extendedstay.review"):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_fines(principal) -> QuerySet[HostelFine]:
    """Fines visible to principal (HM-UC-026, HM-UC-027, HM-UC-038)."""
    qs = HostelFine.objects.select_related("hostel")
    if is_super_admin(principal):
        return qs
    if principal.has_permission("hostel.fine.record") or principal.has_permission(
        "hostel.fine.oversight"
    ):
        assigned = get_assigned_hostel_ids(principal)
        return qs.filter(hostel_id__in=assigned)
    return qs.filter(student_user_id=principal.user_id)


def visible_inventory(principal, hostel_id: int | None = None) -> QuerySet[HostelInventoryItem]:
    """Inventory items visible to principal (HM-UC-028)."""
    qs = HostelInventoryItem.objects.select_related("hostel")
    if is_super_admin(principal):
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        return qs
    assigned = get_assigned_hostel_ids(principal)
    if hostel_id:
        if hostel_id not in assigned:
            return HostelInventoryItem.objects.none()
        return qs.filter(hostel_id=hostel_id)
    return qs.filter(hostel_id__in=assigned)


def visible_staff_logs(principal, hostel_id: int | None = None) -> QuerySet[HostelStaffDutyLog]:
    """Staff duty logs visible to principal (HM-UC-029, HM-UC-039)."""
    qs = HostelStaffDutyLog.objects.select_related("hostel")
    if is_super_admin(principal):
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        return qs
    assigned = get_assigned_hostel_ids(principal)
    if hostel_id:
        if hostel_id not in assigned:
            return HostelStaffDutyLog.objects.none()
        return qs.filter(hostel_id=hostel_id)
    return qs.filter(hostel_id__in=assigned)


def visible_security_shifts(
    principal, hostel_id: int | None = None
) -> QuerySet[SecurityGuardShift]:
    """Security guard shifts visible to principal (HM-UC-030)."""
    qs = SecurityGuardShift.objects.select_related("hostel")
    if is_super_admin(principal):
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        return qs
    assigned = get_assigned_hostel_ids(principal)
    if hostel_id:
        if hostel_id not in assigned:
            return SecurityGuardShift.objects.none()
        return qs.filter(hostel_id=hostel_id)
    return qs.filter(hostel_id__in=assigned)


def visible_notices(principal, hostel_id: int | None = None) -> QuerySet[HostelNotice]:
    """Notices visible to principal on the hostel notice board (HM-UC-032, BR-HM-031)."""
    qs = HostelNotice.objects.filter(is_active=True).select_related("hostel")
    if is_super_admin(principal):
        if hostel_id:
            qs = qs.filter(Q(hostel_id=hostel_id) | Q(hostel__isnull=True))
        return qs
    assigned = get_assigned_hostel_ids(principal)
    # Campus-wide notices (hostel is null) or notices for assigned hostels
    return qs.filter(Q(hostel__isnull=True) | Q(hostel_id__in=assigned))


def visible_notifications(principal) -> QuerySet[HostelNotification]:
    """Notifications for the current principal (HM-UC-034)."""
    return HostelNotification.objects.filter(recipient_user_id=principal.user_id)


def generate_hostel_report(hostel_id: int) -> dict:
    """Predefined report / operational summary for a hostel (HM-UC-033, BR-HM-032)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        return {}

    rooms = Room.objects.filter(hostel_id=hostel_id)
    total_rooms = rooms.count()
    total_capacity = sum(r.capacity for r in rooms)
    current_occupancy = sum(r.current_occupancy for r in rooms)
    occupancy_rate = (
        round((current_occupancy / total_capacity * 100), 1) if total_capacity > 0 else 0.0
    )

    pending_leaves = LeaveRequest.objects.filter(
        hostel_id=hostel_id, status=LeaveStatus.SUBMITTED.value
    ).count()

    open_complaints = (
        HostelComplaint.objects.filter(hostel_id=hostel_id)
        .exclude(status=ComplaintStatus.RESOLVED.value)
        .count()
    )

    escalated_complaints = HostelComplaint.objects.filter(
        hostel_id=hostel_id, status=ComplaintStatus.ESCALATED.value
    ).count()

    total_fines_recorded = HostelFine.objects.filter(hostel_id=hostel_id).count()

    active_inventory_items = HostelInventoryItem.objects.filter(hostel_id=hostel_id).count()

    return {
        "hostel_id": hostel.id,
        "hostel_name": hostel.name,
        "hostel_code": hostel.code,
        "total_rooms": total_rooms,
        "total_capacity": total_capacity,
        "current_occupancy": current_occupancy,
        "occupancy_rate_percent": occupancy_rate,
        "pending_leave_requests": pending_leaves,
        "open_complaints": open_complaints,
        "escalated_complaints": escalated_complaints,
        "total_fines_recorded": total_fines_recorded,
        "active_inventory_items": active_inventory_items,
    }
