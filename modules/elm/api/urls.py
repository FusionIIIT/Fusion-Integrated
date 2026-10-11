from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("leave-requests", views.LeaveRequestListCreateView.as_view(), name="elm-leave-requests"),
    path("leave-requests/<int:pk>", views.LeaveRequestDetailView.as_view(), name="elm-leave-request"),
    path("leave-requests/<int:pk>/substitute-response", views.SubstituteResponseView.as_view(), name="elm-substitute-response"),
    path("leave-requests/<int:pk>/retry", views.RetryAfterDeclineView.as_view(), name="elm-retry-after-decline"),
    path("leave-requests/<int:pk>/decision", views.LeaveDecisionView.as_view(), name="elm-leave-decision"),
    path("leave-requests/<int:pk>/withdraw", views.WithdrawRequestView.as_view(), name="elm-leave-withdraw"),
    path("leave-requests/<int:pk>/cancel", views.CancelLeaveView.as_view(), name="elm-leave-cancel"),
    path("leave-requests/<int:pk>/extend", views.ExtendLeaveView.as_view(), name="elm-leave-extend"),
    path("leave-requests/<int:pk>/resume", views.ResumptionView.as_view(), name="elm-leave-resumption"),
    path("leave-requests/<int:pk>/export", views.LeaveApplicationExportView.as_view(), name="elm-leave-export"),
    path("balances", views.LeaveBalanceView.as_view(), name="elm-leave-balances"),
    path("policies", views.LeavePolicyView.as_view(), name="elm-leave-policies"),
    path("policies/<str:category>", views.LeavePolicyView.as_view(), name="elm-leave-policy"),
    path("calendars", views.LeaveCalendarView.as_view(), name="elm-calendars"),
    path("calendars/<int:pk>/dates", views.LeaveCalendarDateView.as_view(), name="elm-calendar-dates"),
    path("calendars/<int:pk>/publish", views.PublishLeaveCalendarView.as_view(), name="elm-calendar-publish"),
    path("hierarchy", views.LeaveHierarchyView.as_view(), name="elm-hierarchy"),
    path("vacation-periods", views.VacationPeriodListCreateView.as_view(), name="elm-vacation-periods"),
    path("vacation-periods/<int:pk>", views.VacationPeriodDetailView.as_view(), name="elm-vacation-period"),
    path("offline-records", views.OfflineLeaveRecordView.as_view(), name="elm-offline-record"),
    path("sla-config", views.LeaveSLAConfigView.as_view(), name="elm-sla-config"),
    path("sla/process", views.ProcessSLAView.as_view(), name="elm-sla-process"),
    path("year-end/process", views.LeaveYearEndView.as_view(), name="elm-year-end-process"),
    path("notices", views.LeaveNoticesView.as_view(), name="elm-notices"),
]
