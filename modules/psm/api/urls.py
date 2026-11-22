from django.urls import path

from modules.psm.api import views as v

urlpatterns = [
    # Indents
    path("indents", v.IndentListView.as_view(), name="psm-indents"),
    path("indents/<int:pk>", v.IndentDetailView.as_view(), name="psm-indent-detail"),
    path("indents/<int:pk>/submit", v.IndentSubmitView.as_view(), name="psm-indent-submit"),
    path(
        "indents/<int:pk>/dept-action",
        v.IndentDeptActionView.as_view(),
        name="psm-indent-dept-action",
    ),
    path("indents/<int:pk>/ps-action", v.IndentPSActionView.as_view(), name="psm-indent-ps-action"),
    path(
        "indents/<int:pk>/director-action",
        v.IndentDirectorActionView.as_view(),
        name="psm-indent-director-action",
    ),
    path("indents/<int:pk>/cancel", v.IndentCancelView.as_view(), name="psm-indent-cancel"),

    # Vendors
    path("vendors", v.VendorListView.as_view(), name="psm-vendors"),
    path("vendors/<int:pk>/verify", v.VendorVerifyView.as_view(), name="psm-vendor-verify"),

    # Purchase Orders
    path("purchase-orders", v.PurchaseOrderListView.as_view(), name="psm-purchase-orders"),
    path("purchase-orders/<int:pk>/issue", v.PurchaseOrderIssueView.as_view(), name="psm-po-issue"),

    # Goods Receipt
    path("goods-receipts", v.GoodsReceiptListView.as_view(), name="psm-goods-receipts"),
    path(
        "goods-receipts/<int:pk>/acknowledge",
        v.GoodsReceiptAcknowledgeView.as_view(),
        name="psm-grn-ack",
    ),
    path(
        "goods-receipts/<int:pk>/match-invoice",
        v.InvoiceMatchView.as_view(),
        name="psm-invoice-match",
    ),

    # Stock
    path("stock", v.StockListView.as_view(), name="psm-stock-list"),
    path("stock/fulfill", v.StockFulfillView.as_view(), name="psm-stock-fulfill"),

    # Discrepancies
    path("discrepancies", v.DiscrepancyListView.as_view(), name="psm-discrepancies"),
    path(
        "discrepancies/<int:pk>/resolve",
        v.DiscrepancyResolveView.as_view(),
        name="psm-discrepancy-resolve",
    ),

    # Items catalog
    path("items", v.ItemMasterListView.as_view(), name="psm-items"),
]
