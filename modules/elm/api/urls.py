from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.urls import path as drf_path

from modules.elm.api.views import (
    LeaveApplicationViewSet,
    LeaveBalanceViewSet,
    LeaveTypeViewSet,
    record_decision,
)

router = DefaultRouter()
router.register(r"leave-types", LeaveTypeViewSet, basename="leave-types")
router.register(r"leave-balances", LeaveBalanceViewSet, basename="leave-balances")
router.register(r"leave-applications", LeaveApplicationViewSet, basename="leave-applications")

urlpatterns = [
    path("", include(router.urls)),
    drf_path("record-decision/", record_decision, name="record-decision"),
]
