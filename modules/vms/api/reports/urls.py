from django.urls import path

from modules.vms.api.reports import views as v

urlpatterns = [
    path("reports", v.ReportCatalogueView.as_view(), name="vms-reports"),
    path("reports/<str:key>", v.ReportRunView.as_view(), name="vms-report"),
    path("reports/<str:key>/export", v.ReportExportView.as_view(), name="vms-report-export"),
]
