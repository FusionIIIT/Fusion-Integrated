"""URL routing for PHC module."""
from django.urls import path

from .views import (
    AmbulanceLogView,
    DoctorAttendanceView,
    DoctorAvailabilityView,
    DoctorManageView,
    DoctorScheduleManageView,
    DoctorSchedulePublishView,
    HealthAnnouncementView,
    InventoryItemListView,
    InventoryStockAdjustmentView,
    PatientMedicalHistoryView,
    PatientPrescriptionsView,
    PatientRecordDownloadView,
    PatientVisitsManageView,
    PHCAuditTrailView,
    PHCNotificationView,
    PHCReportView,
    PrescriptionManageView,
    ProcurementRequisitionDecisionView,
    ProcurementRequisitionFulfillView,
    ProcurementRequisitionView,
    ReimbursementClaimDetailView,
    ReimbursementClaimSubmitView,
    ReimbursementClaimTrackingView,
    ReimbursementPaymentView,
    ReimbursementReviewForwardView,
    ReimbursementReviewQueueView,
    ReimbursementSanctionView,
    ReimbursementVerifyView,
)

urlpatterns = [
    # Doctor Schedule & Attendance
    path("doctors/availability/", DoctorAvailabilityView.as_view(), name="phc-doctor-availability"),
    path("doctors/", DoctorManageView.as_view(), name="phc-doctor-manage"),
    path("doctors/schedules/", DoctorScheduleManageView.as_view(), name="phc-schedule-manage"),
    path("doctors/schedules/publish/", DoctorSchedulePublishView.as_view(), name="phc-schedule-publish"),
    path("doctors/attendance/", DoctorAttendanceView.as_view(), name="phc-doctor-attendance"),

    # Patient Clinical Records
    path("patient/history/", PatientMedicalHistoryView.as_view(), name="phc-patient-history"),
    path("patient/prescriptions/", PatientPrescriptionsView.as_view(), name="phc-patient-prescriptions"),
    path("patient/download/", PatientRecordDownloadView.as_view(), name="phc-patient-download"),
    path("staff/visits/", PatientVisitsManageView.as_view(), name="phc-staff-visits"),
    path("staff/prescriptions/", PrescriptionManageView.as_view(), name="phc-staff-prescriptions"),

    # Medical Bill Reimbursements
    path("reimbursements/submit/", ReimbursementClaimSubmitView.as_view(), name="phc-reimbursement-submit"),
    path("reimbursements/mine/", ReimbursementClaimTrackingView.as_view(), name="phc-reimbursement-mine"),
    path("reimbursements/queue/", ReimbursementReviewQueueView.as_view(), name="phc-reimbursement-queue"),
    path("reimbursements/<int:pk>/", ReimbursementClaimDetailView.as_view(), name="phc-reimbursement-detail"),
    path("reimbursements/<int:pk>/forward/", ReimbursementReviewForwardView.as_view(), name="phc-reimbursement-forward"),
    path("reimbursements/<int:pk>/verify/", ReimbursementVerifyView.as_view(), name="phc-reimbursement-verify"),
    path("reimbursements/<int:pk>/sanction/", ReimbursementSanctionView.as_view(), name="phc-reimbursement-sanction"),
    path("reimbursements/<int:pk>/pay/", ReimbursementPaymentView.as_view(), name="phc-reimbursement-pay"),

    # Inventory & Procurement Requisitions
    path("inventory/items/", InventoryItemListView.as_view(), name="phc-inventory-items"),
    path("inventory/adjust/", InventoryStockAdjustmentView.as_view(), name="phc-inventory-adjust"),
    path("inventory/requisitions/", ProcurementRequisitionView.as_view(), name="phc-requisitions"),
    path("inventory/requisitions/<int:pk>/decide/", ProcurementRequisitionDecisionView.as_view(), name="phc-requisitions-decide"),
    path("inventory/requisitions/<int:pk>/fulfill/", ProcurementRequisitionFulfillView.as_view(), name="phc-requisitions-fulfill"),

    # Ambulance & Announcements
    path("ambulance/", AmbulanceLogView.as_view(), name="phc-ambulance"),
    path("announcements/", HealthAnnouncementView.as_view(), name="phc-announcements"),

    # Reports, Audit, Notifications
    path("reports/", PHCReportView.as_view(), name="phc-reports"),
    path("audit/", PHCAuditTrailView.as_view(), name="phc-audit"),
    path("notifications/", PHCNotificationView.as_view(), name="phc-notifications"),
]
