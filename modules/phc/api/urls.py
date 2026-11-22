from django.urls import path

from modules.phc.api import views as v

urlpatterns = [
    path("schedules", v.ScheduleListView.as_view()),
    path("schedules/<int:pk>", v.ScheduleDetailView.as_view()),
    path("schedules/<int:pk>/publish", v.SchedulePublishView.as_view()),
    path("schedules/<int:pk>/attendance", v.AttendanceView.as_view()),
    path("patients", v.PatientSearchView.as_view()),
    path("records", v.VisitListView.as_view()),
    path("records/pdf", v.RecordsPdfView.as_view()),
    path("records/<int:pk>", v.VisitDetailView.as_view()),
    path("claims", v.ClaimListView.as_view()),
    path("claims/prescriptions", v.ClaimPrescriptionsView.as_view()),
    path("claims/<int:pk>", v.ClaimDetailView.as_view()),
    path("claims/<int:pk>/transition", v.ClaimTransitionView.as_view()),
    path("inventory", v.InventoryListView.as_view()),
    path("inventory/alerts", v.LowStockAlertListView.as_view()),
    path("inventory/<int:pk>/adjust", v.StockAdjustView.as_view()),
    path("requisitions", v.RequisitionListView.as_view()),
    path("requisitions/<int:pk>/transition", v.RequisitionTransitionView.as_view()),
    path("ambulance", v.AmbulanceListView.as_view()),
    path("advisories", v.AdvisoryListView.as_view()),
    path("reports", v.ReportView.as_view()),
    path("notifications", v.NotificationListView.as_view()),
]
