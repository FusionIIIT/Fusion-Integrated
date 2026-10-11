from django.urls import path

from .views import (
    LeaveRequestApproveView,
    LeaveRequestCancelView,
    LeaveRequestCreateView,
    LeaveRequestDetailView,
    LeaveRequestListView,
    LeaveRequestRejectView,
)

urlpatterns = [
    path("leave-requests/", LeaveRequestListView.as_view(), name="leave-request-list"),
    path("leave-requests/create/", LeaveRequestCreateView.as_view(), name="leave-request-create"),
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path("leave-requests/<int:pk>/approve/", LeaveRequestApproveView.as_view(), name="leave-request-approve"),
    path("leave-requests/<int:pk>/reject/", LeaveRequestRejectView.as_view(), name="leave-request-reject"),
    path("leave-requests/<int:pk>/cancel/", LeaveRequestCancelView.as_view(), name="leave-request-cancel"),
]
