from django.db import transaction
from django.utils import timezone
from modules.elm.domain.policy import PolicyViolation
from modules.elm.domain.state_machine import transition as require_transition
from modules.elm.models import LeaveRequest, LeaveTransition
from modules.elm.services import notifications

@transaction.atomic
def request_cancellation(*, request_id: int, actor_user_id: int, reason: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id, user_id=actor_user_id, status="approved")
    if req.start_date <= timezone.localdate():
        raise PolicyViolation("cancellation_after_start", "Approved leave can only be cancelled before its start date.")
    require_transition(req.status, "request_cancellation", "employee")
    old = req.status
    req.status = "cancellation_pending"
    req.cancellation_reason = reason
    req.cancellation_requested_at = timezone.now()
    req.cancellation_stage = 0
    req.current_role = (req.route[0]["role"] if req.route else "Leave Administrator")
    req.save()
    LeaveTransition.objects.create(request=req, from_status=old, to_status=req.status, event="request_cancellation", actor_user_id=actor_user_id, note=reason)
    notifications.notify(topic="leave_cancellation", title="Leave cancellation requested", body=f"Cancellation of leave request #{req.pk} needs review.", role=req.current_role, payload={"request_id": req.pk})
    return req
