"""Row visibility, decided in one place. Out of scope is absent, so a detail read is a 404."""

from __future__ import annotations

from django.db.models import Q, QuerySet

from modules.department.domain import state_machine as sm
from modules.department.domain.roles import (
    CENTRAL,
    DEPT_ADMIN,
    FACULTY,
    HOD,
    STUDENT,
    ActorContext,
)
from modules.department.models import (
    Announcement,
    Department,
    Feedback,
    InventoryItem,
    LabResource,
    OfficialChange,
    ProfileRecord,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)

OFFICE = (HOD, DEPT_ADMIN)


def _in_department(qs: QuerySet, ctx: ActorContext, field: str = "department__code") -> QuerySet:
    if ctx.department is None:
        return qs.none()
    return qs.filter(**{field: ctx.department})


def departments_for(ctx: ActorContext) -> QuerySet[Department]:
    qs = Department.objects.all()
    if ctx.role == CENTRAL:
        return qs
    return _in_department(qs, ctx, "code")


def official_changes_for(ctx: ActorContext) -> QuerySet[OfficialChange]:
    qs = OfficialChange.objects.select_related("department")
    return _in_department(qs, ctx) if ctx.role in OFFICE else qs.none()


def announcements_for(ctx: ActorContext) -> QuerySet[Announcement]:
    """BR-DEPT-002: relevance by role, programme and year; the HOD sees all to maintain them."""
    qs = _in_department(Announcement.objects.select_related("department"), ctx)
    if ctx.role == HOD:
        return qs.filter(status__in=(Announcement.ACTIVE, Announcement.HIDDEN))
    if ctx.role not in (STUDENT, FACULTY, DEPT_ADMIN):
        return qs.none()
    relevant = Q(audience_role__in=(ctx.role, "all"))
    if ctx.role == STUDENT:
        relevant &= Q(programme="") | Q(programme=ctx.programme)
        relevant &= Q(batch_year__isnull=True) | Q(batch_year=ctx.batch_year)
    return qs.filter(status=Announcement.ACTIVE).filter(relevant | Q(author_id=ctx.user_id))


def inventory_items_for(ctx: ActorContext) -> QuerySet[InventoryItem]:
    qs = InventoryItem.objects.select_related("department")
    return _in_department(qs, ctx) if ctx.role in (FACULTY, *OFFICE) else qs.none()


def stock_movements_for(ctx: ActorContext) -> QuerySet[StockMovement]:
    qs = StockMovement.objects.select_related("item")
    return _in_department(qs, ctx, "item__department__code") if ctx.role in OFFICE else qs.none()


def stock_requests_for(ctx: ActorContext) -> QuerySet[StockRequest]:
    """BR-DEPT-012 with Q12: Faculty see their own requests; the office sees the department's."""
    qs = StockRequest.objects.select_related("item", "department")
    if ctx.role == FACULTY and ctx.user_id is not None:
        return _in_department(qs, ctx).filter(requester_id=ctx.user_id)
    if ctx.role in OFFICE:
        return _in_department(qs, ctx)
    return qs.none()


def feedback_for(ctx: ActorContext) -> QuerySet[Feedback]:
    """BR-DEPT-017, BR-DEPT-018: submitter, Dept_Admin, and HOD only after initial review."""
    qs = Feedback.objects.select_related("department")
    if ctx.role in (STUDENT, FACULTY) and ctx.user_id is not None:
        return qs.filter(submitter_id=ctx.user_id)
    if ctx.role == DEPT_ADMIN:
        return _in_department(qs, ctx)
    if ctx.role == HOD:
        return _in_department(qs, ctx).exclude(status=sm.FEEDBACK_NEW)
    return qs.none()


def timetable_for(ctx: ActorContext) -> QuerySet[TimetableSlot]:
    """AFR-DEPT-037: a student sees the slots for their programme and batch."""
    qs = _in_department(TimetableSlot.objects.select_related("department"), ctx)
    if ctx.role == STUDENT:
        return qs.filter(Q(programme="") | Q(programme=ctx.programme)).filter(
            Q(batch_year__isnull=True) | Q(batch_year=ctx.batch_year)
        )
    return qs if ctx.role in (FACULTY, *OFFICE) else qs.none()


def lab_resources_for(ctx: ActorContext) -> QuerySet[LabResource]:
    qs = LabResource.objects.select_related("department")
    return _in_department(qs, ctx) if ctx.role in (FACULTY, *OFFICE) else qs.none()


def profiles_for(ctx: ActorContext) -> QuerySet[ProfileRecord]:
    """BR-DEPT-019: students see peers and faculty only; the office also sees inactive records."""
    qs = _in_department(ProfileRecord.objects.select_related("department"), ctx)
    if ctx.role in OFFICE:
        return qs
    if ctx.role == STUDENT:
        return qs.filter(is_active=True, kind__in=("student", "faculty"))
    if ctx.role == FACULTY:
        return qs.filter(is_active=True)
    return qs.none()


def tenures_for(ctx: ActorContext) -> QuerySet[RoleTenure]:
    qs = RoleTenure.objects.select_related("department")
    if ctx.role == CENTRAL:
        return qs
    return _in_department(qs, ctx) if ctx.role in OFFICE else qs.none()
