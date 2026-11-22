from django.urls import path

from modules.oap.api import views as v

urlpatterns = [
    path("leave-applications", v.LeaveCollectionView.as_view(), name="oap-leave"),
    path("leave-applications/<int:pk>", v.LeaveDetailView.as_view(), name="oap-leave-detail"),
    path(
        "leave-applications/<int:pk>/decision",
        v.LeaveDecisionView.as_view(),
        name="oap-leave-decision",
    ),
    path("bonafide-requests", v.BonafideCollectionView.as_view(), name="oap-bonafide"),
    path("bonafide-requests/<int:pk>", v.BonafideDetailView.as_view(), name="oap-bonafide-detail"),
    path(
        "bonafide-requests/<int:pk>/verify",
        v.BonafideVerifyView.as_view(),
        name="oap-bonafide-verify",
    ),
    path(
        "bonafide-requests/<int:pk>/decision",
        v.BonafideDecisionView.as_view(),
        name="oap-bonafide-decision",
    ),
    path(
        "bonafide-requests/<int:pk>/certificate",
        v.BonafideCertificateView.as_view(),
        name="oap-bonafide-certificate",
    ),
    path("no-dues-cases", v.NoDuesCollectionView.as_view(), name="oap-no-dues"),
    path("no-dues-cases/<int:pk>", v.NoDuesDetailView.as_view(), name="oap-no-dues-detail"),
    path("no-dues-cases/<int:pk>/results", v.NoDuesResultView.as_view(), name="oap-no-dues-result"),
    path(
        "no-dues-cases/<int:pk>/finalize",
        v.NoDuesFinalizeView.as_view(),
        name="oap-no-dues-finalize",
    ),
    path(
        "no-dues-cases/<int:pk>/certificate",
        v.NoDuesCertificateView.as_view(),
        name="oap-no-dues-certificate",
    ),
    path("assistantship-claims", v.ClaimCollectionView.as_view(), name="oap-claims"),
    path("assistantship-claims/<int:pk>", v.ClaimDetailView.as_view(), name="oap-claim-detail"),
    path(
        "assistantship-claims/<int:pk>/verifications",
        v.ClaimVerifyView.as_view(),
        name="oap-claim-verify",
    ),
    path(
        "assistantship-claims/<int:pk>/forward",
        v.ClaimForwardView.as_view(),
        name="oap-claim-forward",
    ),
    path(
        "assistantship-claims/<int:pk>/decision",
        v.ClaimDecisionView.as_view(),
        name="oap-claim-decision",
    ),
    path(
        "assistantship-claims/<int:pk>/stipend",
        v.ClaimStipendView.as_view(),
        name="oap-claim-stipend",
    ),
    path(
        "thesis-supervisor-assignments",
        v.ThesisAssignmentCollectionView.as_view(),
        name="oap-thesis-assignments",
    ),
    path("ta-assignments", v.TAAssignmentCollectionView.as_view(), name="oap-ta-assignments"),
    path("seminar-requests", v.SeminarRequestCollectionView.as_view(), name="oap-seminars"),
    path(
        "seminar-requests/<int:pk>/schedule",
        v.SeminarScheduleView.as_view(),
        name="oap-seminar-schedule",
    ),
    path("seminar-schedules", v.SeminarScheduleListView.as_view(), name="oap-seminar-schedules"),
    path("notifications", v.NotificationListView.as_view(), name="oap-notifications"),
]
