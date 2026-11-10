"""
PSM Module API URL routing.
Mounts endpoints for indents, vendors, purchase orders, GRN, and stock transfers.
"""

from django.urls import path
from .views import (
    IndentListCreateView,
    IndentDetailView,
    IndentTransitionView,
    IndentWithdrawView,
    IndentVersionListView,
    VendorListCreateView,
    VendorDetailView,
    PurchaseOrderListCreateView,
    GoodsReceiptNoteCreateView,
    StockItemListView,
    StockTransferListCreateView,
)

urlpatterns = [
    # Indents
    path("indents/", IndentListCreateView.as_view(), name="psm-indent-list-create"),
    path("indents/<int:pk>/", IndentDetailView.as_view(), name="psm-indent-detail"),
    path("indents/<int:pk>/transition/", IndentTransitionView.as_view(), name="psm-indent-transition"),
    path("indents/<int:pk>/withdraw/", IndentWithdrawView.as_view(), name="psm-indent-withdraw"),
    path("indents/<int:pk>/versions/", IndentVersionListView.as_view(), name="psm-indent-versions"),

    # Vendors
    path("vendors/", VendorListCreateView.as_view(), name="psm-vendor-list-create"),
    path("vendors/<int:pk>/", VendorDetailView.as_view(), name="psm-vendor-detail"),

    # Purchase Orders & GRN
    path("purchase-orders/", PurchaseOrderListCreateView.as_view(), name="psm-po-list-create"),
    path("grn/", GoodsReceiptNoteCreateView.as_view(), name="psm-grn-create"),

    # Stock Items & Transfers
    path("stock-items/", StockItemListView.as_view(), name="psm-stock-item-list"),
    path("transfers/", StockTransferListCreateView.as_view(), name="psm-transfer-list-create"),
]
