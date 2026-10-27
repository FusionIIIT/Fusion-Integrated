from django.urls import path
from .views import (
    LeaveTypeListView, LeaveTypeDetailView,
    LeaveBalanceListView,
    LeaveListView, LeaveDetailView,
    WithdrawLeaveView,
    SubstituteResponseView,
    UnitHeadReviewView
)

urlpatterns = [
    path('types/', LeaveTypeListView.as_view(), name='leave-type-list-create'),
    path('types/<int:pk>/', LeaveTypeDetailView.as_view(), name='leave-type-detail'),
    path('balances/', LeaveBalanceListView.as_view(), name='leave-balance-list'),
    path('', LeaveListView.as_view(), name='leave-list-create'),
    path('<int:pk>/', LeaveDetailView.as_view(), name='leave-detail'),
    path('<int:pk>/withdraw/', WithdrawLeaveView.as_view(), name='leave-withdraw'),
    path('<int:pk>/substitute-respond/', SubstituteResponseView.as_view(), name='leave-substitute-respond'),
    path('<int:pk>/unit-head-review/', UnitHeadReviewView.as_view(), name='leave-unit-head-review'),
]