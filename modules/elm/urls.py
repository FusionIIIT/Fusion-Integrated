from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LeaveBalanceViewSet, LeaveRequestViewSet, LeaveTypeViewSet

router = DefaultRouter()
router.register(r"leave-types", LeaveTypeViewSet, basename="leave-type")
router.register(r"balances", LeaveBalanceViewSet, basename="leave-balance")
router.register(r"requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("", include(router.urls)),
]
