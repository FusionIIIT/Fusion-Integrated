from django.urls import include, path

from modules.vms.api import legacy_gate, requests

# Routes that exist today. Phase 0d ports them into the area packages below and
# deletes requests.py / legacy_gate.py (api/gate.py was renamed so that the
# api.gate area package can exist).
_legacy = [
    path("pre-registrations", requests.PreRegistrationView.as_view(), name="vms-pre-registrations"),
    path("host/pending", requests.HostPendingListView.as_view(), name="vms-host-pending"),
    path("host/requests/<int:pk>/decision", requests.HostDecisionView.as_view(), name="vms-host-decision"),
    path("gate/validate", legacy_gate.GateValidateView.as_view(), name="vms-gate-validate"),
    path("gate/checkout", legacy_gate.GateCheckoutView.as_view(), name="vms-gate-checkout"),
    path("blacklist", legacy_gate.BlacklistView.as_view(), name="vms-blacklist"),
    path("policies", legacy_gate.PolicyPublishView.as_view(), name="vms-policies"),
    path("policies/<int:pk>/publish", legacy_gate.PolicyPublishView.as_view(), name="vms-policy-publish"),
]

# One url module per area; each lane fills in its own and never edits this file.
_AREAS = (
    "visitor", "host", "gate", "zones", "admin", "walkin", "visit",
    "notify", "monitor", "muster", "events", "reports", "extensions",
)

urlpatterns = _legacy + [
    path("", include(f"modules.vms.api.{area}.urls")) for area in _AREAS
]
