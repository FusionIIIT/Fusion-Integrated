from django.db import transaction
from django.db.models import Sum
from core.api.exceptions import DomainError
from modules.elm.models import LeaveBalanceEntry


def credit_annual_entitlements(user_id, year, is_faculty):
    with transaction.atomic():
        LeaveBalanceEntry.objects.filter(user_id=user_id, year=year).delete()
        if is_faculty:
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="CL", days_delta=8, reason="Annual Entitlement"
            )
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="RH", days_delta=2, reason="Annual Entitlement"
            )
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="SCL", days_delta=15, reason="Annual Entitlement"
            )
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="COL", days_delta=20, reason="Annual Entitlement"
            )
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="EL", days_delta=30, reason="Annual Entitlement"
            )
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="VL", days_delta=60, reason="Annual Entitlement"
            )
        else:
            LeaveBalanceEntry.objects.create(
                user_id=user_id, year=year, category="EL", days_delta=30, reason="Annual Entitlement"
            )


def get_balance(user_id, category, year):
    balance = LeaveBalanceEntry.objects.filter(user_id=user_id, year=year, category=category).aggregate(Sum('days_delta'))
    return balance['days_delta__sum'] or 0
