from django.urls import path

from modules.leave_elm.api.views import LeaveApplicationView, LeaveApplyView, LeaveApproveView

urlpatterns = [
    path("applications", LeaveApplicationView.as_view(), name="leave-applications"),
    path("apply", LeaveApplyView.as_view(), name="leave-apply"),
    path("approve", LeaveApproveView.as_view(), name="leave-approve"),
]
