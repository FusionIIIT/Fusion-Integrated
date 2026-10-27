from django.db import transaction
from modules.leave.models import LeaveBalance, LeaveLedgerEntry

def get_or_create_balance(user_id: int, year: int, is_faculty: bool = False) -> LeaveBalance:
    with transaction.atomic():
        balance, created = LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year
        )
        if created:
            initial_balances = {
                'cl': 8.0,
                'rh': 2.0,
                'scl': 15.0,
                'el': 30.0 if not is_faculty else 0.0,
                'vl': 60.0 if is_faculty else 0.0,
                'col': 20.0
            }
            balance.__dict__.update(initial_balances)
            balance.save()
        return balance

def get_balance_summary(user_id: int, year: int | None = None) -> dict:
    if year is None:
        year = LeaveBalance.objects.filter(user_id=user_id).order_by('-year').first().year
    balance = LeaveBalance.objects.get(user_id=user_id, year=year)
    return {
        'cl': balance.cl,
        'rh': balance.rh,
        'scl': balance.scl,
        'el': balance.el,
        'vl': balance.vl,
        'col': balance.col
    }

def get_ledger_history(user_id: int, year: int | None = None) -> LeaveLedgerEntry:
    if year is None:
        year = LeaveBalance.objects.filter(user_id=user_id).order_by('-year').first().year
    return LeaveLedgerEntry.objects.filter(user_id=user_id, year=year).order_by('-created_at')