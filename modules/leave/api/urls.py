from django.urls import path

from modules.leave.api.views import (
    LeaveApprovalView,
    LeaveBalanceAdjustmentView,
    LeaveCalendarAdminView,
    LeaveCalendarPublishView,
    LeaveCalendarView,
    MyLeaveBalanceHistoryView,
    MyLeaveBalancesView,
    MyLeaveRequestsView,
)

urlpatterns = [
    path("requests", MyLeaveRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:request_id>", MyLeaveRequestsView.as_view(),
         name="leave-request-cancel"),
    path("approvals", LeaveApprovalView.as_view(), name="leave-approvals"),
    path("approvals/<int:request_id>", LeaveApprovalView.as_view(), name="leave-approval"),
    path("balances", MyLeaveBalancesView.as_view(), name="leave-balances"),
    path("balances/changes", MyLeaveBalanceHistoryView.as_view(),
         name="leave-balance-changes"),
    path("admin/balances", LeaveBalanceAdjustmentView.as_view(),
         name="leave-balance-adjustment"),
    path("calendar", LeaveCalendarView.as_view(), name="leave-calendar"),
    path("admin/calendars", LeaveCalendarAdminView.as_view(),
         name="leave-calendar-create"),
    path("admin/calendars/<int:calendar_id>/publish",
         LeaveCalendarPublishView.as_view(), name="leave-calendar-publish"),
]
