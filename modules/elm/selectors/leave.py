from django.db.models import QuerySet
from modules.elm.domain.constants import ApplicationStatus
from modules.elm.models import LeaveApplication, LeaveBalance, Holiday


def get_user_balances(user_id: int, year: int = 2026) -> QuerySet[LeaveBalance]:
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("leave_type")


def get_user_applications(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")


def get_application_by_id(app_id: int) -> LeaveApplication | None:
    try:
        return LeaveApplication.objects.prefetch_related("actions").get(id=app_id)
    except LeaveApplication.DoesNotExist:
        return None


def get_pending_reviews_for_approver(user_id: int, is_authority: bool = False) -> QuerySet[LeaveApplication]:
    """Return applications pending review or sanction."""
    if is_authority:
        return LeaveApplication.objects.filter(
            status__in=[ApplicationStatus.SUBMITTED.value, ApplicationStatus.RECOMMENDED.value]
        ).order_by("-created_at")
    return LeaveApplication.objects.filter(
        status=ApplicationStatus.SUBMITTED.value
    ).order_by("-created_at")


def get_holidays(year: int = 2026) -> QuerySet[Holiday]:
    return Holiday.objects.filter(date__year=year).order_by("date")
