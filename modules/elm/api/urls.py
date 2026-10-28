from django.urls import path
from .views import (LeaveApplyAPIView, MyLeavesAPIView, LeaveCancelAPIView,
                    PendingLeavesAPIView, LeaveApproveAPIView)

urlpatterns = [
    path("leaves/", LeaveApplyAPIView.as_view(), name="elm-leave-apply"),
    path("leaves/mine/", MyLeavesAPIView.as_view(), name="elm-leave-mine"),
    path("leaves/pending/", PendingLeavesAPIView.as_view(), name="elm-leave-pending"),
    path("leaves/<int:pk>/cancel/", LeaveCancelAPIView.as_view(), name="elm-leave-cancel"),
    path("leaves/<int:pk>/approve/", LeaveApproveAPIView.as_view(), name="elm-leave-approve"),
]