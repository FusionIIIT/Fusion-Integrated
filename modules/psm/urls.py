"""URL routing for PSM module."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.psm.views import (
    DeliveryDiscrepancyViewSet,
    GoodsReceiptViewSet,
    IndentViewSet,
    InvoiceViewSet,
    PaymentViewSet,
    PSMAuditLogViewSet,
    PurchaseOrderViewSet,
    StockTransferViewSet,
    StockViewSet,
    VendorViewSet,
)

router = DefaultRouter()
router.register(r"indents", IndentViewSet, basename="psm-indents")
router.register(r"stock", StockViewSet, basename="psm-stock")
router.register(r"transfers", StockTransferViewSet, basename="psm-transfers")
router.register(r"vendors", VendorViewSet, basename="psm-vendors")
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="psm-pos")
router.register(r"grn", GoodsReceiptViewSet, basename="psm-grn")
router.register(r"discrepancies", DeliveryDiscrepancyViewSet, basename="psm-discrepancies")
router.register(r"invoices", InvoiceViewSet, basename="psm-invoices")
router.register(r"payments", PaymentViewSet, basename="psm-payments")
router.register(r"audit", PSMAuditLogViewSet, basename="psm-audit")

urlpatterns = [
    path("", include(router.urls)),
]
