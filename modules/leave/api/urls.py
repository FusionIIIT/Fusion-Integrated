"""URL dispatch for Employee Leave Management endpoints."""

from django.urls import path

from modules.leave.api.views import (
    AdminOfflineLeaveView,
    ApprovalResumptionReviewView,
    ApprovalReviewView,
    ApprovalSanctionView,
    ApprovalsQueueView,
    LeaveAdminView,
    LeaveApplicationCreateView,
    LeaveBalancesView,
    LeaveCancelView,
    LeaveExtendView,
    LeaveHealthView,
    LeaveRequestDetailView,
    LeaveRequestsView,
    LeaveResumeView,
    LeaveTypeListView,
    LeaveWithdrawView,
    SubstituteNominationsListView,
    SubstituteRespondView,
)

app_name = "leave"

urlpatterns = [
    # System & Health
    path("health/", LeaveHealthView.as_view(), name="health"),
    path("types/", LeaveTypeListView.as_view(), name="types"),
    # Balances & History
    path("balances/", LeaveBalancesView.as_view(), name="balances"),
    path("requests/", LeaveRequestsView.as_view(), name="requests"),
    path("requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="request_detail"),
    # Employee Actions
    path("applications/", LeaveApplicationCreateView.as_view(), name="applications"),
    path("requests/<int:pk>/withdraw/", LeaveWithdrawView.as_view(), name="request_withdraw"),
    path("requests/<int:pk>/cancel/", LeaveCancelView.as_view(), name="request_cancel"),
    path("requests/<int:pk>/extend/", LeaveExtendView.as_view(), name="request_extend"),
    path("requests/<int:pk>/resume/", LeaveResumeView.as_view(), name="request_resume"),
    # Substitute Actions
    path(
        "substitute/nominations/",
        SubstituteNominationsListView.as_view(),
        name="substitute_nominations",
    ),
    path(
        "substitute/nominations/<int:pk>/respond/",
        SubstituteRespondView.as_view(),
        name="substitute_respond",
    ),
    # Approvals & Decisions
    path("approvals/", ApprovalsQueueView.as_view(), name="approvals"),
    path("approvals/<int:pk>/review/", ApprovalReviewView.as_view(), name="approval_review"),
    path("approvals/<int:pk>/sanction/", ApprovalSanctionView.as_view(), name="approval_sanction"),
    path(
        "approvals/<int:pk>/resumption/",
        ApprovalResumptionReviewView.as_view(),
        name="approval_resumption",
    ),
    # Admin Operations
    path("admin/", LeaveAdminView.as_view(), name="admin"),
    path("admin/offline/", AdminOfflineLeaveView.as_view(), name="admin_offline"),
]
