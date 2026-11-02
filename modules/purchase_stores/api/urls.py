from django.urls import path

from modules.purchase_stores.api import views

urlpatterns = [
    path("indents", views.IndentListCreateView.as_view(), name="psm-indents"),
    path("indents/<int:pk>", views.IndentDetailView.as_view(), name="psm-indent"),
    path("indents/<int:pk>/modify", views.IndentModifyView.as_view(), name="psm-indent-modify"),
    path("indents/<int:pk>/repeat", views.IndentRepeatView.as_view(), name="psm-indent-repeat"),
    path(
        "indents/<int:pk>/transition",
        views.IndentTransitionView.as_view(),
        name="psm-indent-transition",
    ),
    path(
        "indents/<int:pk>/stock-check",
        views.IndentStockCheckView.as_view(),
        name="psm-indent-stock-check",
    ),
    path(
        "indents/<int:pk>/internal-issue",
        views.InternalIssueView.as_view(),
        name="psm-internal-issue",
    ),
    path(
        "indents/<int:pk>/internal-receipt",
        views.InternalReceiptConfirmView.as_view(),
        name="psm-internal-receipt",
    ),
    path("stock", views.StockListView.as_view(), name="psm-stock"),
    path("vendors", views.VendorListCreateView.as_view(), name="psm-vendors"),
    path("vendors/<int:pk>/verify", views.VendorVerifyView.as_view(), name="psm-vendor-verify"),
    path(
        "purchase-orders", views.PurchaseOrderListCreateView.as_view(), name="psm-purchase-orders"
    ),
    path(
        "purchase-orders/<int:purchase_order_id>/receipts",
        views.ReceiptCreateView.as_view(),
        name="psm-receipts",
    ),
    path(
        "receipts/<int:pk>/confirm", views.ReceiptConfirmView.as_view(), name="psm-receipt-confirm"
    ),
    path(
        "receipts/<int:receipt_id>/discrepancies",
        views.ReceiptDiscrepancyCreateView.as_view(),
        name="psm-receipt-discrepancies",
    ),
    path("discrepancies", views.DiscrepancyListCreateView.as_view(), name="psm-discrepancy-list"),
    path(
        "discrepancies/<int:pk>/resolve",
        views.DiscrepancyResolutionView.as_view(),
        name="psm-discrepancy-resolve",
    ),
    path("invoices", views.InvoiceListView.as_view(), name="psm-invoices"),
    path("invoices/verify", views.InvoiceVerificationView.as_view(), name="psm-invoice-verify"),
    path("invoices/<int:invoice_id>/payments", views.PaymentView.as_view(), name="psm-payments"),
    path("transfers", views.StockTransferListCreateView.as_view(), name="psm-transfers"),
    path(
        "transfers/<int:pk>/<str:action>",
        views.StockTransferActionView.as_view(),
        name="psm-transfer-action",
    ),
    path("tenders", views.TenderListCreateView.as_view(), name="psm-tenders"),
    path("tenders/<int:tender_id>/bids", views.TenderBidView.as_view(), name="psm-tender-bids"),
    path(
        "tenders/<int:tender_id>/bids/<int:bid_id>/award",
        views.TenderAwardView.as_view(),
        name="psm-tender-award",
    ),
    path("reports", views.ReportView.as_view(), name="psm-reports"),
    path("reports/schedules", views.ScheduledReportView.as_view(), name="psm-report-schedules"),
    path("audit", views.AuditLogView.as_view(), name="psm-audit"),
    path("policies", views.PolicySettingView.as_view(), name="psm-policies"),
    path("departments/access", views.DepartmentAccessView.as_view(), name="psm-department-access"),
    path(
        "departments/access/<int:user_id>/<int:department_id>",
        views.DepartmentAccessRevokeView.as_view(),
        name="psm-department-access-revoke",
    ),
]
