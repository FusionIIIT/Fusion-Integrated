"""URL routing for SPACS API."""

from django.urls import path

from modules.spacs.api import views as v

urlpatterns = [
    # Schemes
    path("schemes", v.SchemeListView.as_view(), name="spacs-schemes"),
    path("schemes/<int:pk>", v.SchemeDetailView.as_view(), name="spacs-scheme-detail"),
    # Cycles
    path("cycles", v.CycleListView.as_view(), name="spacs-cycles"),
    path(
        "cycles/<int:pk>/publish",
        v.AwardCyclePublishView.as_view(),
        name="spacs-cycle-publish",
    ),
    # Applications
    path("applications", v.ApplicationListView.as_view(), name="spacs-applications"),
    path(
        "applications/<int:pk>",
        v.ApplicationDetailView.as_view(),
        name="spacs-application-detail",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.ApplicationWithdrawView.as_view(),
        name="spacs-application-withdraw",
    ),
    # Verification
    path("verifications", v.VerificationQueueView.as_view(), name="spacs-verifications"),
    path(
        "verifications/<int:pk>/action",
        v.VerificationActionView.as_view(),
        name="spacs-verification-action",
    ),
    # Decisions
    path("decisions/action", v.DecisionActionView.as_view(), name="spacs-decision-action"),
    # Renewals
    path("renewals", v.RenewalListView.as_view(), name="spacs-renewals"),
    # Awards
    path("awards", v.AwardListView.as_view(), name="spacs-awards"),
    path("awards/publish", v.AwardPublishView.as_view(), name="spacs-award-publish"),
    path("awards/export", v.AwardExportView.as_view(), name="spacs-award-export"),
    # Tasks
    path("tasks", v.TaskListView.as_view(), name="spacs-tasks"),
    # Audit
    path("audit", v.AuditListView.as_view(), name="spacs-audit"),
]
