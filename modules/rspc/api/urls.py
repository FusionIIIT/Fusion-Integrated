"""RSPC Module URL Routing.
Mounts under /api/v1/rspc/.
"""

from django.urls import path

from modules.rspc.api import views as v

urlpatterns = [
    # Research Proposals (UC-002..006, CW-RSPC-01)
    path("proposals", v.ProposalListCreateView.as_view(), name="rspc-proposals"),
    path("proposals/<int:pk>", v.ProposalDetailView.as_view(), name="rspc-proposal-detail"),
    path(
        "proposals/<int:pk>/recommend-dept",
        v.ProposalRecommendDeptView.as_view(),
        name="rspc-proposal-recommend-dept",
    ),
    path("proposals/<int:pk>/verify", v.ProposalVerifyView.as_view(), name="rspc-proposal-verify"),
    path(
        "proposals/<int:pk>/dean-decide",
        v.ProposalDeanDecideView.as_view(),
        name="rspc-proposal-dean-decide",
    ),
    path(
        "proposals/<int:pk>/director-authorize",
        v.ProposalDirectorAuthorizeView.as_view(),
        name="rspc-proposal-director-authorize",
    ),
    # Consultancy Projects (UC-007, 008, CW-RSPC-02)
    path("consultancies", v.ConsultancyListCreateView.as_view(), name="rspc-consultancies"),
    path(
        "consultancies/<int:pk>/recommend-dept",
        v.ConsultancyRecommendDeptView.as_view(),
        name="rspc-consultancy-recommend-dept",
    ),
    path(
        "consultancies/<int:pk>/verify",
        v.ConsultancyVerifyView.as_view(),
        name="rspc-consultancy-verify",
    ),
    path(
        "consultancies/<int:pk>/dean-decide",
        v.ConsultancyDeanDecideView.as_view(),
        name="rspc-consultancy-dean-decide",
    ),
    path(
        "consultancies/<int:pk>/director-authorize",
        v.ConsultancyDirectorAuthorizeView.as_view(),
        name="rspc-consultancy-director-authorize",
    ),
    path(
        "consultancies/<int:pk>/settlements",
        v.ConsultancySettlementView.as_view(),
        name="rspc-consultancy-settlements",
    ),
    # Project Portfolio & Lifecycle (UC-001, UC-021)
    path("projects", v.ProjectPortfolioListView.as_view(), name="rspc-projects"),
    path("projects/<int:pk>", v.ProjectDetailView.as_view(), name="rspc-project-detail"),
    path(
        "projects/<int:pk>/update-lifecycle",
        v.ProjectUpdateView.as_view(),
        name="rspc-project-update-lifecycle",
    ),
    # Staff Appointments (UC-009, 010, 022, 023, CW-RSPC-03)
    path(
        "staff-appointments",
        v.StaffAppointmentListCreateView.as_view(),
        name="rspc-staff-appointments",
    ),
    path(
        "staff-appointments/<int:pk>/verify",
        v.StaffAppointmentVerifyView.as_view(),
        name="rspc-staff-appointment-verify",
    ),
    path(
        "staff-appointments/<int:pk>/recommend",
        v.StaffAppointmentRecommendView.as_view(),
        name="rspc-staff-appointment-recommend",
    ),
    path(
        "staff-appointments/<int:pk>/dean-decide",
        v.StaffAppointmentDeanDecideView.as_view(),
        name="rspc-staff-appointment-dean-decide",
    ),
    path(
        "staff-appointments/<int:pk>/director-authorize",
        v.StaffAppointmentDirectorAuthorizeView.as_view(),
        name="rspc-staff-appointment-director-authorize",
    ),
    # Financial & Fund Requests (UC-011, 012, 024, CW-RSPC-04)
    path(
        "financial-requests",
        v.FinancialRequestListCreateView.as_view(),
        name="rspc-financial-requests",
    ),
    path(
        "financial-requests/<int:pk>/verify",
        v.FinancialRequestVerifyView.as_view(),
        name="rspc-financial-request-verify",
    ),
    path(
        "financial-requests/<int:pk>/dean-decide",
        v.FinancialRequestDeanDecideView.as_view(),
        name="rspc-financial-request-dean-decide",
    ),
    path(
        "financial-requests/<int:pk>/director-authorize",
        v.FinancialRequestDirectorAuthorizeView.as_view(),
        name="rspc-financial-request-director-authorize",
    ),
    # Procurement Requests (UC-013, 025, 026, CW-RSPC-05)
    path(
        "procurement-requests",
        v.ProcurementRequestListCreateView.as_view(),
        name="rspc-procurement-requests",
    ),
    path(
        "procurement-requests/<int:pk>/verify",
        v.ProcurementRequestVerifyView.as_view(),
        name="rspc-procurement-request-verify",
    ),
    path(
        "procurement-requests/<int:pk>/dean-decide",
        v.ProcurementRequestDeanDecideView.as_view(),
        name="rspc-procurement-request-dean-decide",
    ),
    path(
        "procurement-requests/<int:pk>/director-authorize",
        v.ProcurementRequestDirectorAuthorizeView.as_view(),
        name="rspc-procurement-request-director-authorize",
    ),
    # Progress Reports (UC-014)
    path(
        "progress-reports", v.ProgressReportListCreateView.as_view(), name="rspc-progress-reports"
    ),
    # Project Closures (UC-015, 027, 028, CW-RSPC-06)
    path("closures", v.ProjectClosureListCreateView.as_view(), name="rspc-closures"),
    path(
        "closures/<int:pk>/verify", v.ProjectClosureVerifyView.as_view(), name="rspc-closure-verify"
    ),
    path(
        "closures/<int:pk>/dean-decide",
        v.ProjectClosureDeanDecideView.as_view(),
        name="rspc-closure-dean-decide",
    ),
    path(
        "closures/<int:pk>/director-authorize",
        v.ProjectClosureDirectorAuthorizeView.as_view(),
        name="rspc-closure-director-authorize",
    ),
    # Notifications, Audits & Integrations (UC-016, 017, 018, 029, 030)
    path("notifications", v.NotificationListView.as_view(), name="rspc-notifications"),
    path("audit-trails", v.AuditTrailListView.as_view(), name="rspc-audit-trails"),
    path(
        "integrations/exchange",
        v.IntegrationExchangeView.as_view(),
        name="rspc-integration-exchange",
    ),
    path("agency-trackings", v.AgencyTrackingView.as_view(), name="rspc-agency-trackings"),
    path("roles/sync", v.RoleSyncView.as_view(), name="rspc-role-sync"),
]
