from django.urls import path

from modules.vms.api.visitor import views

urlpatterns = [
    path("pre-registrations", views.PreRegistrationView.as_view(),
         name="vms-pre-registrations"),
]
