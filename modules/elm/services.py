from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from modules.elm.models import LeaveBalance, LeaveApplication, LeaveActionHistory

INITIAL_QUOTAS = {"CL": 8.0, "RH": 2.0, "SCL": 15.0, "EL": 30.0, "VL": 60.0, "COL": 20.0}


def ensure_balances(user_id: int, year: int = 2026):
    for lt, val in INITIAL_QUOTAS.items():
        LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, leave_type=lt,
            defaults={"allocated": Decimal(str(val)), "availed": Decimal("0.0"), "pending": Decimal("0.0")}
        )


@transaction.atomic
def apply_leave(user_id: int, leave_type: str, start_date, end_date, reason: str, station_leave: bool = False, station_address: str = ""):
    ensure_balances(user_id, year=start_date.year)
    if end_date < start_date:
        raise ValidationError("End date cannot be earlier than start date.")

    # Calculate days count
    days = Decimal(str((end_date - start_date).days + 1))
    bal = LeaveBalance.objects.select_for_update().get(user_id=user_id, year=start_date.year, leave_type=leave_type)
    if Decimal(str(bal.available_balance)) < days:
        raise ValidationError(f"Insufficient leave balance (available: {bal.available_balance}).")

    bal.pending += days
    bal.save(update_fields=["pending", "updated_at"])

    app = LeaveApplication.objects.create(
        user_id=user_id, leave_type=leave_type, start_date=start_date, end_date=end_date,
        days_requested=days, reason=reason, station_leave=station_leave, station_address=station_address
    )
    LeaveActionHistory.objects.create(application=app, actor_user_id=user_id, action="SUBMIT")
    return app


@transaction.atomic
def review_leave(app_id: int, actor_user_id: int, action: str, remarks: str = ""):
    app = LeaveApplication.objects.select_for_update().get(id=app_id)
    bal = LeaveBalance.objects.select_for_update().get(user_id=app.user_id, year=app.start_date.year, leave_type=app.leave_type)

    if action == "APPROVE":
        app.status = "APPROVED"
        bal.pending = max(Decimal("0.0"), bal.pending - app.days_requested)
        bal.availed += app.days_requested
    elif action == "REJECT":
        app.status = "REJECTED"
        bal.pending = max(Decimal("0.0"), bal.pending - app.days_requested)
    elif action == "RECOMMEND":
        app.status = "RECOMMENDED"

    bal.save(update_fields=["pending", "availed", "updated_at"])
    app.remarks = remarks
    app.save(update_fields=["status", "remarks", "updated_at"])
    LeaveActionHistory.objects.create(application=app, actor_user_id=actor_user_id, action=action, comments=remarks)
    return app


@transaction.atomic
def cancel_leave(app_id: int, user_id: int):
    app = LeaveApplication.objects.select_for_update().get(id=app_id, user_id=user_id)
    if app.status not in ["SUBMITTED", "RECOMMENDED"]:
        raise ValidationError("Only pending applications can be cancelled.")
    bal = LeaveBalance.objects.select_for_update().get(user_id=user_id, year=app.start_date.year, leave_type=app.leave_type)
    bal.pending = max(Decimal("0.0"), bal.pending - app.days_requested)
    bal.save(update_fields=["pending", "updated_at"])
    app.status = "CANCELLED"
    app.save(update_fields=["status", "updated_at"])
    LeaveActionHistory.objects.create(application=app, actor_user_id=user_id, action="CANCEL")
    return app
