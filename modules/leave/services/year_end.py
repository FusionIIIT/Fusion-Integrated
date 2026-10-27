from django.db import transaction
from modules.leave.models import LeaveBalance
from modules.leave.domain.year_end import calculate_year_end_adjustments

@transaction.atomic
def run_year_end_processing(year: int) -> dict:
    balances_to_process = LeaveBalance.objects.filter(year=year, year_end_processed=False)
    processed_count = 0

    for balance in balances_to_process:
        adjustments = calculate_year_end_adjustments(balance)
        
        # Create new leave balance for the next year
        new_balance = LeaveBalance.objects.create(
            employee_id=balance.employee_id,
            year=year + 1,
            available_days=adjustments['available'],
            used_days=adjustments['used'],
            carry_forward_days=adjustments['carry_forward'],
            year_end_processed=False
        )
        
        # Write ledger entries for lapse, conversion, and carry-forward
        if adjustments['lapse']:
            new_balance.ledger_entries.create(
                type='Lapse',
                amount=-adjustments['lapse']
            )
        if adjustments['conversion']:
            new_balance.ledger_entries.create(
                type='Conversion',
                amount=adjustments['conversion']
            )
        if adjustments['carry_forward']:
            new_balance.ledger_entries.create(
                type='Carry Forward',
                amount=adjustments['carry_forward']
            )
        
        # Mark current balance as processed
        balance.year_end_processed = True
        balance.save()
        
        processed_count += 1

    return {'count_processed': processed_count}