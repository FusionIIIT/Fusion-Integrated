"""Leave Management API URL patterns.

Follows placement module pattern: URL patterns in api/urls.py.
"""
from django.urls import include, path

from modules.leave.api import views as api_views

# -- Leave Balance URLs --
leave_balance_urls = [
    path("", api_views.LeaveBalanceListView.as_view(), name="leave_balance_list"),
    path("<int:pk>", api_views.LeaveBalanceDetailView.as_view(), name="leave_balance_detail"),
]

# -- Leave Request URLs --
leave_request_urls = [
    path("", api_views.LeaveRequestListView.as_view(), name="leave_request_list"),
    path("<int:pk>", api_views.LeaveRequestDetailView.as_view(), name="leave_request_detail"),
    path("create", api_views.LeaveRequestCreateView.as_view(), name="leave_request_create"),
    path("<int:pk>/approve", api_views.LeaveRequestApproveView.as_view(), name="leave_request_approve"),
    path("<int:pk>/cancel", api_views.LeaveRequestCancelView.as_view(), name="leave_request_cancel"),
    path("<int:pk>/resumefromresigned", api_views.LeaveRequestResumeView.as_view(), name="leave_request_resume"),
    path("<int:pk>/extend", api_views.LeaveRequestExtendView.as_view(), name="leave_request_extend"),
    path("<int:pk>/withdraw", api_views.LeaveRequestWithdrawView.as_view(), name="leave_request_withdraw"),
]

# -- Leave Policy URLs --
leave_policy_urls = [
    path("", api_views.LeavePolicyListView.as_view(), name="leave_policy_list"),
    path("<int:pk>", api_views.LeavePolicyDetailView.as_view(), name="leave_policy_detail"),
    path("<int:pk>/update", api_views.LeavePolicyUpdateView.as_view(), name="leave_policy_update"),
]

# -- Leave Sanction URLs --
leave_sanction_urls = [
    path("", api_views.LeaveSanctionListView.as_view(), name="leave_sanction_list"),
    path("<int:pk>", api_views.LeaveSanctionDetailView.as_view(), name="leave_sanction_detail"),
    path("<int:request_id>/sanction", api_views.LeaveSanctionCreateView.as_view(), name="leave_sanction_create"),
]

# -- Leave Category URLs --
leave_category_urls = [
    path("", api_views.LeaveCategoryListView.as_view(), name="leave_category_list"),
    path("<int:pk>", api_views.LeaveCategoryDetailView.as_view(), name="leave_category_detail"),
]

# -- Holiday Calendar URLs --
holiday_calendar_urls = [
    path("", api_views.LeaveHolidayCalendarListView.as_view(), name="holiday_calendar_list"),
    path("<int:pk>", api_views.LeaveHolidayCalendarDetailView.as_view(), name="holiday_calendar_detail"),
]


# Include URLs
urlpatterns = [
    path("balance/", include(leave_balance_urls)),
    path("requests/", include(leave_request_urls)),
    path("policy/", include(leave_policy_urls)),
    path("sanctions/", include(leave_sanction_urls)),
    path("categories/", include(leave_category_urls)),
    path("holiday/", include(holiday_calendar_urls)),
]
