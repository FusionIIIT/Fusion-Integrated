from .models import LeaveRequest


def create_leave_request(user, category, start_date, end_date, reason):
    user_id = getattr(user, "user_id", getattr(user, "id", user))
    return LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
    )


def approve_leave_request(leave_request):
    leave_request.status = "approved"
    leave_request.save()


def reject_leave_request(leave_request):
    leave_request.status = "rejected"
    leave_request.save()


def cancel_leave_request(leave_request):
    leave_request.status = "cancelled"
    leave_request.save()
