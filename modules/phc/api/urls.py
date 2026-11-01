from django.urls import path

from modules.phc.api import views

urlpatterns = [
    path("patients", views.PatientListCreateView.as_view(), name="phc-patients"),
    path("doctors", views.DoctorListView.as_view(), name="phc-doctors"),
    path("doctors/manage", views.DoctorCreateView.as_view(), name="phc-doctor-create"),
    path("doctors/<int:pk>", views.DoctorDetailView.as_view(), name="phc-doctor-update"),
    path("schedules", views.ScheduleView.as_view(), name="phc-schedules"),
    path("appointments", views.AppointmentListCreateView.as_view(), name="phc-appointments"),
    path(
        "appointments/<int:pk>/transition",
        views.AppointmentTransitionView.as_view(),
        name="phc-appointment-transition",
    ),
    path("consultations", views.ConsultationListView.as_view(), name="phc-consultations"),
    path(
        "appointments/<int:appointment_id>/consultation",
        views.ConsultationCreateView.as_view(),
        name="phc-consultation-create",
    ),
    path("medicines", views.MedicineListCreateView.as_view(), name="phc-medicines"),
    path("medicines/<int:pk>/stock", views.MedicineStockView.as_view(), name="phc-stock"),
    path(
        "inventory/transactions",
        views.InventoryTransactionListView.as_view(),
        name="phc-inventory-transactions",
    ),
    path("announcements", views.AnnouncementListCreateView.as_view(), name="phc-announcements"),
]
