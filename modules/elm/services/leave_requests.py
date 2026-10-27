from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import (
    LeaveCategory,
    LeaveDayPart,
    LeaveRequest,
    LeaveRequestEvent,
    LeaveStatus,
)


def ensure_no_overlap(
    *,
    user_id: int,
    category: str,
    start_date,
    end_date,
    day_part: str,
) -> None:
    active_requests = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=(LeaveStatus.PENDING, LeaveStatus.APPROVED),
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    for existing in active_requests:
        opposite_half_day_cl = (
            category == LeaveCategory.CL
            and existing.category == LeaveCategory.CL
            and start_date == end_date == existing.start_date == existing.end_date
            and day_part in (
                LeaveDayPart.FIRST_HALF,
                LeaveDayPart.SECOND_HALF,
            )
            and existing.day_part in (
                LeaveDayPart.FIRST_HALF,
                LeaveDayPart.SECOND_HALF,
            )
            and day_part != existing.day_part
        )
        if not opposite_half_day_cl:
            raise ConflictError(
                "The requested dates overlap an existing pending or approved "
                "leave request.",
                code="leave_request_overlap",
            )


@transaction.atomic
def withdraw(*, request_id: int, user_id: int) -> LeaveRequest:
    leave_request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id, user_id=user_id)
        .first()
    )
    if leave_request is None:
        raise NotFoundError("No such leave request.")
    if leave_request.status != LeaveStatus.PENDING:
        raise ConflictError(
            "Only a pending leave request can be withdrawn.",
            code="leave_request_not_pending",
        )

    previous_status = leave_request.status
    leave_request.status = LeaveStatus.WITHDRAWN
    leave_request.save(update_fields=["status", "updated_at"])
    LeaveRequestEvent.objects.create(
        request=leave_request,
        event_type=LeaveRequestEvent.Type.WITHDRAWN,
        from_status=previous_status,
        to_status=LeaveStatus.WITHDRAWN,
        actor_user_id=user_id,
    )
    return leave_request
