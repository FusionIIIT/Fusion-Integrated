from django.urls import path
from modules.leave.api.views import (
    LeaveApplicationListView,
    LeaveApplicationDetailView,
    LeaveTypeListView,
    LeaveBalanceListView,
)

urlpatterns = [
    path("applications/", LeaveApplicationListView.as_view(), name="leave-application-list"),
    path("applications/<int:pk>/", LeaveApplicationDetailView.as_view(), name="leave-application-detail"),
    path("types/", LeaveTypeListView.as_view(), name="leave-type-list"),
    path("balances/", LeaveBalanceListView.as_view(), name="leave-balance-list"),
]
