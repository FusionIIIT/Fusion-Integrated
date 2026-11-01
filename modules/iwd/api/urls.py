"""URL routes for IWD."""
from rest_framework.routers import DefaultRouter
from modules.iwd.api.views import (
    ComplaintViewSet,
    EstimateViewSet,
    InventoryItemViewSet,
    WorkVerificationViewSet,
    BillAndSettlementViewSet,
    ComplaintFeedbackViewSet,
)

router = DefaultRouter()
router.register(r"complaints", ComplaintViewSet, basename="complaint")
router.register(r"estimates", EstimateViewSet, basename="estimate")
router.register(r"inventory", InventoryItemViewSet, basename="inventory")
router.register(r"verifications", WorkVerificationViewSet, basename="verification")
router.register(r"bills", BillAndSettlementViewSet, basename="bill")
router.register(r"feedback", ComplaintFeedbackViewSet, basename="feedback")

urlpatterns = router.urls

