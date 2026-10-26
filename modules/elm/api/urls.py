from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("applications", v.ApplicationsView.as_view(), name="elm-applications"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="elm-application"),
    path("applications/<int:pk>/modify", v.ModifyView.as_view(), name="elm-modify"),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view(), name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancelView.as_view(), name="elm-cancel"),
    path("applications/<int:pk>/extend", v.ExtendView.as_view(), name="elm-extend"),
    path("applications/<int:pk>/resume", v.ResumeView.as_view(), name="elm-resume"),
    path("applications/<int:pk>/substitute-response", v.SubstituteResponseView.as_view(),
         name="elm-substitute-response"),
    path("applications/<int:pk>/unit-head", v.UnitHeadView.as_view(), name="elm-unit-head"),
    path("applications/<int:pk>/route", v.RouteView.as_view(), name="elm-route"),
    path("applications/<int:pk>/sanction", v.SanctionView.as_view(), name="elm-sanction"),
    path("applications/<int:pk>/self-sanction", v.SelfSanctionView.as_view(),
         name="elm-self-sanction"),
    path("applications/<int:pk>/verify-resumption", v.VerifyResumptionView.as_view(),
         name="elm-verify-resumption"),
    path("tasks", v.TasksView.as_view(), name="elm-tasks"),
    path("balances", v.BalancesView.as_view(), name="elm-balances"),
    path("notifications", v.NotificationsView.as_view(), name="elm-notifications"),
    path("calendar", v.CalendarView.as_view(), name="elm-calendar"),
    path("offline", v.OfflineView.as_view(), name="elm-offline"),
    path("year-end", v.YearEndView.as_view(), name="elm-year-end"),
]
