from django.urls import path

from modules.vms.api import views

app_name = "vms"
urlpatterns = [
    path("health", views.HealthView.as_view(), name="health"),
    path("registrations", views.RegistrationView.as_view(), name="register"),
    path("public/hosts", views.PublicHostLookupView.as_view(), name="public-host-lookup"),
    path("visitor/requests", views.VisitorRequestsView.as_view(), name="visitor-requests"),
    path(
        "visitor/requests/<int:visit_id>/checkout",
        views.VisitorSelfCheckoutView.as_view(),
        name="visitor-checkout",
    ),
    path(
        "security/documents/<int:document_id>",
        views.VisitorDocumentView.as_view(),
        name="visitor-document",
    ),
    path("visits", views.VisitListView.as_view(), name="visits"),
    path("visits/inbox", views.HostInboxView.as_view(), name="host-inbox"),
    path("visits/admin-review", views.AdminReviewInboxView.as_view(), name="admin-review-inbox"),
    path(
        "visits/<int:visit_id>/terminate",
        views.VisitTerminationView.as_view(),
        name="visit-terminate",
    ),
    path("admin/gate-attempts", views.GateOverrideView.as_view(), name="gate-attempts"),
    path(
        "admin/gate-attempts/<int:attempt_id>/override",
        views.GateOverrideView.as_view(),
        name="gate-override",
    ),
    path(
        "security/gate-attempts/<int:attempt_id>/escalate",
        views.GateEscalationView.as_view(),
        name="gate-attempt-escalation",
    ),
    path(
        "admin/visits/<int:visit_id>/extension",
        views.VisitExtensionDecisionView.as_view(),
        name="visit-extension-decision",
    ),
    path("pre-authorizations", views.PreAuthorizationsView.as_view(), name="pre-authorizations"),
    path(
        "pre-authorizations/<int:authorization_id>/revoke",
        views.PreAuthorizationRevokeView.as_view(),
        name="pre-authorization-revoke",
    ),
    path(
        "visits/<int:visit_id>/<str:decision>",
        views.VisitDecisionView.as_view(),
        name="visit-decision",
    ),
    path("gate/validate", views.GateValidateView.as_view(), name="gate-validate"),
    path("gate/offline-events", views.OfflineGateEntryView.as_view(), name="gate-offline-event"),
    path("gate/walk-ins", views.WalkInRegistrationView.as_view(), name="gate-walk-in"),
    path(
        "gate/visits/<int:visit_id>/checkout",
        views.GateCheckoutView.as_view(),
        name="gate-checkout",
    ),
    path(
        "security/visits/<int:visit_id>/logs",
        views.ManualVisitLogView.as_view(),
        name="manual-visit-log",
    ),
    path("security/live", views.LiveVisitorsView.as_view(), name="live-visitors"),
    path("reports", views.VisitorReportsView.as_view(), name="reports"),
    path("reports/visitors.csv", views.VisitorExportView.as_view(), name="visitor-export"),
    path("security/alerts", views.ZoneAlertView.as_view(), name="zone-alerts"),
    path(
        "security/alerts/<int:alert_id>/resolve",
        views.ZoneAlertView.as_view(),
        name="zone-alert-resolve",
    ),
    path(
        "security/visits/<int:visit_id>/zones", views.ZoneAccessView.as_view(), name="zone-access"
    ),
    path(
        "security/visits/<int:visit_id>/zones/elevate",
        views.ZoneElevateView.as_view(),
        name="zone-elevate",
    ),
    path("security/muster", views.EmergencyMusterView.as_view(), name="emergency-muster"),
    path(
        "security/muster/<int:muster_id>/visits/<int:visit_id>",
        views.MusterRollCallView.as_view(),
        name="muster-roll-call",
    ),
    path(
        "security/muster/<int:muster_id>/complete",
        views.MusterCompleteView.as_view(),
        name="muster-complete",
    ),
    path("admin/policies", views.PolicyVersionsView.as_view(), name="policy-versions"),
    path(
        "admin/policies/<int:policy_id>/publish",
        views.PolicyPublishView.as_view(),
        name="policy-publish",
    ),
    path("admin/registries", views.RegistryVersionsView.as_view(), name="registry-versions"),
    path(
        "admin/registries/<int:registry_id>/blacklist",
        views.RegistryBlacklistEntryView.as_view(),
        name="blacklist-entry",
    ),
    path(
        "admin/registries/<int:registry_id>/safelist",
        views.RegistrySafeListEntryView.as_view(),
        name="safelist-entry",
    ),
    path(
        "admin/registries/<int:registry_id>/publish",
        views.RegistryPublishView.as_view(),
        name="registry-publish",
    ),
    path("admin/audit", views.AuditEventsView.as_view(), name="audit-events"),
    path("admin/roles", views.RoleAssignmentsView.as_view(), name="role-assignments"),
    path(
        "admin/roles/<int:assignment_id>/revoke",
        views.RoleAssignmentRevokeView.as_view(),
        name="role-revoke",
    ),
    path("admin/integrations", views.IntegrationSettingsView.as_view(), name="integrations"),
    path(
        "admin/integrations/<str:integration_type>",
        views.IntegrationSettingsView.as_view(),
        name="integration-detail",
    ),
    path("admin/vip-permissions", views.VipPermissionsView.as_view(), name="vip-permissions"),
    path(
        "admin/vip-permissions/<int:permission_id>/revoke",
        views.VipPermissionRevokeView.as_view(),
        name="vip-revoke",
    ),
    path("admin/events", views.EventsView.as_view(), name="events"),
    path(
        "admin/events/<int:event_id>/controls",
        views.EventControlsView.as_view(),
        name="event-controls",
    ),
    path(
        "admin/events/<int:event_id>/guests",
        views.EventGuestImportView.as_view(),
        name="event-guests",
    ),
    path(
        "admin/events/<int:event_id>/<str:action>",
        views.EventLifecycleView.as_view(),
        name="event-lifecycle",
    ),
]
