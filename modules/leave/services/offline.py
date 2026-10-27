from django.db import transaction
from django.utils import timezone
from .models import LeaveApplication, LeaveBalance, LeaveLedgerEntry

@transaction.atomic
def record_offline_sanctioned_leave(admin_user_id: int, user_id: int, category: str, start_date: datetime.date, end_date: datetime.date, reference_no: str, sanction_date: datetime.date, purpose: str = "", is_faculty: bool = False) -> LeaveApplication:
    # Create the LeaveApplication
    leave_application = LeaveApplication.objects.create(
        admin_user_id=admin_user_id,
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reference_no=reference_no,
        sanction_date=sanction_date,
        purpose=purpose,
        status="approved",
        is_offline_sanctioned=True
    )

    # Calculate the total days of leave
    total_days = (end_date - start_date).days + 1

    # Deduct balance from LeaveBalance
    leave_balance, created = LeaveBalance.objects.get_or_create(user_id=user_id, category=category)
    if leave_balance.balance >= total_days:
        leave_balance.balance -= total_days
        leave_balance.save()

    # Create LeaveLedgerEntry
    LeaveLedgerEntry.objects.create(
        user_id=user_id,
        category=category,
        transaction_type="deduction",
        amount=-total_days,
        balance=leave_balance.balance,
        transaction_date=sanction_date,
        description=f"Offline sanctioned leave for {total_days} days"
    )

    return leave_application