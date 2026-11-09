"""URL routing for the Visitors Hostel (VH) API."""
from rest_framework.routers import DefaultRouter

from modules.vh.api.views import (
    BillViewSet,
    BookingModificationViewSet,
    BookingViewSet,
    InventoryItemViewSet,
    InventoryReplenishmentViewSet,
    MealBookingViewSet,
    RoomViewSet,
    TariffViewSet,
    VHAlertViewSet,
    VHNotificationLogViewSet,
    VHReportViewSet,
    VHMSUserRoleViewSet,
    VisitorCategoryViewSet,
)

router = DefaultRouter()
router.register("categories", VisitorCategoryViewSet, basename="vh-categories")
router.register("rooms", RoomViewSet, basename="vh-rooms")
router.register("tariffs", TariffViewSet, basename="vh-tariffs")
router.register("bookings", BookingViewSet, basename="vh-bookings")
router.register("meals", MealBookingViewSet, basename="vh-meals")
router.register("bills", BillViewSet, basename="vh-bills")
router.register("inventory", InventoryItemViewSet, basename="vh-inventory")
router.register("replenishments", InventoryReplenishmentViewSet, basename="vh-replenishments")
router.register("modifications", BookingModificationViewSet, basename="vh-modifications")
router.register("roles", VHMSUserRoleViewSet, basename="vh-roles")
router.register("reports", VHReportViewSet, basename="vh-reports")
router.register("alerts", VHAlertViewSet, basename="vh-alerts")
router.register("notifications", VHNotificationLogViewSet, basename="vh-notifications")

urlpatterns = router.urls
