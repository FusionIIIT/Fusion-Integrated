from rest_framework.routers import DefaultRouter

from modules.iwd.api.views import (
    ContractorViewSet,
    InventoryItemViewSet,
    WorkRequestViewSet,
)

router = DefaultRouter()
router.register(r"requests", WorkRequestViewSet, basename="iwd-work-request")
router.register(r"contractors", ContractorViewSet, basename="iwd-contractor")
router.register(r"inventory", InventoryItemViewSet, basename="iwd-inventory")

urlpatterns = router.urls

