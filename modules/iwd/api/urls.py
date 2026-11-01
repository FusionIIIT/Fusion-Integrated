"""URL configuration for IWD API endpoints."""
from django.urls import path

from modules.iwd.api import views

app_name = "iwd"

urlpatterns = [
    path("complaints/", views.ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("complaints/<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint-detail"),
    path("complaints/<int:pk>/assess/", views.ComplaintAssessView.as_view(), name="complaint-assess"),
    path("complaints/<int:pk>/estimates/", views.ComplaintEstimateView.as_view(), name="complaint-estimates"),
    path("complaints/<int:pk>/review-estimate/", views.ComplaintEstimateReviewView.as_view(), name="complaint-review-estimate"),
    path("complaints/<int:pk>/resubmit-estimate/", views.ComplaintEstimateResubmitView.as_view(), name="complaint-resubmit-estimate"),
    path("complaints/<int:pk>/inventory-action/", views.ComplaintInventoryActionView.as_view(), name="complaint-inventory-action"),
]
