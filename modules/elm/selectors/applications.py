"""Query selectors for Leave Management (ELM).

Reads and scoping logic live here.
"""

from django.db.models import QuerySet

from modules.elm.domain.entities import LeaveInterval
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveCategory


def list_categories() -> QuerySet[LeaveCategory]:
    """Return all active leave categories."""
    return LeaveCategory.objects.filter(is_active=True).order_by("code")


def get_category_by_code(code: str) -> LeaveCategory | None:
    """Return a leave category by its uppercase code."""
    try:
        return LeaveCategory.objects.get(code=code.upper(), is_active=True)
    except LeaveCategory.DoesNotExist:
        return None


def list_user_balances(user_id: int, year: int = 2026) -> QuerySet[LeaveBalance]:
    """Return leave balances for a specific user and year."""
    return LeaveBalance.objects.filter(
        user_id=user_id, year=year
    ).select_related("category").order_by("category__code")


def get_user_balance(
    user_id: int, category: LeaveCategory, year: int = 2026
) -> LeaveBalance | None:
    """Return a single leave balance row for user, category, and year."""
    try:
        return LeaveBalance.objects.get(user_id=user_id, category=category, year=year)
    except LeaveBalance.DoesNotExist:
        return None


def list_applications_for_user(user_id: int) -> QuerySet[LeaveApplication]:
    """Return all leave applications submitted by or substituting for the user."""
    return LeaveApplication.objects.filter(user_id=user_id).select_related(
        "category"
    ).order_by("-created_at")


def get_application_scoped(
    application_id: int, user_id: int, is_approver: bool = False
) -> LeaveApplication | None:
    """Retrieve an application strictly scoped to the requesting user.

    Returns None if the application does not exist or the user lacks ownership/access,
    ensuring callers raise HTTP 404 rather than 403.
    """
    try:
        app = LeaveApplication.objects.select_related("category").get(
            id=application_id
        )
    except LeaveApplication.DoesNotExist:
        return None

    if is_approver:
        return app
    if app.user_id == user_id or app.substitute_id == user_id:
        return app

    return None


def get_active_intervals_for_user(
    user_id: int, exclude_app_id: int | None = None
) -> list[LeaveInterval]:
    """Return intervals of active pending or approved leaves for overlap checking."""
    active_statuses = [
        LeaveApplication.STATUS_PENDING_SUBSTITUTE,
        LeaveApplication.STATUS_SUBMITTED,
        LeaveApplication.STATUS_PENDING_SANCTION,
        LeaveApplication.STATUS_APPROVED,
    ]
    qs = LeaveApplication.objects.filter(
        user_id=user_id, status__in=active_statuses
    )
    if exclude_app_id:
        qs = qs.exclude(id=exclude_app_id)

    return [
        LeaveInterval(
            start_date=app.start_date,
            end_date=app.end_date,
            half_day=app.half_day,
        )
        for app in qs
    ]


def list_pending_approvals(
    user_id: int,
    is_approver: bool = False,
) -> QuerySet[LeaveApplication]:
    """Return applications awaiting action by the current user."""
    from django.db.models import Q

    filters = Q(substitute_id=user_id, status=LeaveApplication.STATUS_PENDING_SUBSTITUTE)
    if is_approver:
        filters |= Q(
            status__in=[
                LeaveApplication.STATUS_SUBMITTED,
                LeaveApplication.STATUS_PENDING_SANCTION,
            ]
        )

    return LeaveApplication.objects.filter(filters).select_related(
        "category"
    ).order_by("-created_at")
