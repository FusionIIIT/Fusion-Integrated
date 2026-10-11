"""ELM API route table."""

from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("requests", views.MyRequestsView.as_view(), name="elm-requests"),
    path("requests/<int:pk>/withdraw", views.WithdrawView.as_view(), name="elm-request-withdraw"),
    path(
        "requests/<int:pk>/substitute",
        views.SubstituteResponseView.as_view(),
        name="elm-substitute-response",
    ),
    path(
        "requests/<int:pk>/cancellations", views.CancellationView.as_view(), name="elm-cancellation"
    ),
    path("requests/<int:pk>/extensions", views.ExtensionView.as_view(), name="elm-extension"),
    path("requests/<int:pk>/resumption", views.ResumptionView.as_view(), name="elm-resumption"),
    path("requests/<int:pk>/review", views.ReviewView.as_view(), name="elm-review"),
    path(
        "resumptions/<int:pk>/review",
        views.ResumptionReviewView.as_view(),
        name="elm-resumption-review",
    ),
    path("balances", views.MyBalancesView.as_view(), name="elm-balances"),
    path("tasks", views.TasksView.as_view(), name="elm-tasks"),
    path("notifications", views.NotificationsView.as_view(), name="elm-notifications"),
    path("export.csv", views.ExportView.as_view(), name="elm-export"),
    path("admin/categories", views.CategoriesAdminView.as_view(), name="elm-admin-categories"),
    path(
        "admin/employee-contexts",
        views.EmployeeContextAdminView.as_view(),
        name="elm-admin-employee-contexts",
    ),
    path("admin/routes", views.ApprovalRoutesAdminView.as_view(), name="elm-admin-routes"),
    path("admin/calendars", views.CalendarAdminView.as_view(), name="elm-admin-calendars"),
    path(
        "admin/calendars/<int:pk>/entries",
        views.CalendarEntryAdminView.as_view(),
        name="elm-admin-calendar-entry",
    ),
    path(
        "admin/calendars/<int:pk>/publish",
        views.CalendarPublishAdminView.as_view(),
        name="elm-admin-calendar-publish",
    ),
    path("admin/vacations", views.VacationAdminView.as_view(), name="elm-admin-vacations"),
    path("admin/accounts", views.AccountsAdminView.as_view(), name="elm-admin-accounts"),
    path(
        "admin/accounts/adjustments",
        views.AccountAdjustmentAdminView.as_view(),
        name="elm-admin-account-adjustment",
    ),
    path(
        "admin/records/offline",
        views.OfflineRecordAdminView.as_view(),
        name="elm-admin-offline-record",
    ),
    path("admin/sla", views.SLAAdminView.as_view(), name="elm-admin-sla"),
    path("admin/audit", views.AdminAuditView.as_view(), name="elm-admin-audit"),
]
