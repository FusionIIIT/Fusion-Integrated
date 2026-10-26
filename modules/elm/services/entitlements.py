from django.db import transaction
from django.db.models import Sum
from core.api.exceptions import DomainError
from modules.elm.models import LeaveBalanceEntry


def credit_annual_entitlements(user_id, year, is_faculty):
    with transaction.atomic():
        categories = {
            "CL": 8,
            "RH": 2,
            "SCL": 15,
            "COL": 20,
        }
        if not is_faculty:
            categories["EL"] = 30
        if is_faculty:
            categories["VL"] = 60

        for category, days in categories.items():
            if days == 0:
                continue
            if not LeaveBalanceEntry.objects.filter(user_id=user_id, year=year, category=category, reason="Annual Entitlement").exists():
                LeaveBalanceEntry.objects.create(
                    user_id=user_id, year=year, category=category, days_delta=days, reason="Annual Entitlement"
                )


def get_balance(user_id, category, year):
    balance = LeaveBalanceEntry.objects.filter(user_id=user_id, year=year, category=category).aggregate(Sum('days_delta'))
    return balance['days_delta__sum'] or 0
