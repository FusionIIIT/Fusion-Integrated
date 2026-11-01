"""Server-owned submission and balance reservations."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import EmployeeRecord, HRRequest, LeaveAccount, LeavePolicy
from .support import emit, require, route_for


@transaction.atomic
def submit(principal, data):
    require(principal, "hreis.requests.submit")
    try:
        employee = EmployeeRecord.objects.select_for_update().get(user_id=principal.user_id)
    except EmployeeRecord.DoesNotExist:
        raise ValidationError("An HR employee record is required.") from None
    if employee.retired:
        raise ValidationError("Retired employees cannot submit new requests.")
    kind = data.get("kind")
    purpose = data.get("purpose", "").strip()
    if kind not in ("LEAVE", "LTC", "CPDA") or not purpose:
        raise ValidationError("A supported kind and nonblank purpose are required.")
    documents = data.get("documents", [])
    if not isinstance(documents, list) or any(
        not isinstance(x, str) or not x.strip() for x in documents
    ):
        raise ValidationError("Documents must be a list of nonblank evidence references.")
    values = {"employee": employee, "kind": kind, "purpose": purpose, "documents": documents}
    if kind == "LEAVE":
        policy = data.get("policy")
        if not isinstance(policy, LeavePolicy):
            raise ValidationError("A leave policy is required.")
        policy = LeavePolicy.objects.select_for_update().get(pk=policy.pk)
        if not policy.active or employee.category not in policy.eligible_categories:
            raise ValidationError("The employee is not eligible for this active policy.")
        start, end = data.get("start_date"), data.get("end_date")
        if start is None or end is None or end < start:
            raise ValidationError("A valid inclusive date range is required.")
        if start < timezone.localdate():
            raise ValidationError("New leave requests cannot start in the past.")
        days = Decimal((end - start).days + 1)
        try:
            account = LeaveAccount.objects.select_for_update().get(employee=employee, policy=policy)
        except LeaveAccount.DoesNotExist:
            raise ValidationError("A leave account is required.") from None
        requests = HRRequest.objects.filter(employee=employee, kind="LEAVE")
        reserved = requests.filter(policy=policy, status__in=["SUBMITTED", "PENDING"]).aggregate(
            total=Sum("days")
        )["total"] or Decimal(0)
        if account.available - reserved < days:
            raise ValidationError("Insufficient unreserved leave balance.")
        if requests.filter(
            status__in=["SUBMITTED", "PENDING", "APPROVED"],
            start_date__lte=end,
            end_date__gte=start,
        ).exists():
            raise ValidationError("Leave overlaps an active request.")
        values.update(
            policy=policy,
            start_date=start,
            end_date=end,
            days=days,
            route=route_for(employee, kind),
            status="PENDING",
        )
    else:
        amount = data.get("amount", Decimal(0))
        mode = data.get("mode")
        if mode not in ("ADVANCE", "REIMBURSEMENT") or amount <= 0 or not documents:
            raise ValidationError("A claim mode, positive amount and evidence are required.")
        if any(data.get(key) is not None for key in ("policy", "start_date", "end_date")):
            raise ValidationError("Leave fields are not allowed on financial claims.")
        values.update(mode=mode, amount=amount, status="SUBMITTED")
    req = HRRequest.objects.create(**values)
    emit(principal, "request.submitted", employee, request=req, details={"kind": kind})
    return req
