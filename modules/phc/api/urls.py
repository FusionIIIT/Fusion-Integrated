from django.urls import path
from modules.phc.api.views import (
    ClaimListView, ClaimDetailView, ClaimReviewListView, ClaimReviewView,
    ClaimVerificationListView, ClaimVerificationView, ClaimSanctionListView,
    ClaimSanctionView, ClaimPaymentListView, ClaimPaymentView
)

urlpatterns = [
    path("claims", ClaimListView.as_view(), name="claim-list"),
    path("claims/<int:pk>", ClaimDetailView.as_view(), name="claim-detail"),
    path("claims/queue/review", ClaimReviewListView.as_view(), name="claim-review-list"),
    path("claims/<int:pk>/review", ClaimReviewView.as_view(), name="claim-review"),
    path("claims/queue/verification", ClaimVerificationListView.as_view(), name="claim-verification-list"),
    path("claims/<int:pk>/verify", ClaimVerificationView.as_view(), name="claim-verification"),
    path("claims/queue/sanction", ClaimSanctionListView.as_view(), name="claim-sanction-list"),
    path("claims/<int:pk>/decide", ClaimSanctionView.as_view(), name="claim-sanction"),
    path("claims/queue/payment", ClaimPaymentListView.as_view(), name="claim-payment-list"),
    path("claims/<int:pk>/pay", ClaimPaymentView.as_view(), name="claim-payment"),
]
