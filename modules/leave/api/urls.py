"""URL routing for Employee Leave Management (ELM) API."""
from __future__ import annotations

from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    path("applications", v.LeaveApplicationListCreateView.as_view(), name="leave-applications"),
    path(
        "applications/<int:pk>",
        v.LeaveApplicationDetailView.as_view(),
        name="leave-application-detail",
    ),
    path(
        "applications/<int:pk>/history",
        v.LeaveApplicationHistoryView.as_view(),
        name="leave-application-history",
    ),
    path(
        "applications/<int:pk>/substitute",
        v.SubstituteResponseView.as_view(),
        name="leave-substitute-respond",
    ),
    path(
        "applications/<int:pk>/review",
        v.ReviewApplicationView.as_view(),
        name="leave-application-review",
    ),
    path(
        "applications/<int:pk>/sanction",
        v.SanctionApplicationView.as_view(),
        name="leave-application-sanction",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.WithdrawApplicationView.as_view(),
        name="leave-application-withdraw",
    ),
    path("balances", v.LeaveBalanceListView.as_view(), name="leave-balances"),
]
