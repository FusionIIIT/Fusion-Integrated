from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

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
def review_request(*, leave_request, actor_id, decision, note=""):
    if leave_request.status != "pending":
        raise ValidationError({"status": "Only pending requests can be reviewed."})
    leave_request.status = decision
    leave_request.reviewed_by_user_id = actor_id
    leave_request.reviewed_at = timezone.now()
    leave_request.review_note = note.strip()
    leave_request.save(update_fields=["status", "reviewed_by_user_id", "reviewed_at",
                                      "review_note", "updated_at"])
    return leave_request
