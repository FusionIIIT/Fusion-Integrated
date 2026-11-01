from modules.mess.models import MonthlyBill

def list_published_bills_for_user(user_id):
    return MonthlyBill.objects.filter(user=user_id, status='PUBLISHED').order_by('-created_at')

def outstanding_balance(user_id):
    return MonthlyBill.objects.filter(user=user_id, status='PUBLISHED').aggregate(total=Sum('total_amount'))['total']

def list_bills_for_review(year, month):
    return MonthlyBill.objects.filter(user=user_id, status__in=['GENERATED', 'FINALIZED'], created_at__month=month, created_at__year=year)
