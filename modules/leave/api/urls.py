"""Leave Management API URLs."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.leave import (
    LeaveRequestViewSet,
    PendingApprovalsView,
    ApprovalActionsViewSet,
    SubstituteRequestViewSet,
    LeaveBalanceViewSet,
    LeaveBalanceAdminViewSet,
    LeavePolicyViewSet,
    HolidayCalendarViewSet,
    OfflineLeaveEntryViewSet,
    YearEndProcessingViewSet,
)

router = DefaultRouter()
router.register(r"leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register(r"substitute-requests", SubstituteRequestViewSet, basename="substitute-request")
router.register(r"balances", LeaveBalanceViewSet, basename="leave-balance")
router.register(r"policies", LeavePolicyViewSet, basename="leave-policy")
router.register(r"calendar", HolidayCalendarViewSet, basename="holiday-calendar")
router.register(r"offline-entries", OfflineLeaveEntryViewSet, basename="offline-leave-entry")

urlpatterns = [
    path("", include(router.urls)),
    path("pending-approvals/", PendingApprovalsView.as_view(), name="pending-approvals"),
    path("approvals/", include([
        path("<int:leave_request_id>/unit-head-review/", ApprovalActionsViewSet.as_view({"post": "unit_head_review"}), name="unit-head-review"),
        path("<int:leave_request_id>/establishment-review/", ApprovalActionsViewSet.as_view({"post": "establishment_review"}), name="establishment-review"),
        path("<int:leave_request_id>/final-sanction/", ApprovalActionsViewSet.as_view({"post": "final_sanction"}), name="final-sanction"),
    ])),
    path("balances/admin/", LeaveBalanceAdminViewSet.as_view({"post": "adjust"}), name="balance-adjust"),
    path("year-end/", YearEndProcessingViewSet.as_view({"post": "run"}), name="year-end-run"),
]