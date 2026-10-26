from django.urls import path

from .views import (
    EmployeeLeaveApplicationsView,
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveApprovalListView,
    LeaveBalanceListView,
    LeaveBalanceManagementView,
    LeaveCalendarManagementView,
    LeavePolicyManagementView,
    LeaveSubstituteListCreateView,
    LeaveTypeListView,
    LeaveWithdrawalView,
    OfflineLeaveRecordingView,
    YearEndLeaveProcessingView,
)

urlpatterns = [
    path("types/", LeaveTypeListView.as_view(), name="leave-type-list"),
    path("balances/", LeaveBalanceListView.as_view(), name="leave-balance-list"),
    path("balances/manage/", LeaveBalanceManagementView.as_view(), name="leave-balance-manage"),
    path("applications/", LeaveApplicationListCreateView.as_view(), name="leave-application-list-create"),
    path("applications/all/", EmployeeLeaveApplicationsView.as_view(), name="leave-application-all"),
    path("applications/<int:pk>/", LeaveApplicationDetailView.as_view(), name="leave-application-detail"),
    path("applications/<int:pk>/withdraw/", LeaveWithdrawalView.as_view(), name="leave-application-withdraw"),
    path("substitutes/", LeaveSubstituteListCreateView.as_view(), name="leave-substitute-list-create"),
    path("approvals/", LeaveApprovalListView.as_view(), name="leave-approval-list"),
    path("policy/", LeavePolicyManagementView.as_view(), name="leave-policy-manage"),
    path("calendar/", LeaveCalendarManagementView.as_view(), name="leave-calendar-manage"),
    path("offline/", OfflineLeaveRecordingView.as_view(), name="leave-offline-record"),
    path("year-end/", YearEndLeaveProcessingView.as_view(), name="leave-year-end-process"),
]
