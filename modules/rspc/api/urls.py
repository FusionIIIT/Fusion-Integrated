"""API URLs for RSPC module."""

from django.urls import path

from modules.rspc.api import views

app_name = "rspc"

urlpatterns = [
    # Proposals
    path("proposals/", views.ProposalListCreateView.as_view(), name="proposal-list-create"),
    path("proposals/<int:pk>/", views.ProposalDetailView.as_view(), name="proposal-detail"),
    path("proposals/<int:pk>/submit/", views.ProposalSubmitView.as_view(), name="proposal-submit"),
    path(
        "proposals/<int:pk>/endorse/", views.ProposalEndorseView.as_view(), name="proposal-endorse"
    ),
    path(
        "proposals/<int:pk>/approve/", views.ProposalApproveView.as_view(), name="proposal-approve"
    ),
    # Projects
    path("projects/", views.ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<int:pk>/activate/", views.ProjectActivateView.as_view(), name="project-activate"
    ),
    # Budget & Financial Ledger
    path(
        "projects/<int:pk>/heads/", views.ProjectBudgetHeadListView.as_view(), name="project-heads"
    ),
    path(
        "projects/<int:pk>/disburse/", views.ProjectDisburseView.as_view(), name="project-disburse"
    ),
    path(
        "projects/<int:pk>/disburse/<int:tx_id>/approve/",
        views.ProjectDisburseApproveView.as_view(),
        name="project-disburse-approve",
    ),
    path("projects/<int:pk>/ledger/", views.ProjectLedgerListView.as_view(), name="project-ledger"),
    # Extensions
    path(
        "projects/<int:pk>/extensions/",
        views.ProjectExtensionCreateView.as_view(),
        name="project-extensions",
    ),
    path(
        "projects/<int:pk>/extensions/<int:ext_id>/approve/",
        views.ProjectExtensionApproveView.as_view(),
        name="project-extensions-approve",
    ),
    # Closures
    path(
        "projects/<int:pk>/closure/",
        views.ProjectClosureCreateView.as_view(),
        name="project-closure-create",
    ),
    path(
        "projects/<int:pk>/closure/approve/",
        views.ProjectClosureApproveView.as_view(),
        name="project-closure-approve",
    ),
    # Reports
    path("reports/", views.RspcReportView.as_view(), name="project-reports"),
]
