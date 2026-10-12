from django.urls import path

from modules.elm.api import views

urlpatterns = [
    # policy & hierarchy
    path("policies", views.PolicyListView.as_view(), name="elm-policy-list"),
    path("policies/<int:pk>", views.PolicyDetailView.as_view(), name="elm-policy-detail"),
    path(
        "policies/<int:policy_pk>/hierarchy",
        views.PolicyHierarchyView.as_view(),
        name="elm-hierarchy-list",
    ),
    path(
        "policies/<int:policy_pk>/hierarchy/<int:level_pk>",
        views.PolicyHierarchyDetailView.as_view(),
        name="elm-hierarchy-detail",
    ),

    # holiday / RH calendar & vacation
    path("calendars", views.HolidayCalendarListView.as_view(), name="elm-calendar-list"),
    path("calendars/<int:pk>", views.HolidayCalendarDetailView.as_view(), name="elm-calendar-detail"),
    path(
        "calendars/<int:calendar_pk>/entries",
        views.HolidayEntryListView.as_view(),
        name="elm-calendar-entry-list",
    ),
    path(
        "calendars/<int:calendar_pk>/entries/<int:entry_pk>",
        views.HolidayEntryDetailView.as_view(),
        name="elm-calendar-entry-detail",
    ),
    path("vacation-periods", views.VacationPeriodListView.as_view(), name="elm-vacation-list"),
    path(
        "vacation-periods/<int:pk>",
        views.VacationPeriodDetailView.as_view(),
        name="elm-vacation-detail",
    ),

    # leave requests
    path("applications", views.LeaveApplicationListView.as_view(), name="elm-application-list"),
    path("applications/<int:pk>", views.LeaveApplicationDetailView.as_view(), name="elm-application-detail"),
    path("applications/<int:pk>/consent", views.SubmitSubstituteConsentView.as_view(), name="elm-consent"),
    path("applications/<int:pk>/decision", views.DecisionView.as_view(), name="elm-decision"),
    path("applications/<int:pk>/withdraw", views.WithdrawPendingView.as_view(), name="elm-withdraw"),
    path("applications/<int:pk>/cancel", views.RequestCancellationView.as_view(), name="elm-cancel"),
    path("applications/<int:pk>/extend", views.ExtensionView.as_view(), name="elm-extend"),
    path("applications/<int:pk>/resumption", views.ResumptionView.as_view(), name="elm-resumption"),

    # balance & offline
    path("balances/<int:pk>", views.LeaveBalanceDetailView.as_view(), name="elm-balance-detail"),
    path("offline-leave", views.OfflineLeaveEntryView.as_view(), name="elm-offline-leave"),

    # roles
    path("roles", views.RoleListView.as_view(), name="elm-role-list"),
    path("role-grants", views.RoleGrantListView.as_view(), name="elm-role-grant-list"),
    path("role-grants/<int:pk>", views.RoleGrantDeleteView.as_view(), name="elm-role-grant-delete"),

    # SLA
    path("sla", views.SLAConfigurationListView.as_view(), name="elm-sla-list"),
    path("sla/<int:pk>", views.SLAConfigurationDetailView.as_view(), name="elm-sla-detail"),
]
