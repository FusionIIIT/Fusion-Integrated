from django.urls import path

from modules.vms.api.gate import views

urlpatterns = [
    path("gate/validate", views.GateValidateView.as_view(), name="vms-gate-validate"),
    path("gate/checkout", views.GateCheckoutView.as_view(), name="vms-gate-checkout"),
]
