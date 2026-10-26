from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    HolidayCalendarViewSet,
    LeaveApplicationViewSet,
    LeavePolicyViewSet,
)

router = DefaultRouter()
router.register(r"policies", LeavePolicyViewSet, basename="elm-policies")
router.register(r"holidays", HolidayCalendarViewSet, basename="elm-holidays")
router.register(r"leave-applications", LeaveApplicationViewSet, basename="elm-leave-applications")

urlpatterns = [
    path("", include(router.urls)),
]
