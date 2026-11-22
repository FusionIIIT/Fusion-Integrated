"""VMS API URL Routing.
Mounted at /api/v1/vms/.
"""

from django.urls import path

from modules.vms.api.views import (
    BlacklistManageView,
    EmergencyMusterView,
    GateAlertListView,
    GateCheckOutView,
    GateOfflineSyncView,
    GateVerifyQRCheckInView,
    GateZoneVerifyView,
    VisitApproveView,
    VisitListCreateView,
    VisitRejectView,
)

urlpatterns = [
    path("visits/", VisitListCreateView.as_view(), name="vms-visits-list-create"),
    path("visits/<int:pk>/approve/", VisitApproveView.as_view(), name="vms-visit-approve"),
    path("visits/<int:pk>/reject/", VisitRejectView.as_view(), name="vms-visit-reject"),
    path("gate/check-in/", GateVerifyQRCheckInView.as_view(), name="vms-gate-check-in"),
    path("gate/check-out/", GateCheckOutView.as_view(), name="vms-gate-check-out"),
    path("gate/verify-zone/", GateZoneVerifyView.as_view(), name="vms-gate-verify-zone"),
    path("gate/reconcile-offline/", GateOfflineSyncView.as_view(), name="vms-gate-offline-sync"),
    path("security/alerts/", GateAlertListView.as_view(), name="vms-security-alerts"),
    path("security/blacklist/", BlacklistManageView.as_view(), name="vms-security-blacklist"),
    path("emergency/muster/", EmergencyMusterView.as_view(), name="vms-emergency-muster"),
]
