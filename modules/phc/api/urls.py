"""PHC URL configuration."""

from django.urls import path

from modules.phc.api import views as v

urlpatterns = [
    # Schedule & Availability (PHC-UC-01, PHC-UC-07, PHC-UC-08, PHC-UC-22)
    path("schedules/", v.ScheduleListView.as_view(), name="phc-schedule-list"),
    path("schedules/create/", v.ScheduleCreateView.as_view(), name="phc-schedule-create"),
    path(
        "schedules/<int:pk>/publish/", v.SchedulePublishView.as_view(), name="phc-schedule-publish"
    ),
    path("attendance/mark/", v.AttendanceMarkView.as_view(), name="phc-attendance-mark"),
    path("attendance/today/", v.AttendanceTodayView.as_view(), name="phc-attendance-today"),
    # Patient records - patient self-service (PHC-UC-02, PHC-UC-03)
    path("my/visits/", v.MyVisitsView.as_view(), name="phc-my-visits"),
    path("my/visits/<int:pk>/", v.MyVisitDetailView.as_view(), name="phc-my-visit-detail"),
    path("my/visits/download/", v.MyVisitsPdfView.as_view(), name="phc-my-visits-download"),
    path("my/prescriptions/", v.MyPrescriptionsView.as_view(), name="phc-my-prescriptions"),
    # Patient records - PHC Staff (PHC-UC-06)
    path("visits/", v.VisitListStaffView.as_view(), name="phc-visit-list-staff"),
    path("patients/search/", v.PatientSearchView.as_view(), name="phc-patient-search"),
    path("visits/create/", v.VisitCreateView.as_view(), name="phc-visit-create"),
    path(
        "visits/<int:visit_pk>/prescriptions/",
        v.PrescriptionCreateView.as_view(),
        name="phc-prescription-create",
    ),
    # Reimbursement - employee (PHC-UC-04, PHC-UC-05)
    path("claims/my/", v.MyClaimsView.as_view(), name="phc-claims-my"),
    path("claims/my/<int:pk>/", v.MyClaimDetailView.as_view(), name="phc-claims-my-detail"),
    path("claims/submit/", v.SubmitClaimView.as_view(), name="phc-claims-submit"),
    # Reimbursement - workflow (PHC-UC-15, PHC-UC-19, PHC-UC-20, PHC-UC-21)
    path("claims/", v.AllClaimsView.as_view(), name="phc-claims-all"),
    path("claims/<int:pk>/review/", v.ClaimReviewView.as_view(), name="phc-claims-review"),
    path("claims/<int:pk>/verify/", v.ClaimVerifyView.as_view(), name="phc-claims-verify"),
    path("claims/<int:pk>/decide/", v.ClaimDecideView.as_view(), name="phc-claims-decide"),
    path("claims/<int:pk>/payment/", v.ClaimPaymentView.as_view(), name="phc-claims-payment"),
    path("claims/config/", v.ReimbursementConfigView.as_view(), name="phc-claims-config"),
    # Inventory (PHC-UC-09)
    path("inventory/", v.InventoryListView.as_view(), name="phc-inventory-list"),
    path("inventory/create/", v.InventoryCreateView.as_view(), name="phc-inventory-create"),
    path("inventory/low-stock/", v.LowStockListView.as_view(), name="phc-inventory-low-stock"),
    path("inventory/<int:pk>/", v.InventoryDetailView.as_view(), name="phc-inventory-detail"),
    path(
        "inventory/<int:pk>/adjust/", v.InventoryAdjustView.as_view(), name="phc-inventory-adjust"
    ),
    # Procurement (PHC-UC-10, PHC-UC-14, PHC-UC-16)
    path("requisitions/", v.RequisitionListView.as_view(), name="phc-requisition-list"),
    path("requisitions/create/", v.RequisitionCreateView.as_view(), name="phc-requisition-create"),
    path(
        "requisitions/<int:pk>/decide/",
        v.RequisitionDecideView.as_view(),
        name="phc-requisition-decide",
    ),
    path(
        "requisitions/<int:pk>/fulfill/",
        v.RequisitionFulfillView.as_view(),
        name="phc-requisition-fulfill",
    ),
    # Ambulance (PHC-UC-11)
    path("ambulance/", v.AmbulanceLogListView.as_view(), name="phc-ambulance-list"),
    path("ambulance/log/", v.AmbulanceLogCreateView.as_view(), name="phc-ambulance-log"),
    # Announcements (PHC-UC-12)
    path("announcements/", v.AnnouncementListView.as_view(), name="phc-announcement-list"),
    path(
        "announcements/publish/",
        v.AnnouncementPublishView.as_view(),
        name="phc-announcement-publish",
    ),
    # Reports (PHC-UC-13)
    path("reports/", v.ReportView.as_view(), name="phc-report"),
    # Notifications
    path("notifications/", v.MyNotificationsView.as_view(), name="phc-notifications"),
]
