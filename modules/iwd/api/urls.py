from rest_framework.routers import DefaultRouter

from modules.iwd.api.views import (
    RequestViewSet,
    WorkOrderViewSet,
    VendorViewSet,
    BillViewSet,
    BillItemViewSet,
    BudgetViewSet,
    ProposalViewSet,
    ProposalItemViewSet,
    InventoryItemViewSet,
    InventoryTransactionViewSet,
    FeedbackViewSet,
    SLAEscalationViewSet,
)

router = DefaultRouter()
router.register(r"requests", RequestViewSet, basename="iwd-requests")
router.register(r"work-orders", WorkOrderViewSet, basename="iwd-work-orders")
router.register(r"vendors", VendorViewSet, basename="iwd-vendors")
router.register(r"bills", BillViewSet, basename="iwd-bills")
router.register(r"bill-items", BillItemViewSet, basename="iwd-bill-items")
router.register(r"budgets", BudgetViewSet, basename="iwd-budgets")
router.register(r"proposals", ProposalViewSet, basename="iwd-proposals")
router.register(r"proposal-items", ProposalItemViewSet, basename="iwd-proposal-items")
router.register(r"inventory-items", InventoryItemViewSet, basename="iwd-inventory-items")
router.register(r"inventory-transactions", InventoryTransactionViewSet, basename="iwd-inventory-transactions")
router.register(r"feedback", FeedbackViewSet, basename="iwd-feedback")
router.register(r"sla-escalations", SLAEscalationViewSet, basename="iwd-sla-escalations")

urlpatterns = router.urls
