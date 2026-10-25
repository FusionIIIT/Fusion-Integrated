from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("types", views.LeaveTypeListView.as_view(), name="leave-types"),
    path("balances", views.MyLeaveBalancesView.as_view(), name="leave-balances"),
    path(
        "balances/allocate",
        views.LeaveBalanceAllocateView.as_view(),
        name="leave-balance-allocate",
    ),
    path("requests", views.MyLeaveRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/cancel", views.CancelLeaveRequestView.as_view(), name="leave-cancel"),
    path(
        "requests/<int:pk>/withdraw",
        views.WithdrawLeaveRequestView.as_view(),
        name="leave-withdraw",
    ),
    path(
        "requests/<int:pk>/extend",
        views.ExtensionCreateView.as_view(),
        name="leave-extend",
    ),
    path(
        "requests/<int:pk>/resumption",
        views.ResumptionSubmitView.as_view(),
        name="leave-resumption-submit",
    ),
    path(
        "resumptions/<int:pk>/review",
        views.ResumptionReviewView.as_view(),
        name="leave-resumption-review",
    ),
    path(
        "requests/<int:pk>/substitute",
        views.SubstituteNominateView.as_view(),
        name="leave-substitute-nominate",
    ),
    path(
        "requests/<int:pk>/substitute-response",
        views.SubstituteResponseView.as_view(),
        name="leave-substitute-response",
    ),
    path("requests/<int:pk>/review", views.ReviewView.as_view(), name="leave-review"),
    path("approvals", views.PendingApprovalsView.as_view(), name="leave-pending-approvals"),
    path("requests/<int:pk>/decision", views.LeaveApprovalView.as_view(), name="leave-decision"),
]
