"""URL patterns for RSPC module API."""
from django.urls import path

from modules.rspc.api import views as v

urlpatterns = [
    # Research Proposals
    path("proposals", v.ProposalListCreateView.as_view(), name="rspc-proposals"),
    path(
        "proposals/<int:pk>",
        v.ProposalDetailView.as_view(),
        name="rspc-proposal-detail",
    ),
    path(
        "proposals/<int:pk>/transition",
        v.ProposalTransitionView.as_view(),
        name="rspc-proposal-transition",
    ),

    # Consultancy Projects
    path("consultancies", v.ConsultancyListCreateView.as_view(), name="rspc-consultancies"),
    path(
        "consultancies/<int:pk>",
        v.ConsultancyDetailView.as_view(),
        name="rspc-consultancy-detail",
    ),

    # Staff Appointments
    path("staff", v.StaffAppointmentListCreateView.as_view(), name="rspc-staff"),
    path("staff/<int:pk>", v.StaffAppointmentDetailView.as_view(), name="rspc-staff-detail"),

    # Financial Requests
    path("financial", v.FinancialRequestListCreateView.as_view(), name="rspc-financial"),
    path(
        "financial/<int:pk>",
        v.FinancialRequestDetailView.as_view(),
        name="rspc-financial-detail",
    ),

    # Procurement Requests
    path("procurement", v.ProcurementRequestListCreateView.as_view(), name="rspc-procurement"),
    path(
        "procurement/<int:pk>",
        v.ProcurementRequestDetailView.as_view(),
        name="rspc-procurement-detail",
    ),

    # Progress Reports
    path("reports", v.ProgressReportListCreateView.as_view(), name="rspc-reports"),
    path("reports/<int:pk>", v.ProgressReportDetailView.as_view(), name="rspc-report-detail"),

    # Project Closures
    path("closures", v.ProjectClosureListCreateView.as_view(), name="rspc-closures"),
    path("closures/<int:pk>", v.ProjectClosureDetailView.as_view(), name="rspc-closure-detail"),

    # Audit Logs
    path("audit", v.AuditTrailListView.as_view(), name="rspc-audit"),
]
