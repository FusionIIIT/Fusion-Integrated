from decimal import Decimal

from rest_framework.exceptions import ValidationError

from modules.directory.models import UserRef
from modules.elm.models import LeavePolicy, LeaveRequest
from modules.elm.validation import account


def policy_for(leave_type, kind, medical_evidence=""):
    policies = LeavePolicy.objects.filter(type=leave_type)
    if len(policies) > 1:
        raise ValidationError("Multiple policies found for the leave type")
    if not policies:
        return None
    policy = policies[0]
    if policy.applicable_kind and policy.applicable_kind != kind:
        raise ValidationError("Policy applicable kind does not match")
    if (
        leave_type.type == "COL"
        and policy.medical_evidence_required
        and not medical_evidence.strip()
    ):
        raise ValidationError("Medical evidence is required but not provided")
    return policy


def ensure_overlap_free(employee, leave_type, start, end, half, exclude=None):
    queryset = LeaveRequest.objects.filter(
        employee=employee,
        operation__in=["LEAVE", "EXTENSION"],
        status__in=["PENDING", "APPROVED"],
        start_date__lte=end,
        end_date__gte=start,
    )
    if exclude is not None:
        queryset = queryset.exclude(pk=exclude)
    for row in queryset:
        if half == "FULL" or row.half_day == "FULL":
            raise ValidationError("Overlapping full-day leave")
        if (
            leave_type.type != "CL"
            or row.leave_type.type != "CL"
            or start != end
            or start != row.start_date
            or end != row.end_date
            or (
                half in ["FIRST", "SECOND"]
                and row.half_day in ["FIRST", "SECOND"]
                and half == row.half_day
            )
        ):
            raise ValidationError("Overlap conflict detected")
    return


def ensure_nominee(employee, nominee, required, start, end):
    if nominee is None:
        if required:
            raise ValidationError("Nominee is required.")
        return True
    if not isinstance(nominee, int) or nominee <= 0 or nominee == employee:
        return False
    if not UserRef.objects.filter(
        user_id=nominee, is_active=True, kind__in=["faculty", "staff"]
    ).exists():
        return False
    return not LeaveRequest.objects.filter(
        employee=nominee,
        operation__in=["LEAVE", "EXTENSION"],
        status__in=["PENDING", "APPROVED"],
        start_date__lte=end,
        end_date__gte=start,
    ).exists()


def ensure_balance(employee, leave_type, start, kind, days, exclude=None):
    balance_row = account(employee, leave_type, start.year, kind)
    requests = (
        LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            start_date__year=start.year,
            status="PENDING",
            operation__in=["LEAVE", "EXTENSION"],
        ).exclude(pk=exclude)
        if exclude
        else LeaveRequest.objects.filter(
            employee=employee,
            leave_type=leave_type,
            start_date__year=start.year,
            status="PENDING",
            operation__in=["LEAVE", "EXTENSION"],
        )
    )
    total_days = sum(requests.values_list("days", flat=True), start=Decimal("0"))
    if balance_row.balance - total_days < days:
        raise ValidationError("Insufficient leave balance.")
    return balance_row
