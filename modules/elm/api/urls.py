"""URL routing for Employee Leave Management API."""
from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("types", views.LeaveTypeListView.as_view(), name="elm-leave-types"),
    path("balances", views.LeaveBalanceListView.as_view(), name="elm-balances"),
    path(
        "applications",
        views.LeaveApplicationListCreateView.as_view(),
        name="elm-applications",
    ),
    path(
        "applications/<int:pk>/withdraw",
        views.LeaveWithdrawView.as_view(),
        name="elm-application-withdraw",
    ),
    path(
        "applications/<int:pk>/substitute",
        views.SubstituteResponseView.as_view(),
        name="elm-substitute-respond",
    ),
    path(
        "approvals",
        views.LeaveApprovalQueueView.as_view(),
        name="elm-approvals",
    ),
    path(
        "approvals/<int:pk>/decide",
        views.LeaveApprovalDecisionView.as_view(),
        name="elm-approval-decide",
    ),
    path(
        "calendar",
        views.HolidayCalendarListView.as_view(),
        name="elm-holiday-calendar",
    ),
]
