from django.urls import path
from modules.phc.api.views import (
    InventoryListView, InventoryCreateView, InventoryAdjustView,
    RequisitionListView, RequisitionDetailView, RequisitionDecideView, RequisitionFulfillView,
    PatientVisitListView, PatientVisitCreateView, PrescriptionListView, MedicalRecordExportView
)

urlpatterns = [
    path("inventory", InventoryListView.as_view(), name="inventory-list"),
    path("inventory/create", InventoryCreateView.as_view(), name="inventory-create"),
    path("inventory/<int:pk>/adjust", InventoryAdjustView.as_view(), name="inventory-adjust"),
    path("requisitions", RequisitionListView.as_view(), name="requisition-list"),
    path("requisitions/<int:pk>", RequisitionDetailView.as_view(), name="requisition-detail"),
    path("requisitions/<int:pk>/decide", RequisitionDecideView.as_view(), name="requisition-decide"),
    path("requisitions/<int:pk>/fulfil", RequisitionFulfillView.as_view(), name="requisition-fulfil"),
    path("patients/<int:user_id>/records", PatientVisitListView.as_view(), name="patient-visit-list"),
    path("patients/<int:user_id>/visits", PatientVisitCreateView.as_view(), name="patient-visit-create"),
    path("me/records", PrescriptionListView.as_view(), name="medical-record-list"),
    path("me/records/export", MedicalRecordExportView.as_view(), name="medical-record-export"),
]
