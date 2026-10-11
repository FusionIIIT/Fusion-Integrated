from django.urls import path

from modules.elm.api.views.leave import (
    LeaveListView,
    LeaveDetailView,
    LeaveCreateView,
    LeaveEligibilityView,
    LeaveCancelView,
    LeaveExtendView,
    LeaveResumeView,
    LeaveWithdrawView,
    LeaveApproveView,
    LeaveRejectView
)

urlpatterns = [
    path("leaves", LeaveListView.as_view(), name="elm-leaves"),
    path("leaves/<int:pk>", LeaveDetailView.as_view(), name="elm-leave-detail"),
    path("leaves/create", LeaveCreateView.as_view(), name="elm-leave-create"),
    path("leaves/<int:pk>/eligibility", LeaveEligibilityView.as_view(),
         name="elm-leave-eligibility"),
    path("leaves/<int:pk>/cancel", LeaveCancelView.as_view(), name="elm-leave-cancel"),
    path("leaves/<int:pk>/extend", LeaveExtendView.as_view(), name="elm-leave-extend"),
    path("leaves/<int:pk>/resume", LeaveResumeView.as_view(), name="elm-leave-resume"),
    path("leaves/<int:pk>/withdraw", LeaveWithdrawView.as_view(), name="elm-leave-withdraw"),
    path("leaves/<int:pk>/approve", LeaveApproveView.as_view(), name="elm-leave-approve"),
    path("leaves/<int:pk>/reject", LeaveRejectView.as_view(), name="elm-leave-reject"),
]
