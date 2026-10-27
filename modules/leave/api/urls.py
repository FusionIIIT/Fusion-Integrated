from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LeaveApplicationViewSet,
    SubstituteViewSet,
    ApprovalViewSet,
    BalanceViewSet,
    CalendarViewSet,
    AdminLeaveViewSet,
)

router = DefaultRouter()
router.register(r"applications", LeaveApplicationViewSet, basename="leave-application")
router.register(r"substitutes", SubstituteViewSet, basename="leave-substitute")
router.register(r"approvals", ApprovalViewSet, basename="leave-approval")
router.register(r"balances", BalanceViewSet, basename="leave-balance")
router.register(r"calendar", CalendarViewSet, basename="leave-calendar")
router.register(r"admin", AdminLeaveViewSet, basename="leave-admin")

urlpatterns = [
    path("", include(router.urls)),
]