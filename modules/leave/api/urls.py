"""URL routing for Leave Management endpoints."""
from __future__ import annotations

from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("requests/", views.LeaveRequestListCreateView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/", views.LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path("requests/<int:pk>/decide/", views.DecideLeaveRequestView.as_view(), name="leave-request-decide"),
    path("requests/<int:pk>/cancel/", views.CancelLeaveRequestView.as_view(), name="leave-request-cancel"),
    path("balances/", views.LeaveBalanceListView.as_view(), name="leave-balances"),
    path("pending/", views.PendingApprovalsListView.as_view(), name="leave-pending-approvals"),
]
