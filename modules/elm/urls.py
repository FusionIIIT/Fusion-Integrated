from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet

router = DefaultRouter()
router.register(r"leave-types", LeaveTypeViewSet, basename="leave-type")
router.register(r"balances", LeaveBalanceViewSet, basename="leave-balance")
router.register(r"requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("", include(router.urls)),
]
