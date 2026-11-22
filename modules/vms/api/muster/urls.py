from django.urls import path

from modules.vms.api.muster import views

urlpatterns = [
    path("muster", views.MusterTriggerView.as_view(), name="vms-muster-trigger"),
    path("muster/current", views.MusterCurrentView.as_view(), name="vms-muster-current"),
    path("muster/<int:pk>", views.MusterDetailView.as_view(), name="vms-muster-detail"),
    path("muster/<int:pk>/roster", views.MusterRosterView.as_view(), name="vms-muster-roster"),
    path("muster/<int:pk>/roll-call", views.RollCallView.as_view(), name="vms-muster-roll-call"),
    path("muster/<int:pk>/roll-call/bulk", views.BulkRollCallView.as_view(),
         name="vms-muster-roll-call-bulk"),
    path("muster/<int:pk>/reconcile", views.ReconcileView.as_view(), name="vms-muster-reconcile"),
    path("muster/<int:pk>/close", views.CloseView.as_view(), name="vms-muster-close"),
    path("muster/<int:pk>/report", views.ReportView.as_view(), name="vms-muster-report"),
    path("muster/<int:pk>/report.csv", views.ReportCsvView.as_view(),
         name="vms-muster-report-csv"),
]
