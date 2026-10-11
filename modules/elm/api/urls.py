from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # employee
    path("balances", v.BalanceView.as_view(), name="elm-balances"),
    path("requests", v.MyRequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="elm-request-withdraw"),
    path("requests/<int:pk>/cancel", v.CancelView.as_view(),
         name="elm-request-cancel"),
    path("requests/<int:pk>/extend", v.ExtendView.as_view(),
         name="elm-request-extend"),
    path("requests/<int:pk>/resume", v.ResumeView.as_view(),
         name="elm-request-resume"),
    path("requests/<int:pk>/substitute", v.RenominateView.as_view(),
         name="elm-request-substitute"),
    path("substitute-requests", v.SubstituteTaskListView.as_view(),
         name="elm-substitute-requests"),
    path("substitute-requests/<int:pk>/respond", v.SubstituteRespondView.as_view(),
         name="elm-substitute-respond"),
    path("notifications", v.NotificationListView.as_view(),
         name="elm-notifications"),
    path("employees", v.EmployeeSearchView.as_view(), name="elm-employees"),
    path("calendar", v.PublishedCalendarView.as_view(), name="elm-calendar"),

    # reviewers
    path("tasks", v.TaskListView.as_view(), name="elm-tasks"),
    path("tasks/<int:pk>/decide", v.DecideView.as_view(), name="elm-task-decide"),

    # administration
    path("admin/policy", v.CategoryPolicyView.as_view(), name="elm-admin-policy"),
    path("admin/unit-heads", v.UnitHeadView.as_view(), name="elm-admin-unit-heads"),
    path("admin/routes", v.SanctionRouteView.as_view(), name="elm-admin-routes"),
    path("admin/sla", v.SlaPolicyView.as_view(), name="elm-admin-sla"),
    path("admin/calendars", v.CalendarListView.as_view(),
         name="elm-admin-calendars"),
    path("admin/calendars/<int:pk>/holidays", v.HolidayCreateView.as_view(),
         name="elm-admin-holidays"),
    path("admin/calendars/<int:pk>/holidays/<int:holiday_id>",
         v.HolidayDeleteView.as_view(), name="elm-admin-holiday"),
    path("admin/calendars/<int:pk>/publish", v.CalendarPublishView.as_view(),
         name="elm-admin-calendar-publish"),
    path("admin/vacations", v.VacationPeriodView.as_view(),
         name="elm-admin-vacations"),
    path("admin/offline-records", v.OfflineRecordView.as_view(),
         name="elm-admin-offline"),
    path("admin/adjustments", v.AdjustmentView.as_view(),
         name="elm-admin-adjustments"),
]
