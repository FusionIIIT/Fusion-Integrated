from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("applications", views.ApplicationListView.as_view(), name="leave-applications"),
    path("applications/<int:pk>", views.ApplicationDetailView.as_view(), name="leave-application"),
    path("applications/<int:pk>/action", views.ApplicationActionView.as_view(),
         name="leave-application-action"),
    path("applications/<int:pk>/export", views.ApplicationExportView.as_view(),
         name="leave-application-export"),
    path("cancellations", views.CancellationView.as_view(), name="leave-cancellations"),
    path("extensions", views.ExtensionView.as_view(), name="leave-extensions"),
    path("tasks", views.AssignedTasksView.as_view(), name="leave-tasks"),
    path("balances", views.BalanceView.as_view(), name="leave-balances"),
    path("resumptions", views.ResumptionListCreateView.as_view(), name="leave-resumptions"),
    path("resumptions/<int:pk>/review", views.ResumptionReviewView.as_view(),
         name="leave-resumption-review"),
    path("admin/policies", views.PolicyView.as_view(), name="leave-policies"),
    path("admin/routes", views.AuthorityRouteView.as_view(), name="leave-routes"),
    path("admin/calendars", views.CalendarView.as_view(), name="leave-calendars"),
    path("admin/calendars/<int:pk>/publish", views.CalendarPublishView.as_view(),
         name="leave-calendar-publish"),
    path("admin/offline-leave", views.OfflineLeaveView.as_view(), name="leave-offline"),
    path("admin/record-corrections", views.RecordCorrectionView.as_view(),
         name="leave-record-corrections"),
    path("admin/sla", views.SlaConfigurationView.as_view(), name="leave-sla"),
    path("notifications", views.NotificationStatusView.as_view(), name="leave-notifications"),
]
