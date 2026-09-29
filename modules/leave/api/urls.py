from django.urls import path

from modules.leave.api import views

app_name = "leave"

urlpatterns = [
    path("me/requests", views.MyLeaveView.as_view(), name="my-requests"),
    path("me/balances", views.MyBalanceView.as_view(), name="my-balances"),
    path("me/statement/<str:category>", views.StatementView.as_view(), name="statement"),
    path("requests", views.ApplyView.as_view(), name="apply"),
    path("requests/<int:pk>", views.LeaveDetailView.as_view(), name="detail"),
    path("requests/<int:pk>/trail", views.TrailView.as_view(), name="trail"),
    path("requests/<int:pk>/withdraw", views.WithdrawView.as_view(), name="withdraw"),
    path("requests/<int:pk>/cancel", views.CancellationView.as_view(), name="cancel"),
    path("requests/<int:pk>/extend", views.ExtensionView.as_view(), name="extend"),
    path(
        "requests/<int:pk>/renominate",
        views.RenominateView.as_view(),
        name="renominate",
    ),
    path("requests/<int:pk>/resumption", views.ResumptionView.as_view(), name="resumption"),
    path("nominations", views.NominationsView.as_view(), name="nominations"),
    path(
        "nominations/<int:pk>/respond",
        views.SubstituteRespondView.as_view(),
        name="nomination-respond",
    ),
    path("review", views.ReviewQueueView.as_view(), name="review-queue"),
    path("review/<int:pk>", views.ReviewDecisionView.as_view(), name="review-decide"),
    path("routing", views.RoutingQueueView.as_view(), name="routing-queue"),
    path("routing/<int:pk>", views.RouteView.as_view(), name="route"),
    path("sanction", views.SanctionQueueView.as_view(), name="sanction-queue"),
    path("sanction/<int:pk>", views.SanctionView.as_view(), name="sanction"),
    path("resumptions", views.ResumptionQueueView.as_view(), name="resumption-queue"),
    path(
        "resumptions/<int:pk>/verify",
        views.VerifyResumptionView.as_view(),
        name="resumption-verify",
    ),
    path("balances", views.BalanceDirectoryView.as_view(), name="balance-directory"),

    path("admin/policies", views.PolicyAdminView.as_view(), name="policies"),
    path("admin/policies/<int:pk>/rules", views.PolicyRulesView.as_view(), name="policy-rules"),
    path(
        "admin/policies/<int:pk>/publish",
        views.PolicyPublishView.as_view(),
        name="policy-publish",
    ),
    path(
        "admin/policies/<int:pk>/authority",
        views.PolicyAuthorityView.as_view(),
        name="policy-authority",
    ),
    path("admin/policies/<int:pk>/sla", views.PolicySlaView.as_view(),
         name="policy-sla"),
    path(
        "admin/policies/<int:pk>/readiness",
        views.PolicyReadinessView.as_view(),
        name="policy-readiness",
    ),
    path("admin/calendars", views.CalendarAdminView.as_view(), name="calendars"),
    path(
        "admin/calendars/<int:pk>/holidays",
        views.CalendarHolidaysView.as_view(),
        name="calendar-holidays",
    ),
    path(
        "admin/calendars/<int:pk>/vacations",
        views.CalendarVacationsView.as_view(),
        name="calendar-vacations",
    ),
    path(
        "admin/calendars/<int:pk>/publish",
        views.CalendarPublishView.as_view(),
        name="calendar-publish",
    ),
    path("admin/offline", views.OfflineRecordView.as_view(), name="offline-record"),
]
