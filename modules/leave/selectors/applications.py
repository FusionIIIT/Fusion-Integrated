"""Application query selectors with ownership and scope filtering."""

from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.leave.models import LeaveActionLog, LeaveApplication


def visible_applications(
    principal,
    status: str | None = None,
    leave_type: str | None = None,
) -> QuerySet[LeaveApplication]:
    """QuerySet of applications visible to the caller based on role & scope."""
    qs = LeaveApplication.objects.all().order_by("-created_at")

    if principal.has_any_permission("leave.request.view", "leave.request.approve"):
        # Staff/HOD with view permission can see scoped applications
        pass
    else:
        # Regular employee sees only own applications
        qs = qs.filter(applicant_user_id=principal.user_id)

    if status:
        qs = qs.filter(status=status)
    if leave_type:
        qs = qs.filter(leave_type=leave_type)

    return qs


def get_application_or_404(application_id: int, principal=None) -> LeaveApplication:
    """Retrieve an application, ensuring visibility or raising NotFoundError."""
    try:
        app = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError(f"Leave application #{application_id} not found.") from None

    if (
        principal
        and not principal.has_any_permission("leave.request.view", "leave.request.approve")
        and (
            app.applicant_user_id != principal.user_id
            and app.substitute_user_id != principal.user_id
        )
    ):
        raise NotFoundError(f"Leave application #{application_id} not found.")

    return app


def list_application_logs(application_id: int) -> QuerySet[LeaveActionLog]:
    return LeaveActionLog.objects.filter(application_id=application_id).order_by("created_at")


def list_active_leaves_for_user(user_id: int) -> QuerySet[LeaveApplication]:
    return LeaveApplication.objects.filter(
        applicant_user_id=user_id,
        status__in=[
            "APPROVED",
            "AWAITING_SUBSTITUTE",
            "AWAITING_UNIT_HEAD",
            "AWAITING_ESTABLISHMENT",
            "AWAITING_SANCTION",
        ],
    )
