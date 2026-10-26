from django.urls import path
from modules.leave.api import views as v

urlpatterns = [
    # Employee views
    path("balance", v.LeaveBalanceView.as_view(), name="leave-balance"),
    path("applications", v.LeaveApplicationListCreateView.as_view(), name="leave-applications"),
    path("applications/<int:pk>", v.LeaveApplicationDetailView.as_view(), name="leave-application-detail"),
    path("applications/<int:pk>/withdraw", v.LeaveApplicationWithdrawView.as_view(), name="leave-application-withdraw"),
    path("applications/<int:pk>/cancel", v.LeaveApplicationCancelView.as_view(), name="leave-application-cancel"),
    path("applications/<int:pk>/extend", v.LeaveApplicationExtendView.as_view(), name="leave-application-extend"),
    path("applications/<int:pk>/resumption", v.ResumptionView.as_view(), name="leave-application-resumption"),

    # Substitute views
    path("substitute/<int:pk>/respond", v.SubstituteRespondView.as_view(), name="leave-substitute-respond"),

    # Unit head views
    path("unit-head/queue", v.UnitHeadQueueView.as_view(), name="leave-unit-head-queue"),
    path("unit-head/<int:pk>/decide", v.UnitHeadDecideView.as_view(), name="leave-unit-head-decide"),

    # Admin views
    path("admin/applications", v.AdminApplicationsView.as_view(), name="leave-admin-applications"),
    path("admin/offline", v.AdminOfflineRecordView.as_view(), name="leave-admin-offline"),
    path("admin/policy", v.PolicyView.as_view(), name="leave-admin-policy"),
    path("admin/calendar", v.HolidayCalendarView.as_view(), name="leave-admin-calendar"),
    path("admin/calendar/<int:pk>", v.HolidayCalendarView.as_view(), name="leave-admin-calendar-detail"),
]
