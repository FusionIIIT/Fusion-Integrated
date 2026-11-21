"""Predefined operational reports and summaries (3.12, CFR-HM-035, BR-HM-032)."""

from typing import Any
from django.db.models import Avg, Count, Sum
from ..models import (
    AttendanceRecord,
    ExtendedStayRequest,
    Hostel,
    HostelComplaint,
    HostelFine,
    LeaveRequest,
    Room,
    RoomAllotment,
)


def generate_operational_report(report_type: str, hostel_id: int | None = None) -> dict[str, Any]:
    """Generates predefined summaries and metrics derived from HM records (BR-HM-032)."""
    if report_type == "occupancy":
        # Room utilization and occupancy
        rooms_qs = Room.objects.all()
        if hostel_id:
            rooms_qs = rooms_qs.filter(hostel_id=hostel_id)

        total_capacity = rooms_qs.aggregate(total=Sum("capacity"))["total"] or 0
        total_occupancy = rooms_qs.aggregate(total=Sum("current_occupancy"))["total"] or 0
        available_beds = max(0, total_capacity - total_occupancy)
        utilization_pct = round((total_occupancy / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        hostel_stats = []
        hostels = Hostel.objects.filter(is_active=True)
        if hostel_id:
            hostels = hostels.filter(id=hostel_id)
        for h in hostels:
            h_rooms = rooms_qs.filter(hostel=h)
            h_cap = h_rooms.aggregate(total=Sum("capacity"))["total"] or 0
            h_occ = h_rooms.aggregate(total=Sum("current_occupancy"))["total"] or 0
            hostel_stats.append({
                "hostel_id": h.id,
                "hostel_name": h.name,
                "hostel_code": h.code,
                "total_rooms": h_rooms.count(),
                "capacity": h_cap,
                "occupancy": h_occ,
                "available": max(0, h_cap - h_occ),
                "utilization": round((h_occ / h_cap * 100), 1) if h_cap > 0 else 0.0,
            })

        return {
            "report_type": "occupancy",
            "summary": {
                "total_capacity": total_capacity,
                "total_occupancy": total_occupancy,
                "available_beds": available_beds,
                "utilization_percentage": utilization_pct,
            },
            "hostels": hostel_stats,
        }

    elif report_type == "attendance":
        # Attendance summary
        att_qs = AttendanceRecord.objects.all()
        if hostel_id:
            att_qs = att_qs.filter(hostel_id=hostel_id)

        total_records = att_qs.count()
        present_count = att_qs.filter(status="present").count()
        absent_count = att_qs.filter(status="absent").count()
        leave_count = att_qs.filter(status="on_leave").count()

        return {
            "report_type": "attendance",
            "summary": {
                "total_records": total_records,
                "present": present_count,
                "absent": absent_count,
                "on_leave": leave_count,
                "overall_attendance_pct": round((present_count / total_records * 100), 1) if total_records > 0 else 0.0,
            },
        }

    elif report_type == "complaints":
        # Complaint resolution time and status
        comp_qs = HostelComplaint.objects.all()
        if hostel_id:
            comp_qs = comp_qs.filter(hostel_id=hostel_id)

        total_complaints = comp_qs.count()
        resolved_count = comp_qs.filter(status="resolved").count()
        in_progress_count = comp_qs.filter(status="in_progress").count()
        submitted_count = comp_qs.filter(status="submitted").count()
        escalated_count = comp_qs.filter(escalated_to_warden=True).count()

        category_breakdown = list(
            comp_qs.values("category").annotate(count=Count("id")).order_by("-count")
        )

        return {
            "report_type": "complaints",
            "summary": {
                "total_complaints": total_complaints,
                "resolved": resolved_count,
                "in_progress": in_progress_count,
                "submitted": submitted_count,
                "escalated_to_warden": escalated_count,
                "resolution_rate": round((resolved_count / total_complaints * 100), 1) if total_complaints > 0 else 0.0,
            },
            "by_category": category_breakdown,
        }

    elif report_type == "fines":
        # Fine and disciplinary patterns
        fine_qs = HostelFine.objects.all()
        if hostel_id:
            fine_qs = fine_qs.filter(hostel_id=hostel_id)

        total_fines = fine_qs.count()
        total_amount = fine_qs.aggregate(total=Sum("amount"))["total"] or 0
        paid_amount = fine_qs.filter(is_paid=True).aggregate(total=Sum("amount"))["total"] or 0
        unpaid_amount = fine_qs.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or 0

        type_breakdown = list(
            fine_qs.values("fine_type").annotate(count=Count("id"), amount=Sum("amount")).order_by("-amount")
        )

        return {
            "report_type": "fines",
            "summary": {
                "total_fines": total_fines,
                "total_amount": float(total_amount),
                "paid_amount": float(paid_amount),
                "unpaid_amount": float(unpaid_amount),
            },
            "by_type": type_breakdown,
        }

    elif report_type == "leaves":
        # Leave patterns
        leave_qs = LeaveRequest.objects.all()
        if hostel_id:
            leave_qs = leave_qs.filter(hostel_id=hostel_id)

        total_leaves = leave_qs.count()
        approved = leave_qs.filter(status="approved").count()
        rejected = leave_qs.filter(status="rejected").count()
        pending = leave_qs.filter(status="submitted").count()

        by_type = list(
            leave_qs.values("leave_type").annotate(count=Count("id")).order_by("-count")
        )

        return {
            "report_type": "leaves",
            "summary": {
                "total_requests": total_leaves,
                "approved": approved,
                "rejected": rejected,
                "pending": pending,
            },
            "by_type": by_type,
        }

    else:
        # Cross-Hostel Executive Dashboard Summary
        total_hostels = Hostel.objects.filter(is_active=True).count()
        total_capacity = Room.objects.aggregate(t=Sum("capacity"))["t"] or 0
        total_occupancy = Room.objects.aggregate(t=Sum("current_occupancy"))["t"] or 0
        active_complaints = HostelComplaint.objects.exclude(status="resolved").count()
        pending_leaves = LeaveRequest.objects.filter(status="submitted").count()
        pending_allotments = RoomAllotment.objects.filter(is_active=True).count()

        return {
            "report_type": "dashboard_summary",
            "total_hostels": total_hostels,
            "total_capacity": total_capacity,
            "total_occupancy": total_occupancy,
            "occupancy_rate": round((total_occupancy / total_capacity * 100), 1) if total_capacity > 0 else 0.0,
            "active_complaints": active_complaints,
            "pending_leaves": pending_leaves,
            "active_residents": pending_allotments,
        }
