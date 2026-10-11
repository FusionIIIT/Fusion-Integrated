from .models import LeaveRequest


def get_leave_requests_for_user(user):
    user_id = getattr(user, "user_id", getattr(user, "id", user))
    return LeaveRequest.objects.filter(user_id=user_id)
