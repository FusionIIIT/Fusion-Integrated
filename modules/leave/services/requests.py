from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from modules.leave.domain.rules import LeaveRuleError, validate_request
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType


@transaction.atomic
def create_request(*, user_id, leave_type_id, start_date, end_date, reason):
    leave_type = LeaveType.objects.get(pk=leave_type_id, is_active=True)
    balance = LeaveBalance.objects.select_for_update().filter(
        user_id=user_id, leave_type=leave_type,
        year=start_date.year).first()
    if balance is None:
        raise ValidationError({"leave_type": "No leave balance is configured for this year."})
    used = sum(LeaveRequest.objects.filter(
        user_id=user_id, leave_type=leave_type, start_date__year=start_date.year,
        status__in=["pending", "approved"]).values_list("days", flat=True))
    available = balance.allocated_days + balance.carried_days - used
    try:
        days = validate_request(start_date, end_date, available)
    except LeaveRuleError as exc:
        raise ValidationError({"dates": str(exc)}) from exc
    if end_date.year != start_date.year:
        raise ValidationError({"dates": "A leave request cannot span calendar years."})
    return LeaveRequest.objects.create(
        user_id=user_id, leave_type=leave_type, start_date=start_date, end_date=end_date,
        days=days, reason=reason.strip())


@transaction.atomic
def review_request(*, leave_request, actor_id, decision, scope, note=""):
    if decision not in {"approved", "rejected"}:
        raise ValidationError({"decision": "Choose approved or rejected."})
    row = scope.select_for_update().filter(pk=leave_request.pk).first()
    if row is None:
        raise NotFound("No such leave request.")
    if row.user_id == actor_id:
        raise ValidationError({"status": "You cannot review your own leave request."})
    if row.status != "pending":
        raise ValidationError({"status": "Only pending requests can be reviewed."})
    row.status = decision
    row.reviewed_by_user_id = actor_id
    row.reviewed_at = timezone.now()
    row.review_note = note.strip()
    row.save(update_fields=["status", "reviewed_by_user_id", "reviewed_at",
                            "review_note", "updated_at"])
    return row


@transaction.atomic
def cancel_request(*, leave_request_id, user_id):
    row = (LeaveRequest.objects.select_for_update()
           .filter(pk=leave_request_id, user_id=user_id).first())
    if row is None:
        raise NotFound("No such leave request.")
    if row.status != "pending":
        raise ValidationError({"status": "Only pending requests can be cancelled."})
    row.status = "cancelled"
    row.save(update_fields=["status", "updated_at"])
    return row
