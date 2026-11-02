from django.urls import path

from modules.vms.api.visitor import views

urlpatterns = [
    path("visitor/session/otp", views.OtpRequestView.as_view(), name="vms-visitor-otp"),
    path("visitor/session/verify", views.OtpVerifyView.as_view(),
         name="vms-visitor-verify"),
    path("visitor/pre-registrations", views.PreRegistrationView.as_view(),
         name="vms-pre-registrations"),
    path("visitor/requests", views.RequestListView.as_view(), name="vms-visitor-requests"),
    path("visitor/requests/<int:pk>", views.RequestDetailView.as_view(),
         name="vms-visitor-request"),
    path("visitor/requests/<int:pk>/pass", views.RequestPassView.as_view(),
         name="vms-visitor-pass"),
]
