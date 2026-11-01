from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, ListCreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.inventory_stock_serializers import (
    DeptInventoryItemSerializer,
    DeptInventoryWriteSerializer,
    DeptStockDecisionSerializer,
    DeptStockMovementSerializer,
    DeptStockRequestSerializer,
    DeptStockRequestWriteSerializer,
)
from modules.department.models import InventoryItem, StockMovement, StockRequest
from modules.department.selectors.stock import (
    issued_history,
    visible_inventory,
    visible_movements,
    visible_requests,
)
from modules.department.services import stock as stock_service


@extend_schema(
    summary="List and create department inventory stock items",
    responses={
        200: DeptInventoryItemSerializer,
        201: DeptInventoryItemSerializer,
        400: None,
        403: None,
    },
    tags=["Inventory Stock"],
)
class InventoryListView(ListCreateAPIView):
    """Lists and creates department inventory stock items."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeptInventoryWriteSerializer
        return DeptInventoryItemSerializer

    queryset = InventoryItem.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.inventory.view"),
    ]

    def get_queryset(self) -> QuerySet[InventoryItem]:
        """Returns the queryset of visible inventory items."""
        if getattr(self, "swagger_fake_view", False):
            return InventoryItem.objects.none()
        return visible_inventory(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new department inventory stock item."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        department_id = data['department']

        item = stock_service.insert_stock(
            actor=request.principal,
            department_id=department_id,
            name=data['name'],
            unit=data['unit'],
            quantity=data['quantity'],
        )
        return Response(DeptInventoryItemSerializer(item).data, status=201)


@extend_schema(
    summary="List and create stock requests",
    responses={
        200: DeptStockRequestSerializer,
        201: DeptStockRequestSerializer,
        400: None,
        403: None,
    },
    tags=["Stock Request"],
)
class StockRequestListView(ListCreateAPIView):
    """Lists and creates stock requests."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DeptStockRequestWriteSerializer
        return DeptStockRequestSerializer

    queryset = StockRequest.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_request.view"),
    ]

    def get_queryset(self) -> QuerySet[StockRequest]:
        """Returns the queryset of visible stock requests."""
        if getattr(self, "swagger_fake_view", False):
            return StockRequest.objects.none()
        return visible_requests(self.request.principal)

    def create(self, request, *args, **kwargs):
        """Creates a new stock request."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        item_id = data['item']
        quantity = data['quantity']

        request = stock_service.request_stock(
            actor=request.principal,
            item_id=item_id,
            quantity=quantity,
        )
        return Response(DeptStockRequestSerializer(request).data, status=201)


@extend_schema(
    summary="Decide on a stock request",
    responses={
        200: DeptStockRequestSerializer,
        404: None,
        403: None,
    },
    tags=["Stock Request"],
)
class StockRequestDecideView(APIView):
    """Approves or rejects a stock request."""
    serializer_class = DeptStockDecisionSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_request.approve"),
    ]

    def post(self, request, pk):
        """Decides on the stock request."""
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        outcome = serializer.validated_data['outcome']
        if outcome == 'approved':
            event = 'approve'
        elif outcome == 'rejected':
            event = 'reject'
        else:
            raise ValueError("Invalid outcome")

        request = stock_service.decide_request(
            actor=request.principal,
            request_id=pk,
            outcome=event,
        )
        return Response(DeptStockRequestSerializer(request).data)


@extend_schema(
    summary="Issue stock against a request",
    responses={
        200: DeptStockRequestSerializer,
        404: None,
        403: None,
    },
    tags=["Stock Request"],
)
class StockRequestIssueView(APIView):
    """Issues stock against an approved request."""
    serializer_class = DeptStockRequestSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_request.update"),
    ]

    def post(self, request, pk):
        """Issues stock for the request."""
        request = stock_service.issue_stock(
            actor=request.principal,
            request_id=pk,
        )
        return Response(DeptStockRequestSerializer(request).data)


@extend_schema(
    summary="View issued stock history for the principal",
    responses={
        200: DeptStockRequestSerializer,
        403: None,
    },
    tags=["Stock Request"],
)
class StockHistoryView(ListAPIView):
    """Views the issued stock history of the principal."""
    serializer_class = DeptStockRequestSerializer
    queryset = StockRequest.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_request.view"),
    ]

    def get_queryset(self) -> QuerySet[StockRequest]:
        """Returns the issued stock history for the principal."""
        if getattr(self, "swagger_fake_view", False):
            return StockRequest.objects.none()
        return issued_history(self.request.principal)


@extend_schema(
    summary="View visible stock movements for the principal",
    responses={
        200: DeptStockMovementSerializer,
        403: None,
    },
    tags=["Stock Movement"],
)
class StockMovementListView(ListAPIView):
    """Views visible stock movements for the principal."""
    serializer_class = DeptStockMovementSerializer
    queryset = StockMovement.objects.none()
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_movement.view"),
    ]

    def get_queryset(self) -> QuerySet[StockMovement]:
        """Returns the visible stock movements for the principal."""
        if getattr(self, "swagger_fake_view", False):
            return StockMovement.objects.none()
        return visible_movements(self.request.principal)
