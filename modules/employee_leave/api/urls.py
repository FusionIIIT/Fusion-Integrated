from django.urls import path

from modules.employee_leave.api import views

urlpatterns = [
    path("requests", views.LeaveRequestListCreateView.as_view(), name="elm-requests"),
    path(
        "requests/<int:pk>/actions",
        views.LeaveRequestActionView.as_view(),
        name="elm-request-action",
    ),
    path(
        "requests/<int:pk>/extensions",
        views.LeaveExtensionView.as_view(),
        name="elm-request-extension",
    ),
    path(
        "requests/<int:pk>/print", views.LeaveRequestPrintView.as_view(), name="elm-request-print"
    ),
    path("tasks", views.LeaveTaskQueueView.as_view(), name="elm-tasks"),
    path("notices", views.LeaveTaskNoticeListView.as_view(), name="elm-notices"),
    path("notices/<int:pk>/read", views.LeaveTaskNoticeReadView.as_view(), name="elm-notice-read"),
    path("balances", views.LeaveBalanceView.as_view(), name="elm-balances"),
    path("balances/adjust", views.LeaveBalanceAdjustmentView.as_view(), name="elm-balance-adjust"),
    path("requests/offline", views.OfflineLeaveView.as_view(), name="elm-offline-leave"),
    path("year-end", views.LeaveYearEndView.as_view(), name="elm-year-end"),
    path("policies", views.LeavePolicyView.as_view(), name="elm-policies"),
    path("policies/<int:pk>", views.LeavePolicyDetailView.as_view(), name="elm-policy-detail"),
    path("calendar", views.LeaveHolidayView.as_view(), name="elm-calendar"),
    path(
        "calendar/<int:pk>/publish",
        views.LeaveHolidayPublishView.as_view(),
        name="elm-calendar-publish",
    ),
]
