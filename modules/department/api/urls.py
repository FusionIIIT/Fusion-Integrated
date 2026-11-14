from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.department.api.views import (
    AnnouncementViewSet,
    DepartmentDetailChangeViewSet,
    DepartmentDetailViewSet,
    DepartmentProfileViewSet,
    DepartmentViewSet,
    FeedbackViewSet,
    InventoryItemViewSet,
    LabResourceViewSet,
    StockRequestViewSet,
    TimetableSlotViewSet,
    TimetableViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet)
router.register("announcements", AnnouncementViewSet)
router.register("inventory", InventoryItemViewSet)
router.register("stock-requests", StockRequestViewSet)
router.register("feedback", FeedbackViewSet)
router.register("profiles", DepartmentProfileViewSet)
router.register("timetables", TimetableViewSet)
router.register("timetable-slots", TimetableSlotViewSet)
router.register("resources", LabResourceViewSet)
router.register("details", DepartmentDetailViewSet)
router.register("detail-changes", DepartmentDetailChangeViewSet)

urlpatterns = [path("", include(router.urls))]
