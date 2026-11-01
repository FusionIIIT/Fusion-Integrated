from django.db.models import Count, Sum
from modules.mess.models import RegistrationWindow, SpecialFoodRequest, Bill

def registration_trend():
    return RegistrationWindow.objects.values('window_title').annotate(approved_count=Count('approved'), rejected_count=Count('rejected'), pending_count=Count('pending'))

def special_meal_log(start_date, end_date):
    return SpecialFoodRequest.objects.filter(requested_for__range=(start_date, end_date)).order_by('requested_for')

def billing_summary(year, month):
    bills = Bill.objects.filter(date__year=year, date__month=month)
    total_amount = bills.aggregate(total_amount=Sum('amount'))
    status_counts = bills.values('status').annotate(count=Count('status'))
    return {'total_bills': bills.count(), 'total_amount': total_amount['total_amount'], 'status_counts': status_counts}
