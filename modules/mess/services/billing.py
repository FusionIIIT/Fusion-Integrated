from django.db import transaction
from django.utils import timezone
from modules.mess.models import SpecialFoodRequest, RebateRequest, MonthlyBill, BillingRule, RebateRule, State
from modules.mess.services._audit import record_transition, queue_notification

@transaction.atomic
def generate_monthly_bills(year, month, daily_rate, served_days_by_user):
    created_bills = []
    for user_id, served_days in served_days_by_user.items():
        charge_amount = SpecialFoodRequest.objects.filter(user_id=user_id, status__in=['APPROVED', 'SERVED'], requested_for__month=month, requested_for__year=year).aggregate(total=Sum('charge_amount'))['total']
        rebate_days = RebateRule.objects.filter(user_id=user_id, approved_date__month=month, approved_date__year=year).aggregate(total=Sum('rebate_days_in_month'))['total']
        total_days = served_days + rebate_days
        bill = MonthlyBill(user_id=user_id, year=year, month=month, total_days=total_days, daily_rate=daily_rate, status='GENERATED')
        bill.save()
        created_bills.append(bill)

    return created_bills

def finalize_bill(bill_id, actor_user_id):
    bill = MonthlyBill.objects.get(id=bill_id)
    if bill.status != 'GENERATED':
        raise ValueError('Bill status is not GENERATED')
    if not can_transition(bill, 'FINALIZED', actor_user_id):
        raise ValueError('Cannot transition bill to FINALIZED')
    record_transition(bill, 'FINALIZED', actor_user_id)
    bill.status = 'FINALIZED'
    bill.published_at = timezone.now()
    queue_notification('BILL_PUBLISHED', bill.user_id)
    bill.save()

def publish_bill(bill_id, actor_user_id):
    bill = MonthlyBill.objects.get(id=bill_id)
    if bill.status != 'FINALIZED':
        raise ValueError('Bill status is not FINALIZED')
    if not can_transition(bill, 'PUBLISHED', actor_user_id):
        raise ValueError('Cannot transition bill to PUBLISHED')
    record_transition(bill, 'PUBLISHED', actor_user_id)
    bill.status = 'PUBLISHED'
    bill.save()
