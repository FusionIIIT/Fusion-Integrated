"""Versioned ELM endpoints."""
from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("employees", views.EmployeeSearchView.as_view(), name="leave-employee-search"),
    path("categories", views.CategoryListView.as_view(), name="leave-categories"),
    path("balances", views.BalanceListView.as_view(), name="leave-balances"),
    path("accounts", views.AccountHistoryView.as_view(), name="leave-account-history"),
    path("requests", views.RequestListCreateView.as_view(), name="leave-requests"),
    path("requests/<int:pk>", views.RequestDetailView.as_view(), name="leave-request"),
    path("requests/<int:pk>/history", views.RequestHistoryView.as_view(), name="leave-request-history"),
    path("requests/<int:pk>/submit", views.SubmitView.as_view(), name="leave-request-submit"),
    path("requests/<int:pk>/withdraw", views.WithdrawView.as_view(), name="leave-request-withdraw"),
    path("requests/<int:pk>/cancel", views.CancellationView.as_view(), name="leave-request-cancel"),
    path("requests/<int:pk>/extend", views.ExtensionView.as_view(), name="leave-request-extend"),
    path("requests/<int:pk>/resumption", views.ResumptionView.as_view(), name="leave-request-resumption"),
    path("requests/<int:pk>/print", views.RequestPrintView.as_view(), name="leave-request-print"),
    path("requests/<int:pk>/substitute-response", views.SubstituteResponseView.as_view(), name="leave-substitute-response"),
    path("requests/<int:pk>/replace-substitute", views.ReplaceSubstituteView.as_view(), name="leave-replace-substitute"),
    path("substitutions", views.SubstituteInboxView.as_view(), name="leave-substitute-inbox"),
    path("tasks", views.TaskListView.as_view(), name="leave-tasks"),
    path("tasks/<int:pk>/decision", views.TaskDecisionView.as_view(), name="leave-task-decision"),
    path("policy", views.PolicyView.as_view(), name="leave-policy"),
    path("calendars", views.HolidayCalendarListView.as_view(), name="leave-holiday-calendars"),
    path("calendars/drafts", views.HolidayCalendarDraftView.as_view(), name="leave-calendar-drafts"),
    path("calendars/<int:pk>/publish", views.HolidayCalendarPublishView.as_view(), name="leave-calendar-publish"),
    path("configuration/routes", views.RouteConfigurationListView.as_view(), name="leave-route-configurations"),
    path("configuration/routes/<int:pk>", views.RouteConfigurationDetailView.as_view(), name="leave-route-configuration"),
    path("configuration/sla", views.SLAConfigurationListView.as_view(), name="leave-sla-configurations"),
    path("configuration/sla/<int:pk>", views.SLAConfigurationDetailView.as_view(), name="leave-sla-configuration"),
    path("admin/offline-leave", views.OfflineLeaveView.as_view(), name="leave-offline-record"),
    path("admin/account-adjustments", views.AccountAdjustmentView.as_view(), name="leave-account-adjustment"),
]
