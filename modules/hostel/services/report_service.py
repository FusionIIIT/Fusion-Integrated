"""Operational reports and analytics summaries (CFR-HM-031, 032, HM-UC-033, BR-HM-032, 033)."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Sum

from modules.hostel.domain.constants import (
    AllotmentStatus,
    AttendanceStatus,
    ComplaintStatus,
    FineStatus,
)
from modules.hostel.models import (
    AttendanceRecord,
    ExtendedStayRequest,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelLeave,
    Room,
    RoomAllotment,
)


def get_hostel_occupancy_report(hostel_id: int | None = None) -> list[dict[str, Any]]:
    """CFR-HM-031, AFR-HM-077: Room occupancy and utilization report."""
    qs = Hostel.objects.filter(is_active=True)
    if hostel_id:
        qs = qs.filter(id=hostel_id)

    report = []
    for h in qs:
        rooms = Room.objects.filter(hostel=h)
        total_capacity = sum(r.capacity for r in rooms)
        total_occupied = sum(r.current_occupancy for r in rooms)
        available_beds = max(0, total_capacity - total_occupied)
        utilization = (
            round((total_occupied / total_capacity) * 100, 1) if total_capacity > 0 else 0.0
        )

        report.append(
            {
                "hostel_id": h.id,
                "hostel_name": h.name,
                "hostel_code": h.code,
                "total_rooms": rooms.count(),
                "total_capacity": total_capacity,
                "total_occupied": total_occupied,
                "available_beds": available_beds,
                "utilization_pct": utilization,
            }
        )
    return report


def get_hostel_attendance_report(
    hostel_id: int | None = None,
) -> dict[str, Any]:
    """CFR-HM-031, AFR-HM-078: Attendance summary."""
    qs = AttendanceRecord.objects.all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    total_records = qs.count()
    present_count = qs.filter(status=AttendanceStatus.PRESENT.value).count()
    absent_count = qs.filter(status=AttendanceStatus.ABSENT.value).count()
    leave_count = qs.filter(status=AttendanceStatus.ON_LEAVE.value).count()

    attendance_pct = round((present_count / total_records) * 100, 1) if total_records > 0 else 0.0

    return {
        "total_attendance_marked": total_records,
        "present_count": present_count,
        "absent_count": absent_count,
        "on_leave_count": leave_count,
        "average_attendance_pct": attendance_pct,
    }


def get_hostel_complaints_report(
    hostel_id: int | None = None,
) -> dict[str, Any]:
    """CFR-HM-031, AFR-HM-080: Complaint resolution report."""
    qs = HostelComplaint.objects.all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    total = qs.count()
    open_count = qs.filter(status=ComplaintStatus.OPEN.value).count()
    in_progress = qs.filter(status=ComplaintStatus.IN_PROGRESS.value).count()
    resolved = qs.filter(status=ComplaintStatus.RESOLVED.value).count()
    escalated = qs.filter(status=ComplaintStatus.ESCALATED.value).count()
    closed = qs.filter(status=ComplaintStatus.CLOSED.value).count()

    category_breakdown = list(qs.values("category").annotate(count=Count("id")).order_by("-count"))

    return {
        "total_complaints": total,
        "open_count": open_count,
        "in_progress_count": in_progress,
        "resolved_count": resolved,
        "escalated_count": escalated,
        "closed_count": closed,
        "category_breakdown": category_breakdown,
    }


def get_hostel_fines_report(
    hostel_id: int | None = None,
) -> dict[str, Any]:
    """CFR-HM-031, AFR-HM-079: Disciplinary fines and payments summary."""
    qs = HostelFine.objects.all()
    if hostel_id:
        qs = qs.filter(hostel_id=hostel_id)

    total_fines = qs.count()
    total_amount = qs.aggregate(s=Sum("amount"))["s"] or 0
    paid_amount = qs.filter(status=FineStatus.PAID.value).aggregate(s=Sum("amount"))["s"] or 0
    pending_amount = qs.filter(status=FineStatus.PENDING.value).aggregate(s=Sum("amount"))["s"] or 0

    return {
        "total_fines_count": total_fines,
        "total_amount": float(total_amount),
        "paid_amount": float(paid_amount),
        "pending_amount": float(pending_amount),
    }


def get_cross_hostel_executive_summary() -> dict[str, Any]:
    """CFR-HM-031, AFR-HM-085: Cross-hostel executive operational summary for Super Admin."""
    hostels_count = Hostel.objects.count()
    active_hostels = Hostel.objects.filter(is_active=True).count()
    rooms_count = Room.objects.count()
    allotted_students = RoomAllotment.objects.filter(status=AllotmentStatus.ACTIVE.value).count()
    open_complaints = HostelComplaint.objects.filter(
        status__in=[ComplaintStatus.OPEN.value, ComplaintStatus.ESCALATED.value]
    ).count()
    pending_leaves = HostelLeave.objects.filter(status="pending").count()
    pending_extended_stays = ExtendedStayRequest.objects.filter(status="pending").count()

    total_capacity = Room.objects.aggregate(s=Sum("capacity"))["s"] or 0
    overall_occupancy = Room.objects.aggregate(s=Sum("current_occupancy"))["s"] or 0
    occupancy_pct = (
        round((overall_occupancy / total_capacity) * 100, 1) if total_capacity > 0 else 0.0
    )

    return {
        "total_hostels": hostels_count,
        "active_hostels": active_hostels,
        "total_rooms": rooms_count,
        "total_capacity": total_capacity,
        "overall_occupancy": overall_occupancy,
        "overall_occupancy_pct": occupancy_pct,
        "active_allotments": allotted_students,
        "open_complaints": open_complaints,
        "pending_leaves": pending_leaves,
        "pending_extended_stays": pending_extended_stays,
    }
