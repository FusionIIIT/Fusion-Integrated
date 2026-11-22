from django.urls import path

from modules.vms.api.gate import views

urlpatterns = [
    path("gate/validate", views.GateValidateView.as_view(), name="vms-gate-validate"),
    path("gate/override", views.GateOverrideView.as_view(), name="vms-gate-override"),
    path("gate/escalations", views.EscalationCreateView.as_view(), name="vms-gate-escalate"),
    path("gate/escalations/<int:pk>/resolve", views.EscalationResolveView.as_view(),
         name="vms-gate-escalation-resolve"),
    path("gate/manual-entries", views.ManualEntryView.as_view(), name="vms-gate-manual"),
    path("gate/denials", views.DenialListView.as_view(), name="vms-gate-denials"),
    path("gate/alerts", views.AlertListView.as_view(), name="vms-gate-alerts"),
    path("gate/alerts/<int:pk>/handle", views.AlertHandleView.as_view(),
         name="vms-gate-alert-handle"),
    path("gate/sync", views.SyncView.as_view(), name="vms-gate-sync"),
    path("gate/cached-roster", views.CachedRosterView.as_view(), name="vms-gate-roster"),
]
