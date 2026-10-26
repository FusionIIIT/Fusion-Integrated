from django.urls import path
from modules.leave.api.views import (
    LeaveTypeListView,
    LeaveApplicationListCreateView,
    LeaveApplicationDetailView,
    LeaveApplicationReviewView,
)

urlpatterns = [
    path("types/", LeaveTypeListView.as_view(), name="leave-types"),
    path("applications/", LeaveApplicationListCreateView.as_view(), name="leave-applications"),
    path("applications/<int:pk>/", LeaveApplicationDetailView.as_view(), name="leave-application-detail"),
    path("applications/<int:pk>/review/", LeaveApplicationReviewView.as_view(), name="leave-application-review"),
]
