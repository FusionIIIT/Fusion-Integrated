from django.urls import path

from modules.phc.api import views as v

urlpatterns = [
    # ---- Doctor schedule & availability (CFR-001 / AFR-001..005) --------
    path("schedule", v.DoctorScheduleListView.as_view(),
         name="phc-schedule"),

    path("staff/schedule", v.DoctorScheduleCreateView.as_view(),
         name="phc-staff-schedule-create"),
    path("staff/schedule/<int:pk>", v.DoctorScheduleMaintainView.as_view(),
         name="phc-staff-schedule-maintain"),
    path("staff/schedule/<int:pk>/publish",
         v.DoctorSchedulePublishView.as_view(),
         name="phc-staff-schedule-publish"),
    path("staff/attendance", v.DoctorAttendanceMarkView.as_view(),
         name="phc-staff-attendance"),

    # ---- Patient records & prescriptions (CFR-002 / AFR-006..012) ------
    path("staff/patients/search", v.PatientSearchView.as_view(),
         name="phc-patient-search"),
    path("staff/visits", v.VisitCreateView.as_view(),
         name="phc-visit-create"),
    path("staff/prescriptions", v.PrescriptionCreateView.as_view(),
         name="phc-prescription-create"),
    path("records", v.PatientRecordsView.as_view(),
         name="phc-patient-records"),
    path("records/prescriptions", v.PatientPrescriptionsView.as_view(),
         name="phc-patient-prescriptions"),
    path("records/download/<int:pk>", v.RecordDownloadView.as_view(),
         name="phc-record-download"),

    # ---- Reimbursement (CFR-003, CFR-004, CFR-005 / AFR-013..023, 038)-
    path("claims", v.ReimbursementClaimCreateView.as_view(),
         name="phc-claim-create"),
    path("claims/mine", v.MyClaimsView.as_view(),
         name="phc-claims-mine"),
    path("staff/claims/<int:pk>/review", v.ClaimReviewView.as_view(),
         name="phc-claim-review"),
    path("audit/claims/<int:pk>/verify", v.ClaimVerifyView.as_view(),
         name="phc-claim-verify"),
    path("approver/claims/<int:pk>/sanction", v.ClaimSanctionView.as_view(),
         name="phc-claim-sanction"),
    path("audit/claims/<int:pk>/payment", v.ClaimPaymentView.as_view(),
         name="phc-claim-payment"),

    # ---- Inventory & procurement (CFR-006, CFR-007 / AFR-024..031) -----
    path("staff/inventory/adjust", v.StockAdjustView.as_view(),
         name="phc-stock-adjust"),
    path("staff/inventory/items", v.InventoryItemListCreateView.as_view(),
         name="phc-inventory-items"),
    path("staff/requisitions", v.RequisitionCreateView.as_view(),
         name="phc-requisition-create"),
    path("approver/requisitions/<int:pk>/decide",
         v.RequisitionDecideView.as_view(),
         name="phc-requisition-decide"),
    path("staff/requisitions/<int:pk>/fulfill",
         v.RequisitionFulfillView.as_view(),
         name="phc-requisition-fulfill"),

    # ---- Ambulance (CFR-008 / AFR-032) ---------------------------------
    path("staff/ambulance", v.AmbulanceLogCreateView.as_view(),
         name="phc-ambulance-log"),

    # ---- Health advisories (CFR-009 / AFR-033) -------------------------
    path("staff/advisories", v.HealthAdvisoryCreateView.as_view(),
         name="phc-advisory-publish"),
    path("advisories", v.HealthAdvisoryListView.as_view(),
         name="phc-advisory-list"),

    # ---- Reports (CFR-010 / AFR-034..035) ------------------------------
    path("staff/reports", v.AdminReportView.as_view(),
         name="phc-admin-report"),

    # ---- Audit trail (CFR-012 / AFR-037) -------------------------------
    path("audit/log", v.AuditLogView.as_view(),
         name="phc-audit-log"),
]
