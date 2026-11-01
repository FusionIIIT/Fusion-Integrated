from django.urls import path
from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.RequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="elm-request-detail"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(), name="elm-withdraw"),
    path("requests/<int:pk>/cancel", v.CancellationView.as_view(), name="elm-cancel"),
    path("requests/<int:pk>/extend", v.ExtensionView.as_view(), name="elm-extend"),
    path("requests/<int:pk>/resume", v.ResumptionSubmitView.as_view(), name="elm-resume"),
    path("requests/<int:pk>/substitute", v.ReplacementSubstituteView.as_view(), name="elm-replacement-substitute"),
    path("requests/<int:pk>/print", v.PrintView.as_view(), name="elm-print"),
    path("requests/<int:pk>/history", v.HistoryView.as_view(), name="elm-history"),
    path("substitutions", v.SubstitutionListView.as_view(), name="elm-substitutions"),
    path("substitutions/<int:pk>/respond", v.SubstituteResponseView.as_view(), name="elm-substitute-response"),
    path("queue", v.QueueView.as_view(), name="elm-queue"),
    path("queue/<int:pk>/decide", v.DecideView.as_view(), name="elm-decide"),
    path("balances", v.BalanceView.as_view(), name="elm-balances"),
    path("admin/policies", v.PolicyView.as_view(), name="elm-policy"),
    path("admin/calendars", v.CalendarListView.as_view(), name="elm-calendars"),
    path("admin/calendars/<int:pk>", v.CalendarDetailView.as_view(), name="elm-calendar-detail"),
    path("admin/calendars/<int:pk>/publish", v.CalendarPublishView.as_view(), name="elm-calendar-publish"),
    path("admin/offline", v.OfflineView.as_view(), name="elm-offline"),
    path("admin/offline/<int:pk>", v.OfflineRecordDetailView.as_view(), name="elm-offline-detail"),
    path("admin/sla", v.SlaConfigView.as_view(), name="elm-sla-config"),
    path("notifications", v.NotificationView.as_view(), name="elm-notifications"),
    path("resumptions", v.ResumptionQueueView.as_view(), name="elm-resumptions"),
    path("resumptions/<int:pk>/verify", v.ResumptionVerifyView.as_view(), name="elm-resumption-verify"),
]
