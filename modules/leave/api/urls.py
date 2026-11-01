from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    path("balances", v.BalanceView.as_view()),
    path("applications", v.ApplicationListView.as_view()),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view()),
    path("applications/<int:pk>/history", v.ApplicationHistoryView.as_view()),
    path("applications/<int:pk>/withdraw", v.WithdrawView.as_view()),
    path("applications/<int:pk>/cancel", v.CancellationView.as_view()),
    path("applications/<int:pk>/extend", v.ExtensionView.as_view()),
    path("applications/<int:pk>/substitute", v.SubstituteResponseView.as_view()),
    path("applications/<int:pk>/replacement", v.ReplacementView.as_view()),
    path("applications/<int:pk>/decision", v.DecisionView.as_view()),
    path("applications/<int:pk>/export", v.ExportView.as_view()),
    path("applications/<int:pk>/resumption", v.ResumptionCreateView.as_view()),
    path("resumptions/<int:pk>/review", v.ResumptionReviewView.as_view()),
    path("admin/offline", v.OfflineLeaveView.as_view()),
    path("notifications", v.NotificationListView.as_view()),
    path("configuration/policies", v.PolicyView.as_view()),
    path("configuration/calendars", v.CalendarView.as_view()),
    path("configuration/calendars/<int:pk>/publish", v.CalendarPublishView.as_view()),
    path("year-end", v.YearEndView.as_view()),
]
