"""URL routing for VMS API."""
from django.urls import path
from modules.vms.api.views import (
    PreRegisterView,
    HostPendingRequestsView,
    HostDecisionView,
    GateValidationView,
    GateCheckoutView,
    ActivePassesView,
    ActiveVisitsView,
    CampusGatesView,
)

app_name = "vms"

urlpatterns = [
    path("requests/", PreRegisterView.as_view(), name="requests"),
    path("host/pending/", HostPendingRequestsView.as_view(), name="host_pending"),
    path("requests/<str:request_id>/decision/", HostDecisionView.as_view(), name="host_decision"),
    path("gate/validate/", GateValidationView.as_view(), name="gate_validate"),
    path("gate/checkout/", GateCheckoutView.as_view(), name="gate_checkout"),
    path("passes/active/", ActivePassesView.as_view(), name="active_passes"),
    path("visits/active/", ActiveVisitsView.as_view(), name="active_visits"),
    path("gates/", CampusGatesView.as_view(), name="campus_gates"),
]
