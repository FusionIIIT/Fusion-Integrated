"""URL routing for the Visitors Hostel (VH) API."""
from rest_framework.routers import DefaultRouter

from modules.vh.api.views import (
    BillViewSet,
    BookingViewSet,
    InventoryItemViewSet,
    InventoryReplenishmentViewSet,
    MealBookingViewSet,
    RoomViewSet,
    TariffViewSet,
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

urlpatterns = router.urls
