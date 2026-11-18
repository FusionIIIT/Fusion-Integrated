from django.urls import path

from modules.visitors.api import views as v

urlpatterns = [
    # Visitor self-service (VMS-UC-010, 011, 012)
    path("visits/register", v.PreRegisterView.as_view(),
         name="vms-register"),
    path("visits", v.MyVisitsView.as_view(),
         name="vms-my-visits"),
    path("visits/<int:pk>", v.VisitDetailView.as_view(),
         name="vms-visit-detail"),

    # Host (VMS-UC-013, 015, 016)
    path("host/pending", v.HostPendingView.as_view(),
         name="vms-host-pending"),
    path("host/<int:pk>/decide", v.HostDecideView.as_view(),
         name="vms-host-decide"),
    path("host/arrivals", v.HostArrivalsView.as_view(),
         name="vms-host-arrivals"),
    path("host/<int:pk>/terminate", v.HostTerminateView.as_view(),
         name="vms-host-terminate"),

    # Security / gate operations (VMS-UC-017, 018, 019, 020, 021, 022)
    path("gate/walkin", v.WalkInRegisterView.as_view(),
         name="vms-walkin"),
    path("gate/<int:pk>/validate", v.GateValidateView.as_view(),
         name="vms-gate-validate"),
    path("gate/<int:pk>/override", v.GateOverrideView.as_view(),
         name="vms-gate-override"),
    path("gate/<int:pk>/checkout", v.GateCheckoutView.as_view(),
         name="vms-gate-checkout"),
    path("gate/<int:pk>/logs", v.GateLogsView.as_view(),
         name="vms-gate-logs"),
    path("gate/dashboard", v.LiveDashboardView.as_view(),
         name="vms-dashboard"),

    # Zone access (VMS-UC-023, 024)
    path("zones", v.ZoneListView.as_view(),
         name="vms-zones"),
    path("zones/<int:pk>/validate", v.ZoneValidateView.as_view(),
         name="vms-zone-validate"),
    path("zones/<int:pk>/elevate", v.ZoneElevationView.as_view(),
         name="vms-zone-elevate"),

    # Admin (VMS-UC-005, 006, 007, 033, 034, 035, 036)
    path("admin/pending", v.AdminPendingView.as_view(),
         name="vms-admin-pending"),
    path("admin/<int:pk>/decide", v.AdminDecideView.as_view(),
         name="vms-admin-decide"),
    path("admin/<int:pk>/terminate", v.AdminTerminateView.as_view(),
         name="vms-admin-terminate"),
    path("admin/<int:pk>/extend", v.ExtensionView.as_view(),
         name="vms-admin-extend"),
    path("admin/reports", v.ReportView.as_view(),
         name="vms-reports"),
    path("admin/blacklist", v.BlacklistView.as_view(),
         name="vms-blacklist"),
    path("admin/policies", v.AccessPolicyView.as_view(),
         name="vms-policies"),

    # Emergency muster (VMS-UC-026, 027, 032)
    path("muster/trigger", v.MusterTriggerView.as_view(),
         name="vms-muster-trigger"),
    path("muster", v.MusterListView.as_view(),
         name="vms-muster-list"),
    path("muster/<int:muster_id>/roll-call", v.MusterRollCallView.as_view(),
         name="vms-muster-rollcall"),
    path("muster/<int:muster_id>/roll-call/<int:visit_id>/account",
         v.MusterAccountView.as_view(), name="vms-muster-account"),
]
