from django.urls import path
from .views import (
    LeaveTypeListView,
    LeaveBalanceListView,
    LeaveRequestListCreateView,
    LeaveRequestDetailView,
    SubstituteResponseView,
    LeaveApprovalActionView,
    LeaveWithdrawView,
)

urlpatterns = [
    path('types/', LeaveTypeListView.as_view(), name='leave-type-list'),
    path('balances/', LeaveBalanceListView.as_view(), name='leave-balance-list'),
    path('requests/', LeaveRequestListCreateView.as_view(), name='leave-request-list-create'),
    path('requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='leave-request-detail'),
    path('requests/<int:pk>/substitute-response/', SubstituteResponseView.as_view(), name='substitute-response'),
    path('requests/<int:pk>/action/', LeaveApprovalActionView.as_view(), name='leave-approval-action'),
    path('requests/<int:pk>/withdraw/', LeaveWithdrawView.as_view(), name='leave-withdraw'),
]