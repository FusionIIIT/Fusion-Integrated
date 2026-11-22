# Stock catalog, availability, adjustments, internal issues, and inter-departmental transfers.
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.psm.api import serializers as ser
from modules.psm.selectors import scoping
from modules.psm.selectors import stock as stock_sel
from modules.psm.services import stock, transfers


def _parse_optional_int(raw: str | None, name: str) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise BadRequestError(
            f"Query parameter '{name}' must be an integer.", code="invalid_query_param"
        ) from exc


class StockItemListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.stock.view" if self.request.method == "GET" else "psm.stock.update"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List active stock catalog items",
        responses={200: ser.StockItemSerializer(many=True)},
    )
    def get(self, request):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(scoping.active_stock_items(), request)
        return paginator.get_paginated_response(ser.StockItemSerializer(page, many=True).data)

    @extend_schema(
        tags=["psm"],
        summary="Create a stock catalog item",
        request=ser.StockItemSerializer,
        responses={201: ser.StockItemSerializer},
        examples=[
            OpenApiExample(
                "Stock item",
                value={
                    "sku": "NET-SW24",
                    "name": "24-Port Switch",
                    "category": "Networking",
                    "unit": "unit",
                },
            )
        ],
    )
    def post(self, request):
        s = ser.StockItemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = stock.create_stock_item(actor=request.principal, **s.validated_data)
        return Response(ser.StockItemSerializer(obj).data, status=status.HTTP_201_CREATED)


class StockLocationListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.stock.view" if self.request.method == "GET" else "psm.stock.update"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List visible departmental and central stock locations",
        responses={200: ser.StockLocationSerializer(many=True)},
    )
    def get(self, request):
        rows = scoping.stock_locations_for(request.principal)
        return Response({"results": ser.StockLocationSerializer(rows, many=True).data})

    @extend_schema(
        tags=["psm"],
        summary="Create a stock location",
        request=ser.StockLocationSerializer,
        responses={201: ser.StockLocationSerializer},
    )
    def post(self, request):
        s = ser.StockLocationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = stock.create_stock_location(actor=request.principal, **s.validated_data)
        return Response(ser.StockLocationSerializer(obj).data, status=status.HTTP_201_CREATED)


class StockAvailabilityView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.view")]

    @extend_schema(
        tags=["psm"],
        summary="Check departmental and central stock availability (PSM-UC-007, PSM-UC-017)",
        responses={200: ser.StockAvailabilitySerializer(many=True)},
    )
    def get(self, request):
        item_id = _parse_optional_int(request.query_params.get("item_id"), "item_id")
        location_id = _parse_optional_int(request.query_params.get("location_id"), "location_id")
        rows = stock_sel.availability_rows(
            request.principal, item_id=item_id, location_id=location_id
        )
        return Response({"results": ser.StockAvailabilitySerializer(rows, many=True).data})


class StockAdjustmentCreateView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Record an authorized stock ledger adjustment (PSM-UC-008)",
        request=ser.StockAdjustmentCreateSerializer,
        responses={201: ser.StockLedgerEntrySerializer},
    )
    def post(self, request):
        s = ser.StockAdjustmentCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        entry = stock.record_adjustment(actor=request.principal, **s.validated_data)
        return Response(ser.StockLedgerEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class InternalIssueListView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.view")]

    @extend_schema(
        tags=["psm"],
        summary="List scoped internal stock issues (PSM-UC-009)",
        responses={200: ser.InternalIssueSerializer(many=True)},
    )
    def get(self, request):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(scoping.internal_issues_for(request.principal), request)
        return paginator.get_paginated_response(ser.InternalIssueSerializer(page, many=True).data)


class InternalIssuePickView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Schedule picking for an approved internal issue (PSM-UC-009)",
        request=ser.SchedulePickingSerializer,
        responses={200: ser.InternalIssueSerializer},
    )
    def post(self, request, issue_id: int):
        s = ser.SchedulePickingSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = stock.schedule_picking(actor=request.principal, issue_id=issue_id, **s.validated_data)
        return Response(ser.InternalIssueSerializer(obj).data)


class InternalIssueDispatchView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.stock.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Dispatch an approved internal stock issue (PSM-UC-009)",
        request=None,
        responses={200: ser.InternalIssueSerializer},
    )
    def post(self, request, issue_id: int):
        obj = stock.dispatch_internal_issue(actor=request.principal, issue_id=issue_id)
        return Response(ser.InternalIssueSerializer(obj).data)


class StockTransferListCreateView(APIView):
    def get_permissions(self):
        perm = "psm.transfer.view" if self.request.method == "GET" else "psm.transfer.create"
        return [HasModuleGrant("psm")(), HasPermission(perm)()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "psm_write"
        return super().get_throttles()

    @extend_schema(
        tags=["psm"],
        summary="List scoped inter-departmental stock transfers (BW-PSM-08)",
        responses={200: ser.StockTransferReadSerializer(many=True)},
    )
    def get(self, request):
        paginator = CursorPagination()
        page = paginator.paginate_queryset(scoping.transfers_for(request.principal), request)
        return paginator.get_paginated_response(
            ser.StockTransferReadSerializer(page, many=True).data
        )

    @extend_schema(
        tags=["psm"],
        summary="Request an inter-departmental stock transfer (PSM-UC-021)",
        request=ser.StockTransferCreateSerializer,
        responses={201: ser.StockTransferReadSerializer},
    )
    def post(self, request):
        s = ser.StockTransferCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        obj = transfers.request_transfer(actor=request.principal, **s.validated_data)
        return Response(ser.StockTransferReadSerializer(obj).data, status=status.HTTP_201_CREATED)


class StockTransferDispatchView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.transfer.update")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Reserve and dispatch a stock transfer (PSM-UC-033)",
        request=None,
        responses={200: ser.StockTransferReadSerializer},
    )
    def post(self, request, transfer_id: int):
        obj = transfers.dispatch_transfer(actor=request.principal, transfer_id=transfer_id)
        return Response(ser.StockTransferReadSerializer(obj).data)


class StockTransferConfirmView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.transfer.approve")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Confirm transfer receipt and post dual ledgers (PSM-UC-034)",
        request=None,
        responses={200: ser.StockTransferReadSerializer},
    )
    def post(self, request, transfer_id: int):
        obj = transfers.confirm_transfer(actor=request.principal, transfer_id=transfer_id)
        return Response(ser.StockTransferReadSerializer(obj).data)


class StockTransferCancelView(APIView):
    permission_classes = [HasModuleGrant("psm"), HasPermission("psm.transfer.delete")]
    throttle_scope = "psm_write"

    @extend_schema(
        tags=["psm"],
        summary="Cancel a pending stock transfer request",
        request=None,
        responses={200: ser.StockTransferReadSerializer},
    )
    def post(self, request, transfer_id: int):
        obj = transfers.cancel_transfer(actor=request.principal, transfer_id=transfer_id)
        return Response(ser.StockTransferReadSerializer(obj).data)
