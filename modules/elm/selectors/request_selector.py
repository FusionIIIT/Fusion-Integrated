from modules.elm.models import LeaveApprovalTask, LeaveRequest


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


    @staticmethod
    def pending_substitute_for_user(user_id):
        return LeaveRequest.objects.filter(
            substitute_user_id=user_id,
            substitute_status="PENDING",
            status="PENDING_SUBSTITUTE",
        ).order_by("submitted_at")


class LeaveApprovalTaskSelector:
    """Only return actionable tasks assigned to the current IAM identity."""

    @staticmethod
    def pending_for_user(user_id):
        return (
            LeaveApprovalTask.objects.filter(
                assignee_user_id=user_id,
                status="PENDING",
            )
            .select_related("request")
            .order_by("assigned_at", "step_order")
        )
