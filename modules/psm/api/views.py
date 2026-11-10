"""
API Views for the PSM Module.
Thin controllers: GET delegates to selectors; POST/PATCH delegates to services.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from core.api.exceptions import NotFoundError, BadRequestError as ValidationError
from modules.psm.models import PurchaseOrder, GoodsReceiptNote

try:
    from fusion_auth.permissions import IsAuthenticatedPrincipal, HasModuleGrant
    _PSM_PERMS = [IsAuthenticatedPrincipal, HasModuleGrant("psm")]
except Exception:
    _PSM_PERMS = [AllowAny]

from modules.psm.selectors.indents import (
    list_indents,
    get_indent_by_id,
    get_indent_version_history,
)
from modules.psm.selectors.vendors import (
    list_vendors,
    get_vendor_by_id,
)
from modules.psm.selectors.stock import (
    list_stock_transfers,
    list_stock_items,
    get_allocable_stock,
)
from modules.psm.services.indents import (
    create_indent,
    modify_indent,
    transition_indent,
    withdraw_indent,
)
from modules.psm.services.procurement import (
    create_vendor,
    verify_vendor,
    create_purchase_order,
    record_grn,
)
from modules.psm.services.stock import (
    initiate_stock_transfer,
)
from .serializers import (
    IndentSerializer,
    IndentVersionSerializer,
    VendorSerializer,
    PurchaseOrderSerializer,
    GoodsReceiptNoteSerializer,
    StockItemSerializer,
    StockTransferSerializer,
)


class IndentListCreateView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        status_param = request.query_params.get("status")
        indents = list_indents(request.principal, status=status_param)
        serializer = IndentSerializer(indents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        indent = create_indent(
            principal=request.principal,
            item_details=data.get("item_details", ""),
            quantity=data.get("quantity", 0),
            estimated_cost=data.get("estimated_cost", 0),
            justification=data.get("justification", ""),
            priority=data.get("priority", "NORMAL"),
            status=data.get("status", "SUBMITTED"),
        )
        serializer = IndentSerializer(indent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IndentDetailView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request, pk):
        indent = get_indent_by_id(request.principal, pk)
        if indent is None:
            raise NotFoundError("Indent not found.")
        serializer = IndentSerializer(indent)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        data = request.data
        indent = modify_indent(
            principal=request.principal,
            indent_id=pk,
            **data,
        )
        serializer = IndentSerializer(indent)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IndentTransitionView(APIView):
    permission_classes = _PSM_PERMS

    def post(self, request, pk):
        data = request.data
        target_state = data.get("target_state")
        justification = data.get("justification", "")
        if not target_state:
            raise ValidationError("Target state is required.")

        indent = transition_indent(
            principal=request.principal,
            indent_id=pk,
            target_state=target_state,
            justification=justification,
        )
        serializer = IndentSerializer(indent)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IndentWithdrawView(APIView):
    permission_classes = _PSM_PERMS

    def post(self, request, pk):
        indent = withdraw_indent(principal=request.principal, indent_id=pk)
        serializer = IndentSerializer(indent)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IndentVersionListView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request, pk):
        versions = get_indent_version_history(request.principal, pk)
        if versions is None:
            raise NotFoundError("Indent not found.")
        serializer = IndentVersionSerializer(versions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VendorListCreateView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        verified_param = request.query_params.get("is_verified")
        is_verified = None
        if verified_param is not None:
            is_verified = verified_param.lower() in ["true", "1", "yes"]

        vendors = list_vendors(request.principal, is_verified=is_verified)
        serializer = VendorSerializer(vendors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        vendor = create_vendor(
            name=data.get("name", ""),
            gst_number=data.get("gst_number", ""),
            bank_account_number=data.get("bank_account_number", ""),
            bank_ifsc=data.get("bank_ifsc", ""),
            compliance_docs_url=data.get("compliance_docs_url", ""),
        )
        serializer = VendorSerializer(vendor)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class VendorDetailView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request, pk):
        vendor = get_vendor_by_id(pk)
        if not vendor:
            raise NotFoundError("Vendor not found.")
        serializer = VendorSerializer(vendor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        # Admin verification toggle
        if request.data.get("is_verified"):
            vendor = verify_vendor(vendor_id=pk)
        else:
            vendor = get_vendor_by_id(pk)
            if not vendor:
                raise NotFoundError("Vendor not found.")
        serializer = VendorSerializer(vendor)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PurchaseOrderListCreateView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        pos = PurchaseOrder.objects.all().order_by("-created_at")
        serializer = PurchaseOrderSerializer(pos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        po = create_purchase_order(
            indent_id=data.get("indent_id"),
            vendor_id=data.get("vendor_id"),
            procurement_method=data.get("procurement_method", "DIRECT"),
            total_cost=data.get("total_cost", 0),
            delivery_schedule=data.get("delivery_schedule"),
        )
        serializer = PurchaseOrderSerializer(po)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GoodsReceiptNoteCreateView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        grns = GoodsReceiptNote.objects.all().order_by("-created_at")
        serializer = GoodsReceiptNoteSerializer(grns, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        grn = record_grn(
            purchase_order_id=data.get("purchase_order_id"),
            accepted_quantity=data.get("accepted_quantity", 0),
            rejected_quantity=data.get("rejected_quantity", 0),
            inspection_remarks=data.get("inspection_remarks", ""),
        )
        serializer = GoodsReceiptNoteSerializer(grn)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StockItemListView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        dept = request.query_params.get("department")
        items = list_stock_items(department=dept)
        serializer = StockItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockTransferListCreateView(APIView):
    permission_classes = _PSM_PERMS

    def get(self, request):
        transfers = list_stock_transfers(request.principal)
        serializer = StockTransferSerializer(transfers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        transfer = initiate_stock_transfer(
            source_dept=data.get("source_department", ""),
            dest_dept=data.get("destination_department", ""),
            stock_item_id=data.get("stock_item_id"),
            quantity=data.get("quantity", 0),
        )
        serializer = StockTransferSerializer(transfer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
