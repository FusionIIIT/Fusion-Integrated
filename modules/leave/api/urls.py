from django.urls import path

from modules.leave.api.views import LeaveRequestView

urlpatterns = [
    path("requests", LeaveRequestView.as_view(), name="leave-requests"),
]
