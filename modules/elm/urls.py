from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LeaveBalanceViewSet,
    LeaveApplicationViewSet,
    SubstituteRequestViewSet,
    HolidayCalendarViewSet,
    LeavePolicyViewSet
)

router = DefaultRouter()
router.register(r"balances", LeaveBalanceViewSet)
router.register(r"applications", LeaveApplicationViewSet)
router.register(r"substitutes", SubstituteRequestViewSet)
router.register(r"holidays", HolidayCalendarViewSet)
router.register(r"policies", LeavePolicyViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
