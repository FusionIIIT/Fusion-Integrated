from django.urls import path

from modules.rspc.api import views as v

urlpatterns = [
    # Dashboard
    path("dashboard", v.DashboardView.as_view(), name="rspc-dashboard"),

    # Research Project Proposals
    path("proposals", v.ProposalListCreateView.as_view(), name="rspc-proposals"),
    path("proposals/<int:pk>", v.ProposalDetailView.as_view(), name="rspc-proposal"),
    path("proposals/<int:pk>/transition", v.ProposalTransitionView.as_view(),
         name="rspc-proposal-transition"),
    path("proposals/<int:pk>/history", v.ProposalHistoryView.as_view(),
         name="rspc-proposal-history"),

    # Consultancy Projects
    path("consultancy", v.ConsultancyListCreateView.as_view(), name="rspc-consultancy"),
    path("consultancy/<int:pk>/transition", v.ConsultancyTransitionView.as_view(),
         name="rspc-consultancy-transition"),

    # Staff Appointments
    path("appointments", v.AppointmentListCreateView.as_view(), name="rspc-appointments"),
    path("appointments/<int:pk>/transition", v.AppointmentTransitionView.as_view(),
         name="rspc-appointment-transition"),

    # Financial Requests
    path("finance", v.FinanceListCreateView.as_view(), name="rspc-finance"),
    path("finance/<int:pk>/transition", v.FinanceTransitionView.as_view(),
         name="rspc-finance-transition"),

    # Procurement Requests
    path("procurement", v.ProcurementListCreateView.as_view(), name="rspc-procurement"),
    path("procurement/<int:pk>/transition", v.ProcurementTransitionView.as_view(),
         name="rspc-procurement-transition"),

    # Progress Reports
    path("progress-reports", v.ProgressReportListCreateView.as_view(),
         name="rspc-progress-reports"),
    path("progress-reports/<int:pk>/transition",
         v.ProgressReportTransitionView.as_view(),
         name="rspc-progress-report-transition"),

    # Project Closures
    path("closures", v.ClosureListCreateView.as_view(), name="rspc-closures"),
    path("closures/<int:pk>/transition", v.ClosureTransitionView.as_view(),
         name="rspc-closure-transition"),
]
