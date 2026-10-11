from modules.elm.models import ApprovalTask, LeaveRequest


def requests_for_user(user_id):
    return LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")


def pending_tasks_for_approver(user_id):
    return ApprovalTask.objects.filter(approver_user_id=user_id, status="pending").select_related("request").order_by("created_at")
