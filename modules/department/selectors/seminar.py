"""Scoped querysets for Department module."""
from __future__ import annotations

from django.db.models import QuerySet
from modules.department.models.seminar import (
    SeminarSchedulingRequest,
    GraduateSeminar,
    SeminarSchedulingHistory,
)
from modules.department.models.allocation import (
    ThesisSupervisorAllocation,
    TAAllocation,
)
from modules.department.models.announcement import DepartmentAnnouncement

P_VIEW_ALL = "department.seminar.view_all"


def _has(actor, perm: str) -> bool:
    if not actor:
        return False
    return actor.has_permission(perm) if hasattr(actor, "has_permission") else False


def visible_seminar_requests(actor) -> QuerySet[SeminarSchedulingRequest]:
    """Return requests visible to this actor.

    Admin/HOD holding department.seminar.view_all sees all requests;
    students see only their own.
    """
    qs = SeminarSchedulingRequest.objects.all().order_by("-created_at")
    if not actor:
        return qs.none()
    if _has(actor, P_VIEW_ALL):
        return qs
    return qs.filter(student_id=actor.user_id)


def pending_seminar_requests(actor=None) -> QuerySet[SeminarSchedulingRequest]:
    """Queue of seminar requests awaiting scheduling (OA-UC-53)."""
    return SeminarSchedulingRequest.objects.filter(
        status="AWAITING_SCHEDULING"
    ).order_by("created_at")


def scheduled_seminars(department: str = "") -> QuerySet[GraduateSeminar]:
    """All scheduled seminars ordered by date and time (AFR-OAP-049)."""
    qs = GraduateSeminar.objects.select_related("request").all().order_by("-scheduled_date", "-start_time")
    if department:
        qs = qs.filter(request__department=department)
    return qs


def seminar_history_for_seminar(seminar_id: int) -> QuerySet[SeminarSchedulingHistory]:
    """Audit logs for a particular graduate seminar."""
    return SeminarSchedulingHistory.objects.filter(seminar_id=seminar_id).order_by("-recorded_at")


def visible_ta_allocations(actor=None) -> QuerySet[TAAllocation]:
    """TA allocations list."""
    qs = TAAllocation.objects.all().order_by("-created_at")
    if not actor:
        return qs
    if _has(actor, "department.allocation.manage") or _has(actor, P_VIEW_ALL):
        return qs
    # Students see allocations where they are TA; Faculty see allocations for their course
    return qs.filter(student_id=actor.user_id) | qs.filter(faculty_id=actor.user_id)


def visible_supervisor_allocations(actor=None) -> QuerySet[ThesisSupervisorAllocation]:
    """Thesis supervisor allocations list."""
    qs = ThesisSupervisorAllocation.objects.all().order_by("-created_at")
    if not actor:
        return qs
    if _has(actor, "department.allocation.manage") or _has(actor, P_VIEW_ALL):
        return qs
    return qs.filter(student_id=actor.user_id) | qs.filter(supervisor_id=actor.user_id)


def published_announcements() -> QuerySet[DepartmentAnnouncement]:
    """All published department announcements."""
    return DepartmentAnnouncement.objects.all()
