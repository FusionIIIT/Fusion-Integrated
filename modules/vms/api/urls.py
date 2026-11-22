"""URL configuration for VMS endpoints."""

from django.urls import path

from modules.vms.api import views

urlpatterns = [
    # Visits & Passes
    path("visits/pre-register/", views.PreRegisterView.as_view(), name="vms-pre-register"),
    path("visits/walk-in/", views.WalkInView.as_view(), name="vms-walk-in"),
    path("visits/bulk/", views.BulkRegisterView.as_view(), name="vms-bulk-register"),
    path("visits/", views.VisitListView.as_view(), name="vms-visit-list"),
    path("visits/<int:pk>/", views.VisitDetailView.as_view(), name="vms-visit-detail"),
    path("visits/<int:pk>/decide/", views.VisitDecideView.as_view(), name="vms-visit-decide"),
    path(
        "visits/<int:pk>/contingency-approve/",
        views.VisitContingencyApproveView.as_view(),
        name="vms-visit-contingency",
    ),
    path("visits/<int:pk>/extend/", views.VisitExtendView.as_view(), name="vms-visit-extend"),
    path(
        "visits/<int:pk>/terminate/",
        views.VisitTerminateView.as_view(),
        name="vms-visit-terminate",
    ),
    path("passes/<int:pk>/", views.PassDetailView.as_view(), name="vms-pass-detail"),
    # Security Gate & Scanner
    path("gate/validate/", views.GateValidateView.as_view(), name="vms-gate-validate"),
    path("gate/check-in/", views.GateCheckInView.as_view(), name="vms-gate-checkin"),
    path("gate/check-out/", views.GateCheckOutView.as_view(), name="vms-gate-checkout"),
    path("gate/override/", views.GateOverrideView.as_view(), name="vms-gate-override"),
    path("gate/offline-sync/", views.GateOfflineSyncView.as_view(), name="vms-gate-offline-sync"),
    # Live Dashboard & Zone Control
    path("dashboard/live/", views.LiveDashboardView.as_view(), name="vms-live-dashboard"),
    path("zones/validate/", views.ZoneValidateView.as_view(), name="vms-zone-validate"),
    path("zones/elevate/", views.ZoneElevateView.as_view(), name="vms-zone-elevate"),
    # Blacklist & Safe-list
    path("blacklist/", views.BlacklistListView.as_view(), name="vms-blacklist-list"),
    path(
        "blacklist/<int:pk>/safe-list/",
        views.BlacklistSafeListView.as_view(),
        name="vms-blacklist-safelist",
    ),
    # Emergency Muster
    path("emergency/muster/", views.EmergencyMusterView.as_view(), name="vms-emergency-muster"),
    path("emergency/roster/", views.EmergencyRosterView.as_view(), name="vms-emergency-roster"),
    path(
        "emergency/roll-call/<int:pk>/",
        views.EmergencyRollCallView.as_view(),
        name="vms-emergency-rollcall",
    ),
    # Analytics & Audit
    path(
        "analytics/dashboard/",
        views.AnalyticsDashboardView.as_view(),
        name="vms-analytics-dashboard",
    ),
    path("audit/", views.AuditLogListView.as_view(), name="vms-audit-list"),
    # Policy & Pre-authorizations
    path("policies/", views.AccessPolicyListView.as_view(), name="vms-policy-list"),
    path(
        "policies/<int:version>/publish/",
        views.AccessPolicyPublishView.as_view(),
        name="vms-policy-publish",
    ),
    path("pre-authorizations/", views.PreAuthorizationListView.as_view(), name="vms-preauth-list"),
]
