"""Authenticated purchase and stores endpoints."""

import csv
from decimal import Decimal

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.purchase_stores.api import serializers as s
from modules.purchase_stores.models import (
    Bid,
    DiscrepancyCase,
    Indent,
    PurchaseOrder,
    ReportGeneration,
    ScheduledReport,
    StockBalance,
    Tender,
    Vendor,
    VendorInvoice,
    VendorVersion,
    WorkflowAction,
)
from modules.purchase_stores.selectors import records
from modules.purchase_stores.services import workflow

MODULE = HasModuleGrant("purchase_stores")


def _schema_ready(view_class):
    """Give APIView operations an explicit JSON contract in the API schema."""
    allowed = {name.lower() for name in view_class.http_method_names}
    for method in ("get", "post", "put", "patch", "delete"):
        if method not in allowed:
            continue
        handler = getattr(view_class, method, None)
        if handler is None:
            continue
        setattr(
            view_class,
            method,
            extend_schema(
                request=OpenApiTypes.OBJECT if method in {"post", "put", "patch"} else None,
                responses=OpenApiTypes.OBJECT,
                operation_id=f"psm_{view_class.__name__}_{method}",
            )(handler),
        )
    return view_class


@_schema_ready
class IndentListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            permission = "purchase_stores.indent.create"
        elif getattr(self.request, "principal", None) and self.request.principal.has_permission(
            "purchase_stores.indent.view"
        ):
            permission = "purchase_stores.indent.view"
        else:
            permission = "purchase_stores.indent.view_self"
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        queryset = records.indents_for(request.principal)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response(s.IndentSerializer(queryset, many=True).data)

    def post(self, request):
        payload = s.IndentCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data.copy()
        priority = data.pop("priority", "")
        indent = workflow.create_indent(actor=request.principal, priority=priority, **data)
        return Response(s.IndentSerializer(indent).data, status=status.HTTP_201_CREATED)


@_schema_ready
class IndentDetailView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.indent.view"
            if getattr(self.request, "principal", None)
            and self.request.principal.has_permission("purchase_stores.indent.view")
            else "purchase_stores.indent.view_self"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request, pk):
        indent = get_object_or_404(records.indents_for(request.principal), pk=pk)
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class IndentModifyView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.indent.create")]

    def patch(self, request, pk):
        payload = s.IndentModifySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        indent = workflow.modify_indent(
            actor=request.principal, indent_id=pk, **payload.validated_data
        )
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class IndentRepeatView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.indent.create")]

    def post(self, request, pk):
        original = get_object_or_404(records.indents_for(request.principal), pk=pk)
        lines = list(
            original.lines.values(
                "item_name", "description", "quantity", "unit", "estimated_unit_cost", "sku"
            )
        )
        indent = workflow.create_indent(
            actor=request.principal,
            department_id=original.department_id,
            justification=original.justification,
            lines=lines,
            draft=True,
        )
        return Response(s.IndentSerializer(indent).data, status=status.HTTP_201_CREATED)


@_schema_ready
class IndentTransitionView(APIView):
    def get_permissions(self):
        target = self.request.data.get("to_status") if self.request.method == "POST" else None
        permission = (
            "purchase_stores.indent.withdraw"
            if target in {Indent.Status.WITHDRAWN, Indent.Status.CANCELLED}
            else "purchase_stores.indent.review"
        )
        return [MODULE(), HasPermission(permission)()]

    def post(self, request, pk):
        payload = s.IndentTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        indent = workflow.transition_indent(
            actor=request.principal, indent_id=pk, **payload.validated_data
        )
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class IndentStockCheckView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.stock.manage")]

    def post(self, request, pk):
        indent = workflow.check_and_reserve_stock(actor=request.principal, indent_id=pk)
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class InternalIssueView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.stock.manage")]

    def post(self, request, pk):
        indent = workflow.process_internal_issue(actor=request.principal, indent_id=pk)
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class InternalReceiptConfirmView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.indent.create")]

    def post(self, request, pk):
        indent = workflow.confirm_internal_receipt(
            actor=request.principal,
            indent_id=pk,
            reason=str(request.data.get("note", "")),
        )
        return Response(s.IndentSerializer(indent).data)


@_schema_ready
class StockListView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.stock.view")]

    def get(self, request):
        return Response(
            s.StockBalanceSerializer(records.stock_for(request.principal), many=True).data
        )


@_schema_ready
class VendorListCreateView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.vendor.manage"
            if self.request.method == "POST"
            else "purchase_stores.po.view"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        return Response(s.VendorSerializer(Vendor.objects.all(), many=True).data)

    def post(self, request):
        payload = s.VendorInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        vendor = workflow.create_vendor(actor=request.principal, data=payload.validated_data)
        return Response(s.VendorSerializer(vendor).data, status=status.HTTP_201_CREATED)


@_schema_ready
class VendorVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.vendor.manage")]

    def post(self, request, pk):
        vendor = get_object_or_404(Vendor.objects, pk=pk)
        if vendor.status == Vendor.Status.SUSPENDED:
            return Response(
                {"detail": "A suspended vendor cannot be verified."},
                status=status.HTTP_409_CONFLICT,
            )
        if not vendor.gst_number or not vendor.bank_details or not vendor.compliance_documents:
            return Response(
                {"detail": "GST, bank, and compliance records are required before verification."},
                status=status.HTTP_409_CONFLICT,
            )
        if vendor.status != Vendor.Status.VERIFIED:
            vendor.status = Vendor.Status.VERIFIED
            vendor.version += 1
            vendor.save(update_fields=["status", "version", "updated_at"])
            VendorVersion.objects.create(
                vendor=vendor,
                version=vendor.version,
                actor_user_id=request.principal.user_id,
                snapshot={
                    "legal_name": vendor.legal_name,
                    "gst_number": vendor.gst_number,
                    "bank_details": vendor.bank_details,
                    "compliance_documents": vendor.compliance_documents,
                    "status": vendor.status,
                },
            )
        return Response(s.VendorSerializer(vendor).data)


@_schema_ready
class PurchaseOrderListCreateView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.po.manage"
            if self.request.method == "POST"
            else "purchase_stores.po.view"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        return Response(
            s.PurchaseOrderSerializer(records.orders_for(request.principal), many=True).data
        )

    def post(self, request):
        payload = s.PurchaseOrderCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        order = workflow.issue_purchase_order(actor=request.principal, **payload.validated_data)
        return Response(s.PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


@_schema_ready
class ReceiptCreateView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.receipt.manage")]

    def post(self, request, purchase_order_id):
        payload = s.ReceiptInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        receipt = workflow.record_goods_receipt(
            actor=request.principal, purchase_order_id=purchase_order_id, **payload.validated_data
        )
        return Response(s.GoodsReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


@_schema_ready
class ReceiptConfirmView(APIView):
    def get_permissions(self):
        return [MODULE(), HasPermission("purchase_stores.indent.create")()]

    def post(self, request, pk):
        receipt = workflow.confirm_goods_receipt(actor=request.principal, receipt_id=pk)
        return Response(s.GoodsReceiptSerializer(receipt).data)


@_schema_ready
class DiscrepancyListCreateView(APIView):
    http_method_names = ["get", "options"]
    permission_classes = [MODULE, HasPermission("purchase_stores.audit.view")]

    def get(self, request):
        return Response(list(DiscrepancyCase.objects.values()))


@_schema_ready
class ReceiptDiscrepancyCreateView(APIView):
    http_method_names = ["post", "options"]

    def get_permissions(self):
        permission = (
            "purchase_stores.indent.create"
            if getattr(self.request, "principal", None)
            and self.request.principal.has_permission("purchase_stores.indent.create")
            else "purchase_stores.discrepancy.manage"
        )
        return [MODULE(), HasPermission(permission)()]

    def post(self, request, receipt_id):
        description = str(request.data.get("description", "")).strip()
        if not description:
            return Response(
                {"description": "This field is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        case = workflow.create_discrepancy_case(
            actor=request.principal,
            receipt_id=receipt_id,
            description=description,
            evidence=request.data.get("evidence", []),
        )
        return Response({"id": case.pk, "status": case.status}, status=status.HTTP_201_CREATED)


@_schema_ready
class DiscrepancyResolutionView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.discrepancy.manage")]

    def post(self, request, pk):
        payload = s.DiscrepancyResolutionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        case = workflow.resolve_discrepancy(
            actor=request.principal, case_id=pk, **payload.validated_data
        )
        return Response({"id": case.pk, "status": case.status, "resolution": case.resolution})


@_schema_ready
class InvoiceListView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.invoice.manage")]

    def get(self, request):
        return Response(s.VendorInvoiceSerializer(VendorInvoice.objects.all(), many=True).data)


@_schema_ready
class InvoiceVerificationView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.invoice.manage")]

    def post(self, request):
        payload = s.InvoiceVerificationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        invoice = workflow.verify_invoice(actor=request.principal, **payload.validated_data)
        return Response(s.VendorInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


@_schema_ready
class PaymentView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.invoice.manage")]

    def post(self, request, invoice_id):
        payload = s.PaymentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        payment = workflow.process_payment(
            actor=request.principal, invoice_id=invoice_id, **payload.validated_data
        )
        return Response(
            {"id": payment.pk, "amount": payment.amount, "paid_at": payment.paid_at},
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class StockTransferListCreateView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.stock.manage"
            if self.request.method == "POST"
            else "purchase_stores.stock.view"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        transfers = records.transfers_for(request.principal)
        return Response(s.StockTransferSerializer(transfers, many=True).data)

    def post(self, request):
        payload = s.StockTransferInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        transfer = workflow.create_stock_transfer(actor=request.principal, **payload.validated_data)
        return Response(s.StockTransferSerializer(transfer).data, status=status.HTTP_201_CREATED)


@_schema_ready
class StockTransferActionView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.stock.manage")]

    def post(self, request, pk, action):
        functions = {
            "dispatch": workflow.dispatch_stock_transfer,
            "receive": workflow.receive_stock_transfer,
        }
        operation = functions.get(action)
        if operation is None:
            return Response(
                {"detail": "Action must be dispatch or receive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        transfer = operation(actor=request.principal, transfer_id=pk)
        return Response(s.StockTransferSerializer(transfer).data)


@_schema_ready
class TenderListCreateView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.tender.manage"
            if self.request.method == "POST"
            else "purchase_stores.indent.view"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        return Response(list(Tender.objects.values()))

    def post(self, request):
        payload = s.TenderInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        indent = get_object_or_404(Indent, pk=payload.validated_data["indent_id"])
        if indent.status != Indent.Status.PROCUREMENT_AUTHORIZED:
            return Response(
                {"detail": "Tender requires an authorized procurement indent."},
                status=status.HTTP_409_CONFLICT,
            )
        threshold = workflow.policy_value("procurement_method_threshold")
        if threshold is None:
            return Response(
                {"detail": "Configure procurement_method_threshold before publishing a tender."},
                status=status.HTTP_409_CONFLICT,
            )
        amount = sum((line.quantity * line.estimated_unit_cost for line in indent.lines.all()), 0)
        if amount < Decimal(str(threshold)):
            return Response(
                {"detail": "The indent is below the configured tender threshold."},
                status=status.HTTP_409_CONFLICT,
            )
        tender = Tender.objects.create(
            indent=indent,
            reference=workflow._reference("TND"),
            evaluation_criteria=payload.validated_data["evaluation_criteria"],
            status=Tender.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        return Response(
            {"id": tender.pk, "reference": tender.reference, "status": tender.status},
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class PolicySettingView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.policy.manage"
            if self.request.method in {"POST", "PUT"}
            else "purchase_stores.indent.view"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        from modules.purchase_stores.models import PolicySetting

        return Response(
            list(
                PolicySetting.objects.order_by("key").values(
                    "key", "value", "description", "updated_at"
                )
            )
        )

    def post(self, request):
        payload = s.PolicySettingInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        setting = workflow.set_policy_value(actor=request.principal, **payload.validated_data)
        return Response(
            {"key": setting.key, "value": setting.value, "updated_at": setting.updated_at},
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class DepartmentAccessView(APIView):
    http_method_names = ["get", "post", "options"]

    def get_permissions(self):
        return [MODULE(), HasPermission("purchase_stores.policy.manage")()]

    def get(self, request):
        from modules.purchase_stores.models import DepartmentAccess

        return Response(
            list(
                DepartmentAccess.objects.filter(is_active=True)
                .order_by("department_id", "user_id")
                .values("user_id", "department_id", "assigned_by_user_id", "created_at")
            )
        )

    def post(self, request):
        payload = s.DepartmentAccessInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        access = workflow.grant_department_access(actor=request.principal, **payload.validated_data)
        return Response(
            {"user_id": access.user_id, "department_id": access.department_id},
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class DepartmentAccessRevokeView(APIView):
    http_method_names = ["delete", "options"]
    permission_classes = [MODULE, HasPermission("purchase_stores.policy.manage")]

    def delete(self, request, user_id, department_id):
        workflow.revoke_department_access(
            actor=request.principal, user_id=user_id, department_id=department_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@_schema_ready
class TenderBidView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.tender.manage")]

    def post(self, request, tender_id):
        payload = s.TenderBidInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tender = get_object_or_404(Tender, pk=tender_id)
        vendor = get_object_or_404(
            Vendor, pk=payload.validated_data["vendor_id"], status=Vendor.Status.VERIFIED
        )
        if tender.status != Tender.Status.PUBLISHED:
            return Response(
                {"detail": "This tender is not accepting bids."}, status=status.HTTP_409_CONFLICT
            )
        bid = Bid.objects.create(
            tender=tender,
            vendor=vendor,
            amount=payload.validated_data["amount"],
            proposal=payload.validated_data["proposal"],
        )
        return Response(
            {"id": bid.pk, "tender_id": tender.pk, "vendor_id": vendor.pk},
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class TenderAwardView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.tender.manage")]

    def post(self, request, tender_id, bid_id):
        roles = {role.lower() for role in request.principal.roles}
        if (
            "procurement_committee" not in roles
            and (request.principal.active_role or "").lower() != "procurement_committee"
        ):
            return Response(
                {"detail": "Only the Procurement Committee may approve tender selection."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tender = get_object_or_404(Tender, pk=tender_id)
        bid = get_object_or_404(Bid, pk=bid_id, tender=tender)
        if not request.data.get("committee_approved"):
            return Response(
                {"detail": "Committee approval is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        bid.committee_approved = True
        bid.evaluation = request.data.get("evaluation", {})
        bid.save(update_fields=["committee_approved", "evaluation", "updated_at"])
        tender.selected_bid = bid
        tender.status = Tender.Status.AWARDED
        tender.save(update_fields=["selected_bid", "status", "updated_at"])
        return Response({"id": tender.pk, "status": tender.status, "selected_bid_id": bid.pk})


@_schema_ready
class ReportView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.report.view")]

    def get(self, request):
        report_code = request.query_params.get("report_code", "operations")
        valid = {"operations", "procurement", "stock", "financial"}
        if report_code not in valid:
            return Response(
                {"report_code": f"Choose one of {sorted(valid)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        output_format = request.query_params.get("format", "json")
        if output_format not in {"json", "csv"}:
            return Response({"format": "Choose json or csv."}, status=status.HTTP_400_BAD_REQUEST)
        filters = request.query_params.dict()
        ReportGeneration.objects.create(
            report_code=report_code,
            requested_by_user_id=request.principal.user_id,
            filters=filters,
            output_format=output_format,
        )
        indents = Indent.objects.all()
        invoices = VendorInvoice.objects.all()
        if filters.get("status"):
            indents = indents.filter(status=filters["status"])
            invoices = invoices.filter(status=filters["status"])
        data = {
            "indents": list(indents.values("status").annotate(count=Count("id"))),
            "purchase_orders": list(
                PurchaseOrder.objects.values("status").annotate(count=Count("id"))
            ),
            "stock": StockBalance.objects.aggregate(
                on_hand=Sum("quantity_on_hand"), reserved=Sum("quantity_reserved")
            ),
            "invoices": list(invoices.values("status").annotate(count=Count("id"))),
        }
        if output_format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="psm-{report_code}.csv"'
            writer = csv.writer(response)
            writer.writerow(["report", "section", "status", "count", "value"])
            for section in ("indents", "purchase_orders", "invoices"):
                for row in data[section]:
                    writer.writerow([report_code, section, row["status"], row["count"], ""])
            for value in data["stock"].values():
                writer.writerow([report_code, "stock", "", "", value])
            return response
        return Response({"report_code": report_code, "generated_at": timezone.now(), "data": data})


@_schema_ready
class ScheduledReportView(APIView):
    def get_permissions(self):
        permission = (
            "purchase_stores.report.view"
            if self.request.method == "GET"
            else "purchase_stores.policy.manage"
        )
        return [MODULE(), HasPermission(permission)()]

    def get(self, request):
        rows = ScheduledReport.objects.all()
        if not request.principal.has_permission("purchase_stores.policy.manage"):
            rows = rows.filter(owner_user_id=request.principal.user_id)
        return Response(list(rows.values()))

    def post(self, request):
        payload = s.ScheduledReportInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        schedule = ScheduledReport.objects.create(
            owner_user_id=request.principal.user_id, **payload.validated_data
        )
        return Response(
            {
                "id": schedule.pk,
                "report_code": schedule.report_code,
                "next_run_at": schedule.next_run_at,
            },
            status=status.HTTP_201_CREATED,
        )


@_schema_ready
class AuditLogView(APIView):
    permission_classes = [MODULE, HasPermission("purchase_stores.audit.view")]

    def get(self, request):
        actions = WorkflowAction.objects.order_by("-at")[:500]
        return Response(s.WorkflowActionSerializer(actions, many=True).data)
