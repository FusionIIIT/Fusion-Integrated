"""URL patterns for the IWD REST API."""

from django.urls import path

from modules.iwd.api import views

app_name = "iwd"

urlpatterns = [
    path("complaints/", views.ComplaintListCreateView.as_view(), name="complaints_list_create"),
    path("complaints/<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint_detail"),
    path(
        "complaints/<int:pk>/assess/", views.AssessComplaintView.as_view(), name="assess_complaint"
    ),
    path(
        "complaints/<int:pk>/estimates/", views.SubmitEstimateView.as_view(), name="submit_estimate"
    ),
    path("complaints/<int:pk>/flag-urgent/", views.FlagUrgentView.as_view(), name="flag_urgent"),
    path(
        "complaints/<int:pk>/review-urgent/", views.ReviewUrgentView.as_view(), name="review_urgent"
    ),
    path(
        "complaints/<int:pk>/review-low-cost/",
        views.ReviewLowCostView.as_view(),
        name="review_low_cost",
    ),
    path(
        "complaints/<int:pk>/review-mid-range/",
        views.ReviewMidRangeView.as_view(),
        name="review_mid_range",
    ),
    path(
        "complaints/<int:pk>/review-director/",
        views.ReviewDirectorView.as_view(),
        name="review_director",
    ),
    path(
        "complaints/<int:pk>/issue-material/",
        views.StockCheckIssueView.as_view(),
        name="stock_check_issue",
    ),
    path(
        "complaints/<int:pk>/complete-work/", views.CompleteWorkView.as_view(), name="complete_work"
    ),
    path("complaints/<int:pk>/verify/", views.VerifyWorkView.as_view(), name="verify_work"),
    path("complaints/<int:pk>/final-bill/", views.FinalBillView.as_view(), name="final_bill"),
    path("complaints/<int:pk>/audit/", views.AuditFinalBillView.as_view(), name="audit_bill"),
    path("complaints/<int:pk>/settle/", views.SettlePaymentView.as_view(), name="settle_payment"),
    path("complaints/<int:pk>/feedback/", views.ComplaintFeedbackView.as_view(), name="feedback"),
    path(
        "complaints/<int:pk>/resubmit/",
        views.ResubmitEstimateView.as_view(),
        name="resubmit_estimate",
    ),
    path("inventory/", views.InventoryListCreateView.as_view(), name="inventory_list_create"),
]
