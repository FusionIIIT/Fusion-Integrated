from rest_framework.routers import DefaultRouter

from .views import (
    EmployeeViewSet,
    HolidayCalendarViewSet,
    LeaveApplicationViewSet,
    LeavePolicyViewSet,
)

router = DefaultRouter()
router.register("policies", LeavePolicyViewSet, basename="elm-policy")
router.register("holidays", HolidayCalendarViewSet, basename="elm-holiday")
router.register("colleagues", EmployeeViewSet, basename="elm-colleague")
router.register("applications", LeaveApplicationViewSet, basename="elm-application")

urlpatterns = router.urls
