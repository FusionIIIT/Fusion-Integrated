from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from modules.elm.models import LeaveBalance, LeaveApplication, LeaveActionHistory

ANNUAL_LIMITS = {"CL": 8.0, "RH": 2.0, "SCL": 15.0, "EL": 30.0, "VL": 60.0, "COL": 20.0}


def init_user_quotas(user_id: int, year: int = 2026):
    for code, quota in ANNUAL_LIMITS.items():
        LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, leave_type=code,
            defaults={"allocated": Decimal(str(quota)), "availed": Decimal("0.0"), "pending": Decimal("0.0")}
        )


@transaction.atomic
def create_leave_request(user_id: int, leave_type: str, start_date, end_date, reason: str, station_leave: bool = False, station_address: str = ""):
    init_user_quotas(user_id, year=start_date.year)
    if end_date < start_date:
        raise ValidationError("End date cannot precede start date.")

    days = Decimal(str((end_date - start_date).days + 1))
    account = LeaveBalance.objects.select_for_update().get(user_id=user_id, year=start_date.year, leave_type=leave_type)
    if Decimal(str(account.remaining)) < days:
        raise ValidationError(f"Requested days ({days}) exceed available balance ({account.remaining}).")

    account.pending += days
    account.save(update_fields=["pending", "updated_at"])

    req = LeaveApplication.objects.create(
        user_id=user_id, leave_type=leave_type, start_date=start_date, end_date=end_date,
        days_count=days, reason=reason, station_leave=station_leave, station_address=station_address
    )
    LeaveActionHistory.objects.create(application=req, actor_id=user_id, action="SUBMIT", remark="Application submitted")
    return req


@transaction.atomic
def resolve_leave_request(req_id: int, actor_id: int, outcome: str, note: str = ""):
    req = LeaveApplication.objects.select_for_update().get(id=req_id)
    account = LeaveBalance.objects.select_for_update().get(user_id=req.user_id, year=req.start_date.year, leave_type=req.leave_type)

    if outcome == "APPROVE":
        req.status = "APPROVED"
        account.pending = max(Decimal("0.0"), account.pending - req.days_count)
        account.availed += req.days_count
    elif outcome == "REJECT":
        req.status = "REJECTED"
        account.pending = max(Decimal("0.0"), account.pending - req.days_count)

    account.save(update_fields=["pending", "availed", "updated_at"])
    req.admin_remark = note
    req.save(update_fields=["status", "admin_remark", "updated_at"])
    LeaveActionHistory.objects.create(application=req, actor_id=actor_id, action=outcome, remark=note)
    return req


@transaction.atomic
def withdraw_leave_request(req_id: int, user_id: int):
    req = LeaveApplication.objects.select_for_update().get(id=req_id, user_id=user_id)
    if req.status != "PENDING":
        raise ValidationError("Only pending requests can be withdrawn.")
    account = LeaveBalance.objects.select_for_update().get(user_id=user_id, year=req.start_date.year, leave_type=req.leave_type)
    account.pending = max(Decimal("0.0"), account.pending - req.days_count)
    account.save(update_fields=["pending", "updated_at"])
    req.status = "CANCELLED"
    req.save(update_fields=["status", "updated_at"])
    LeaveActionHistory.objects.create(application=req, actor_id=user_id, action="WITHDRAW", remark="Withdrawn by applicant")
    return req
