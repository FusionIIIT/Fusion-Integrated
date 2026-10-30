"""Leave API URL routes."""
from django.urls import path

from .views import (
    ApprovalsQueueListView,
    DecideCancellationView,
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveBalanceListView,
    LeaveCancellationView,
    LeaveExtensionView,
    LeaveResumptionView,
    LeaveReviewView,
    OfflineLeaveRecordView,
    SubstituteQueueListView,
    SubstituteRespondView,
    VerifyResumptionView,
    YearEndProcessingView,
)

urlpatterns = [
    path("balances/", LeaveBalanceListView.as_view(), name="leave_balances"),
    path("applications/", LeaveApplicationListCreateView.as_view(), name="leave_applications"),
    path("applications/<int:pk>/", LeaveApplicationDetailView.as_view(), name="leave_detail"),
    path("applications/<int:pk>/cancel/", LeaveCancellationView.as_view(), name="leave_cancel"),
    path("applications/<int:pk>/decide-cancellation/", DecideCancellationView.as_view(), name="leave_decide_cancellation"),
    path("applications/<int:pk>/extend/", LeaveExtensionView.as_view(), name="leave_extend"),
    path("applications/<int:pk>/resume/", LeaveResumptionView.as_view(), name="leave_resume"),
    path("applications/<int:pk>/verify-resumption/", VerifyResumptionView.as_view(), name="leave_verify_resumption"),
    path("substitute-queue/", SubstituteQueueListView.as_view(), name="substitute_queue"),
    path("substitute-queue/<int:pk>/respond/", SubstituteRespondView.as_view(), name="substitute_respond"),
    path("approvals-queue/", ApprovalsQueueListView.as_view(), name="approvals_queue"),
    path("approvals-queue/<int:pk>/decide/", LeaveReviewView.as_view(), name="approvals_decide"),
    path("offline-record/", OfflineLeaveRecordView.as_view(), name="offline_record"),
    path("year-end/", YearEndProcessingView.as_view(), name="year_end"),
]
