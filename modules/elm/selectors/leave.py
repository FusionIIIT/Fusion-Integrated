from django.db.models import Exists, OuterRef, QuerySet

from modules.elm.models import LeaveApplication, LeaveApprovalRoute, LeaveBalance


def applications_for(actor) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(employee_id=actor.user_id).order_by("-created_at")


def balances_for(actor, year: int | None = None) -> QuerySet[LeaveBalance]:
    query = LeaveBalance.objects.filter(employee_id=actor.user_id)
    if year is not None:
        query = query.filter(year=year)
    return query.order_by("-year", "category")


def review_queue_for(actor) -> QuerySet[LeaveApplication]:
    assignment = LeaveApprovalRoute.objects.filter(
        employee_id=OuterRef("employee_id"),
        category=OuterRef("category"),
        step_order=OuterRef("current_step_order"),
        stage=OuterRef("current_stage"),
        approver_user_id=actor.user_id,
    )
    return (LeaveApplication.objects.annotate(_assigned=Exists(assignment)).filter(
        status=LeaveApplication.Status.PENDING,
        _assigned=True,
    ).order_by("created_at"))
