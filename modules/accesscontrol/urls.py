from django.urls import path
from .views import LeaveTypeListView, LeaveBalanceListView, LeaveApplicationListView, SubstituteNomineeListView

urlpatterns = [
    path('leave-types/', LeaveTypeListView.as_view(), name='leave-type-list'),
    path('leave-balances/', LeaveBalanceListView.as_view(), name='leave-balance-list'),
    path('leave-applications/', LeaveApplicationListView.as_view(), name='leave-application-list'),
    path('substitute-nominations/', SubstituteNomineeListView.as_view(), name='substitute-nomination-list'),
]
