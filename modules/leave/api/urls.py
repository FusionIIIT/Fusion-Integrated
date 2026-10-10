from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LeaveApplicationViewSet, LeaveBalanceViewSet, OfflineLeaveRecordViewSet,
    LeavePolicyViewSet, HolidayCalendarViewSet, AdminControlView
)

router = DefaultRouter()
router.register(r"applications", LeaveApplicationViewSet, basename="leave-application")
router.register(r"balances", LeaveBalanceViewSet, basename="leave-balance")
router.register(r"offline-records", OfflineLeaveRecordViewSet, basename="offline-leave")
router.register(r"policies", LeavePolicyViewSet, basename="leave-policy")
router.register(r"holidays", HolidayCalendarViewSet, basename="holiday-calendar")

urlpatterns = [
    path("", include(router.urls)),
    path("year-end-process/", AdminControlView.as_view(), name="year-end-process"),
]
