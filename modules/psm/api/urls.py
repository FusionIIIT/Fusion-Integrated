# URL routing for /api/v1/psm/ endpoints.
from django.urls import path

from modules.psm.api import views_finance_reports as vf
from modules.psm.api import views_indents as vi
from modules.psm.api import views_procurement as vp
from modules.psm.api import views_stock as vs

urlpatterns = [
    path("dashboard", vf.DashboardView.as_view(), name="psm-dashboard"),
    path("indents", vi.IndentListCreateView.as_view(), name="psm-indents"),
    path("indents/<int:indent_id>", vi.IndentDetailView.as_view(), name="psm-indent-detail"),
    path("indents/<int:indent_id>/submit", vi.IndentSubmitView.as_view(), name="psm-indent-submit"),
    path(
        "indents/<int:indent_id>/withdraw",
        vi.IndentWithdrawView.as_view(),
        name="psm-indent-withdraw",
    ),
    path("indents/<int:indent_id>/repeat", vi.IndentRepeatView.as_view(), name="psm-indent-repeat"),
    path(
        "indents/<int:indent_id>/stock-check",
        vi.IndentStockCheckView.as_view(),
        name="psm-indent-stock-check",
    ),
    path(
        "indents/<int:indent_id>/review",
        vi.IndentDeptAdminReviewView.as_view(),
        name="psm-indent-review",
    ),
    path(
        "indents/<int:indent_id>/recommend",
        vi.IndentHodRecommendView.as_view(),
        name="psm-indent-recommend",
    ),
    path(
        "indents/<int:indent_id>/procurement-review",
        vi.IndentProcurementReviewView.as_view(),
        name="psm-indent-proc-review",
    ),
    path(
        "indents/<int:indent_id>/final-decision",
        vi.IndentFinalDecisionView.as_view(),
        name="psm-indent-final-decision",
    ),
    path("stock/items", vs.StockItemListCreateView.as_view(), name="psm-stock-items"),
    path("stock/locations", vs.StockLocationListCreateView.as_view(), name="psm-stock-locations"),
    path("stock/availability", vs.StockAvailabilityView.as_view(), name="psm-stock-availability"),
    path("stock/adjustments", vs.StockAdjustmentCreateView.as_view(), name="psm-stock-adjustments"),
    path("internal-issues", vs.InternalIssueListView.as_view(), name="psm-internal-issues"),
    path(
        "internal-issues/<int:issue_id>/schedule-picking",
        vs.InternalIssuePickView.as_view(),
        name="psm-internal-issue-pick",
    ),
    path(
        "internal-issues/<int:issue_id>/dispatch",
        vs.InternalIssueDispatchView.as_view(),
        name="psm-internal-issue-dispatch",
    ),
    path("transfers", vs.StockTransferListCreateView.as_view(), name="psm-transfers"),
    path(
        "transfers/<int:transfer_id>/dispatch",
        vs.StockTransferDispatchView.as_view(),
        name="psm-transfer-dispatch",
    ),
    path(
        "transfers/<int:transfer_id>/confirm",
        vs.StockTransferConfirmView.as_view(),
        name="psm-transfer-confirm",
    ),
    path(
        "transfers/<int:transfer_id>/cancel",
        vs.StockTransferCancelView.as_view(),
        name="psm-transfer-cancel",
    ),
    path("vendors", vp.VendorListCreateView.as_view(), name="psm-vendors"),
    path("vendors/<int:vendor_id>", vp.VendorDetailView.as_view(), name="psm-vendor-detail"),
    path("vendors/<int:vendor_id>/verify", vp.VendorVerifyView.as_view(), name="psm-vendor-verify"),
    path("tenders", vp.TenderListCreateView.as_view(), name="psm-tenders"),
    path(
        "tenders/<int:tender_id>/publish", vp.TenderPublishView.as_view(), name="psm-tender-publish"
    ),
    path("tenders/<int:tender_id>/bids", vp.TenderBidCreateView.as_view(), name="psm-tender-bids"),
    path(
        "tenders/<int:tender_id>/evaluate",
        vp.TenderEvaluateView.as_view(),
        name="psm-tender-evaluate",
    ),
    path("tenders/<int:tender_id>/award", vp.TenderAwardView.as_view(), name="psm-tender-award"),
    path("purchase-orders", vp.PurchaseOrderListCreateView.as_view(), name="psm-purchase-orders"),
    path(
        "purchase-orders/<int:po_id>",
        vp.PurchaseOrderUpdateView.as_view(),
        name="psm-purchase-order-update",
    ),
    path("grns", vp.GrnListCreateView.as_view(), name="psm-grns"),
    path("grns/<int:grn_id>/confirm", vp.GrnConfirmView.as_view(), name="psm-grn-confirm"),
    path("discrepancies", vp.DiscrepancyListCreateView.as_view(), name="psm-discrepancies"),
    path(
        "discrepancies/<int:case_id>/communications",
        vp.DiscrepancyCommCreateView.as_view(),
        name="psm-discrepancy-comms",
    ),
    path(
        "discrepancies/<int:case_id>/resolve",
        vp.DiscrepancyResolveView.as_view(),
        name="psm-discrepancy-resolve",
    ),
    path("invoices", vf.InvoiceListCreateView.as_view(), name="psm-invoices"),
    path(
        "invoices/<int:invoice_id>/verify",
        vf.InvoiceVerifyView.as_view(),
        name="psm-invoice-verify",
    ),
    path("invoices/<int:invoice_id>/hold", vf.InvoiceHoldView.as_view(), name="psm-invoice-hold"),
    path("invoices/<int:invoice_id>/pay", vf.InvoicePayView.as_view(), name="psm-invoice-pay"),
    path("reports/generate", vf.ReportGenerateView.as_view(), name="psm-reports-generate"),
    path("reports/export", vf.ReportExportView.as_view(), name="psm-reports-export"),
    path(
        "reports/schedules", vf.ReportScheduleListCreateView.as_view(), name="psm-report-schedules"
    ),
    path(
        "reports/schedules/<int:schedule_id>",
        vf.ReportScheduleUpdateView.as_view(),
        name="psm-report-schedule-update",
    ),
    path(
        "reports/schedules/<int:schedule_id>/run",
        vf.ReportScheduleRunView.as_view(),
        name="psm-report-schedule-run",
    ),
    path("reports/logs", vf.ReportGenerationLogListView.as_view(), name="psm-report-logs"),
    path("audit", vf.AuditLogListView.as_view(), name="psm-audit"),
    path("notifications", vf.NotificationListView.as_view(), name="psm-notifications"),
    path("policy", vf.PolicyListCreateView.as_view(), name="psm-policy"),
]
