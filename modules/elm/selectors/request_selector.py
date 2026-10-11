from modules.elm.models import LeaveRequest


class LeaveRequestSelector:
    """Read leave requests with ownership filtering."""

    @staticmethod
    def for_user(user_id):
        return LeaveRequest.objects.filter(
            user_id=user_id
        ).order_by("-submitted_at")

    @staticmethod
    def get_for_user(request_id, user_id):
        return LeaveRequest.objects.filter(
            pk=request_id,
            user_id=user_id,
        ).first()
