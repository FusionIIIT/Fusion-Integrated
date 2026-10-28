from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    # employee
    path("requests", v.MyLeaveListView.as_view(), name="leave-requests"),
    path("requests/apply", v.ApplyLeaveView.as_view(), name="leave-apply"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="leave-withdraw"),
    path("requests/<int:pk>/cancel", v.CancelRequestView.as_view(),
         name="leave-cancel"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(),
         name="leave-extension"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(),
         name="leave-resumption"),
    path("requests/<int:pk>/cover", v.SubstituteRespondView.as_view(),
         name="leave-cover-respond"),
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),

    # sanctioning / administrative
    path("queue", v.ApprovalQueueView.as_view(), name="leave-queue"),
    path("requests/<int:pk>/recommend", v.RecommendView.as_view(),
         name="leave-recommend"),
    path("requests/<int:pk>/sanction", v.SanctionView.as_view(),
         name="leave-sanction"),
    path("records/offline", v.OfflineLeaveView.as_view(),
         name="leave-offline-record"),
    path("calendar", v.CalendarView.as_view(), name="leave-calendar"),
    path("calendar/vacations", v.VacationView.as_view(),
         name="leave-vacations"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("reports", v.LeaveReportView.as_view(), name="leave-reports"),
]
