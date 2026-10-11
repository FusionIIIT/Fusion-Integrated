"""URL dispatch for Employee Leave Management endpoints."""
from django.urls import path

from modules.leave.api.views import (
    LeaveAdminStubView,
    LeaveApplicationStubView,
    LeaveApprovalsStubView,
    LeaveHealthView,
)

app_name = "leave"

urlpatterns = [
    path("health/", LeaveHealthView.as_view(), name="health"),
    path("applications/", LeaveApplicationStubView.as_view(), name="applications"),
    path("approvals/", LeaveApprovalsStubView.as_view(), name="approvals"),
    path("admin/", LeaveAdminStubView.as_view(), name="admin"),
]
