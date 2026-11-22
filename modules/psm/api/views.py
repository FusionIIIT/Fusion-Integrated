from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.psm.api.permissions import RequirePermission
from modules.psm.api.serializers import (
    DiscrepancyReportSerializer,
    GoodsReceiptNoteSerializer,
    GRNCreateSerializer,
    IndentActionSerializer,
    IndentCreateSerializer,
    IndentSerializer,
    ItemMasterSerializer,
    POCreateSerializer,
    PurchaseOrderSerializer,
    StockIssueSerializer,
    StockItemSerializer,
    VendorSerializer,
)
from modules.psm.domain.validators import ValidationError
from modules.psm.models.discrepancy import DiscrepancyReport
from modules.psm.models.goods_receipt import GoodsReceiptNote
from modules.psm.models.indent import Indent
from modules.psm.models.inventory import StockItem
from modules.psm.models.item import ItemMaster
from modules.psm.models.purchase_order import PurchaseOrder
from modules.psm.models.vendor import Vendor
from modules.psm.selectors.scoping import (
    scope_goods_receipts,
    scope_indents_for_user,
    scope_purchase_orders,
)
from modules.psm.services.discrepancy_service import resolve_discrepancy
from modules.psm.services.grn_service import acknowledge_grn, create_grn
from modules.psm.services.indent_service import (
    cancel_indent,
    create_indent,
    review_dept_indent,
    review_director_indent,
    review_ps_indent,
    submit_indent,
)
from modules.psm.services.inventory_service import fulfill_internal_stock
from modules.psm.services.po_service import (
    create_purchase_order,
    issue_purchase_order,
)
from modules.psm.services.vendor_service import register_vendor, verify_vendor


def get_user_id(request) -> int:
    principal = getattr(request, "principal", None) or getattr(request, "user", None)
    return getattr(principal, "user_id", 1)


# -- Indents -------------------------------------------------------------------
class IndentListView(APIView):
    permission_classes = [RequirePermission("psm.indent.view", "psm.indent.create")]

    @extend_schema(
        operation_id="psm_indents_list",
        responses={200: IndentSerializer(many=True)},
    )
    def get(self, request):
        qs = scope_indents_for_user(
            request.user,
            Indent.objects.all().prefetch_related("items__item_master"),
        )
        serializer = IndentSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="psm_indents_create",
        request=IndentCreateSerializer,
        responses={201: IndentSerializer, 400: dict},
    )
    def post(self, request):
        serializer = IndentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            indent = create_indent(
                user_id=user_id,
                department_code=serializer.validated_data["department_code"],
                title=serializer.validated_data["title"],
                purpose=serializer.validated_data["purpose"],
                priority=serializer.validated_data["priority"],
                items_data=serializer.validated_data["items"],
            )
            return Response(IndentSerializer(indent).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IndentDetailView(APIView):
    permission_classes = [RequirePermission("psm.indent.view")]

    @extend_schema(
        operation_id="psm_indents_detail",
        responses={200: IndentSerializer},
    )
    def get(self, request, pk: int):
        qs = scope_indents_for_user(
            request.user,
            Indent.objects.all().prefetch_related("items__item_master"),
        )
        indent = get_object_or_404(qs, pk=pk)
        return Response(IndentSerializer(indent).data)


class IndentSubmitView(APIView):
    permission_classes = [RequirePermission("psm.indent.create")]

    @extend_schema(
        operation_id="psm_indents_submit",
        request=None,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        try:
            indent = submit_indent(indent_id=pk, user_id=user_id)
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IndentDeptActionView(APIView):
    permission_classes = [RequirePermission("psm.indent.approve_dept")]

    @extend_schema(
        operation_id="psm_indents_dept_action",
        request=IndentActionSerializer,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        serializer = IndentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            indent = review_dept_indent(
                indent_id=pk,
                user_id=user_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IndentPSActionView(APIView):
    permission_classes = [RequirePermission("psm.indent.approve_ps")]

    @extend_schema(
        operation_id="psm_indents_ps_action",
        request=IndentActionSerializer,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        serializer = IndentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            indent = review_ps_indent(
                indent_id=pk,
                user_id=user_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IndentDirectorActionView(APIView):
    permission_classes = [RequirePermission("psm.indent.approve_director")]

    @extend_schema(
        operation_id="psm_indents_director_action",
        request=IndentActionSerializer,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        serializer = IndentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            indent = review_director_indent(
                indent_id=pk,
                user_id=user_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class IndentCancelView(APIView):
    permission_classes = [RequirePermission("psm.indent.create")]

    @extend_schema(
        operation_id="psm_indents_cancel",
        request=None,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        try:
            indent = cancel_indent(indent_id=pk, user_id=user_id)
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# -- Vendors -------------------------------------------------------------------
class VendorListView(APIView):
    permission_classes = [RequirePermission("psm.vendor.view", "psm.vendor.manage")]

    @extend_schema(
        operation_id="psm_vendors_list",
        responses={200: VendorSerializer(many=True)},
    )
    def get(self, request):
        vendors = Vendor.objects.all()
        return Response(VendorSerializer(vendors, many=True).data)

    @extend_schema(
        operation_id="psm_vendors_create",
        request=VendorSerializer,
        responses={201: VendorSerializer, 400: dict},
    )
    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            vendor = register_vendor(**serializer.validated_data)
            return Response(VendorSerializer(vendor).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VendorVerifyView(APIView):
    permission_classes = [RequirePermission("psm.vendor.manage")]

    @extend_schema(
        operation_id="psm_vendors_verify",
        request=None,
        responses={200: VendorSerializer},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        vendor = verify_vendor(vendor_id=pk, user_id=user_id)
        return Response(VendorSerializer(vendor).data)


# -- Purchase Orders -----------------------------------------------------------
class PurchaseOrderListView(APIView):
    permission_classes = [RequirePermission("psm.po.view", "psm.po.create")]

    @extend_schema(
        operation_id="psm_purchase_orders_list",
        responses={200: PurchaseOrderSerializer(many=True)},
    )
    def get(self, request):
        qs = scope_purchase_orders(
            request.user,
            PurchaseOrder.objects.all().prefetch_related("lines__item_master"),
        )
        return Response(PurchaseOrderSerializer(qs, many=True).data)

    @extend_schema(
        operation_id="psm_purchase_orders_create",
        request=POCreateSerializer,
        responses={201: PurchaseOrderSerializer, 400: dict},
    )
    def post(self, request):
        serializer = POCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            po = create_purchase_order(
                indent_id=serializer.validated_data["indent_id"],
                vendor_id=serializer.validated_data["vendor_id"],
                delivery_due_date=serializer.validated_data.get("delivery_due_date"),
                user_id=user_id,
            )
            return Response(PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseOrderIssueView(APIView):
    permission_classes = [RequirePermission("psm.po.create")]

    @extend_schema(
        operation_id="psm_purchase_orders_issue",
        request=None,
        responses={200: PurchaseOrderSerializer},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        po = issue_purchase_order(po_id=pk, user_id=user_id)
        return Response(PurchaseOrderSerializer(po).data)


# -- Goods Receipt -------------------------------------------------------------
class GoodsReceiptListView(APIView):
    permission_classes = [RequirePermission("psm.grn.view", "psm.grn.create")]

    @extend_schema(
        operation_id="psm_goods_receipts_list",
        responses={200: GoodsReceiptNoteSerializer(many=True)},
    )
    def get(self, request):
        qs = scope_goods_receipts(
            request.user,
            GoodsReceiptNote.objects.all().prefetch_related(
                "items__po_line_item__item_master"
            ),
        )
        return Response(GoodsReceiptNoteSerializer(qs, many=True).data)

    @extend_schema(
        operation_id="psm_goods_receipts_create",
        request=GRNCreateSerializer,
        responses={201: GoodsReceiptNoteSerializer, 400: dict},
    )
    def post(self, request):
        serializer = GRNCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            grn = create_grn(
                po_id=serializer.validated_data["po_id"],
                user_id=user_id,
                receipt_date=serializer.validated_data["receipt_date"],
                challan_number=serializer.validated_data.get("challan_number", ""),
                invoice_number=serializer.validated_data.get("invoice_number", ""),
                items_data=serializer.validated_data["items"],
            )
            return Response(GoodsReceiptNoteSerializer(grn).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GoodsReceiptAcknowledgeView(APIView):
    permission_classes = [RequirePermission("psm.grn.acknowledge")]

    @extend_schema(
        operation_id="psm_goods_receipts_ack",
        request=None,
        responses={200: GoodsReceiptNoteSerializer, 400: dict},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        try:
            grn = acknowledge_grn(grn_id=pk, user_id=user_id)
            return Response(GoodsReceiptNoteSerializer(grn).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InvoiceMatchView(APIView):
    permission_classes = [RequirePermission("psm.invoice.match")]

    @extend_schema(
        operation_id="psm_invoice_match",
        request=None,
        responses={200: dict},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        grn = get_object_or_404(GoodsReceiptNote.objects.all(), pk=pk)
        invoice_num = request.data.get("invoice_number", grn.invoice_number)
        return Response({
            "status": "matched",
            "grn_number": grn.grn_number,
            "po_number": grn.purchase_order.po_number,
            "invoice_number": invoice_num,
            "matched_by_user_id": user_id,
        })


# -- Inventory -----------------------------------------------------------------
class StockListView(APIView):
    permission_classes = [RequirePermission("psm.stock.view")]

    @extend_schema(
        operation_id="psm_stock_list",
        responses={200: StockItemSerializer(many=True)},
    )
    def get(self, request):
        stocks = StockItem.objects.all().select_related("item_master")
        return Response(StockItemSerializer(stocks, many=True).data)


class StockFulfillView(APIView):
    permission_classes = [RequirePermission("psm.stock.manage")]

    @extend_schema(
        operation_id="psm_stock_fulfill",
        request=StockIssueSerializer,
        responses={200: IndentSerializer, 400: dict},
    )
    def post(self, request):
        serializer = StockIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = get_user_id(request)
        try:
            indent = fulfill_internal_stock(
                indent_id=serializer.validated_data["indent_id"],
                user_id=user_id,
            )
            return Response(IndentSerializer(indent).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# -- Discrepancies -------------------------------------------------------------
class DiscrepancyListView(APIView):
    permission_classes = [RequirePermission("psm.discrepancy.manage")]

    @extend_schema(
        operation_id="psm_discrepancies_list",
        responses={200: DiscrepancyReportSerializer(many=True)},
    )
    def get(self, request):
        reports = DiscrepancyReport.objects.all().select_related("grn")
        return Response(DiscrepancyReportSerializer(reports, many=True).data)


class DiscrepancyResolveView(APIView):
    permission_classes = [RequirePermission("psm.discrepancy.manage")]

    @extend_schema(
        operation_id="psm_discrepancies_resolve",
        request=None,
        responses={200: DiscrepancyReportSerializer},
    )
    def post(self, request, pk: int):
        user_id = get_user_id(request)
        summary = request.data.get("resolution_summary", "Resolved by purchase officer.")
        report = resolve_discrepancy(
            discrepancy_id=pk, user_id=user_id, resolution_summary=summary
        )
        return Response(DiscrepancyReportSerializer(report).data)


# -- Item Masters --------------------------------------------------------------
class ItemMasterListView(APIView):
    permission_classes = [RequirePermission("psm.indent.create", "psm.indent.view")]

    @extend_schema(
        operation_id="psm_items_list",
        responses={200: ItemMasterSerializer(many=True)},
    )
    def get(self, request):
        items = ItemMaster.objects.all()
        return Response(ItemMasterSerializer(items, many=True).data)
