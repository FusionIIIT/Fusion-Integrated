from django.urls import path

from modules.vms.api import gate, requests

urlpatterns = [
    path("pre-registrations", requests.PreRegistrationView.as_view(), name="vms-pre-registrations"),
    path("host/pending", requests.HostPendingListView.as_view(), name="vms-host-pending"),
    path("host/requests/<int:pk>/decision", requests.HostDecisionView.as_view(), name="vms-host-decision"),
    path("gate/validate", gate.GateValidateView.as_view(), name="vms-gate-validate"),
    path("gate/checkout", gate.GateCheckoutView.as_view(), name="vms-gate-checkout"),
    path("blacklist", gate.BlacklistView.as_view(), name="vms-blacklist"),
    path("policies", gate.PolicyPublishView.as_view(), name="vms-policies"),
    path("policies/<int:pk>/publish", gate.PolicyPublishView.as_view(), name="vms-policy-publish"),
]
