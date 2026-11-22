from django.urls import path

from modules.iwd.api import views as v

urlpatterns = [
    path("complaints", v.ComplaintListCreateView.as_view(), name="iwd-complaints"),
    path("complaints/<int:pk>", v.ComplaintDetailView.as_view(), name="iwd-complaint-detail"),
    path(
        "complaints/<int:pk>/assess",
        v.ComplaintAssessView.as_view(),
        name="iwd-complaint-assess",
    ),
    path(
        "complaints/<int:pk>/urgent",
        v.ComplaintUrgentFlagView.as_view(),
        name="iwd-complaint-urgent",
    ),
    path(
        "complaints/<int:pk>/estimates",
        v.ComplaintEstimateListCreateView.as_view(),
        name="iwd-complaint-estimates",
    ),
    path(
        "complaints/<int:pk>/issue-materials",
        v.ComplaintIssueMaterialsView.as_view(),
        name="iwd-complaint-issue-materials",
    ),
    path(
        "complaints/<int:pk>/procure",
        v.ComplaintProcureView.as_view(),
        name="iwd-complaint-procure",
    ),
    path(
        "complaints/<int:pk>/complete-work",
        v.ComplaintCompleteWorkView.as_view(),
        name="iwd-complaint-complete-work",
    ),
    path(
        "complaints/<int:pk>/verify",
        v.ComplaintVerifyWorkView.as_view(),
        name="iwd-complaint-verify",
    ),
    path(
        "complaints/<int:pk>/final-bill",
        v.ComplaintFinalBillView.as_view(),
        name="iwd-complaint-final-bill",
    ),
    path(
        "complaints/<int:pk>/feedback",
        v.ComplaintFeedbackView.as_view(),
        name="iwd-complaint-feedback",
    ),
    path(
        "estimates/<int:pk>/review-low",
        v.EstimateReviewLowView.as_view(),
        name="iwd-estimate-review-low",
    ),
    path(
        "estimates/<int:pk>/committee-review",
        v.EstimateCommitteeReviewView.as_view(),
        name="iwd-estimate-committee-review",
    ),
    path(
        "estimates/<int:pk>/review-mid",
        v.EstimateReviewMidView.as_view(),
        name="iwd-estimate-review-mid",
    ),
    path(
        "estimates/<int:pk>/review-director",
        v.EstimateReviewDirectorView.as_view(),
        name="iwd-estimate-review-director",
    ),
    path("inventory", v.InventoryListView.as_view(), name="iwd-inventory"),
    path("bills/<int:pk>/audit", v.BillAuditView.as_view(), name="iwd-bill-audit"),
    path("bills/<int:pk>/settle", v.BillSettleView.as_view(), name="iwd-bill-settle"),
]
