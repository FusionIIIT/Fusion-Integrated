"""URL patterns for Employee Leave Management (ELM) API."""
from django.urls import path

from .views import (
    ApprovalStepActionView,
    HolidayCalendarListView,
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveBalanceListView,
    LeaveCancelView,
    LeaveExtensionView,
    LeavePolicyListView,
    LeaveResumptionView,
    LeaveWithdrawView,
    OfflineSanctionCreateView,
    PendingApprovalsListView,
    PendingSubstituteListView,
    SubstituteResponseView,
)

app_name = "elm"

urlpatterns = [
    path("balances/", LeaveBalanceListView.as_view(), name="balances-list"),
    path("policies/", LeavePolicyListView.as_view(), name="policies-list"),
    path("calendar/", HolidayCalendarListView.as_view(), name="calendar-list"),
    path("applications/", LeaveApplicationListCreateView.as_view(), name="applications-list-create"),
    path("applications/<int:pk>/", LeaveApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/withdraw/", LeaveWithdrawView.as_view(), name="application-withdraw"),
    path("applications/<int:pk>/cancel/", LeaveCancelView.as_view(), name="application-cancel"),
    path("applications/<int:pk>/extend/", LeaveExtensionView.as_view(), name="application-extend"),
    path("applications/<int:pk>/resumption/", LeaveResumptionView.as_view(), name="application-resumption"),
    path("tasks/approvals/", PendingApprovalsListView.as_view(), name="pending-approvals"),
    path("tasks/approvals/<int:pk>/decide/", ApprovalStepActionView.as_view(), name="approval-decide"),
    path("tasks/substitutes/", PendingSubstituteListView.as_view(), name="pending-substitutes"),
    path("tasks/substitutes/<int:pk>/respond/", SubstituteResponseView.as_view(), name="substitute-respond"),
    path("admin/offline-sanction/", OfflineSanctionCreateView.as_view(), name="offline-sanction"),
]
