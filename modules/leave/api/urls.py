from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("applications", v.MyLeaveView.as_view(), name="leave-applications"),
    path("applications/apply", v.ApplyView.as_view(), name="leave-apply"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="leave-withdraw"),
    path("applications/<int:pk>/cancel", v.CancellationView.as_view(),
         name="leave-cancel"),
    path("applications/<int:pk>/resumption", v.ResumptionView.as_view(),
         name="leave-resumption"),
    path("nominations", v.NominationListView.as_view(), name="leave-nominations"),
    path("nominations/<int:pk>/respond", v.NominationResponseView.as_view(),
         name="leave-nomination-respond"),
    path("requests", v.ReviewQueueView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/review", v.ReviewView.as_view(), name="leave-review"),
    path("sanctions", v.SanctionQueueView.as_view(), name="leave-sanctions"),
    path("sanctions/<int:pk>/decision", v.SanctionView.as_view(),
         name="leave-sanction"),
    path("holidays", v.HolidayCalendarView.as_view(), name="leave-holidays"),
]
