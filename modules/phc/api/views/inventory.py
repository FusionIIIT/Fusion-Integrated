from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiParameter
from fusion_auth.permissions import HasPermission

from modules.phc.models import InventoryItem, Requisition
from modules.phc.api.serializers import (
    InventoryItemSerializer,
    StockAdjustmentSerializer,
    RequisitionSerializer,
    RequisitionCreateSerializer,
    RequisitionDecisionSerializer,
)
from modules.phc.services.inventory import (
    adjust_stock,
    create_requisition,
    decide_requisition,
    fulfil_requisition,
)

class InventoryListView(APIView):
    permission_classes = [HasPermission("phc.inventory.view")]

    @extend_schema(responses={200: InventoryItemSerializer(many=True)})
    def get(self, request):
        items = InventoryItem.objects.all()
        return Response(InventoryItemSerializer(items, many=True).data)

class InventoryAdjustView(APIView):
    permission_classes = [HasPermission("phc.inventory.update")]

    @extend_schema(
        parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)],
        request=StockAdjustmentSerializer,
        responses={200: InventoryItemSerializer}
    )
    def post(self, request, pk):
        try:
            item = InventoryItem.objects.get(pk=pk)
        except InventoryItem.DoesNotExist:
            raise NotFound("Inventory item not found.")
        
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_item = adjust_stock(
            item_id=pk,
            delta=serializer.validated_data["delta"],
            reason=serializer.validated_data["reason"],
            actor_user_id=request.user.user_id,
        )
        return Response(InventoryItemSerializer(updated_item).data)

class RequisitionListCreateView(APIView):
    permission_classes = [HasPermission("phc.requisition.create")]

    @extend_schema(responses={200: RequisitionSerializer(many=True)})
    def get(self, request):
        reqs = Requisition.objects.filter(requested_by_user_id=request.user.user_id)
        return Response(RequisitionSerializer(reqs, many=True).data)

    @extend_schema(request=RequisitionCreateSerializer, responses={201: RequisitionSerializer})
    def post(self, request):
        serializer = RequisitionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        req = create_requisition(
            requested_by_user_id=request.user.user_id,
            lines=serializer.validated_data["lines"]
        )
        return Response(RequisitionSerializer(req).data, status=status.HTTP_201_CREATED)

class RequisitionDecideView(APIView):
    permission_classes = [HasPermission("phc.requisition.approve")]

    @extend_schema(
        parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)],
        request=RequisitionDecisionSerializer,
        responses={200: RequisitionSerializer}
    )
    def post(self, request, pk):
        serializer = RequisitionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        req = decide_requisition(
            req_id=pk,
            decision=serializer.validated_data["decision"],
            actor_user_id=request.user.user_id,
        )
        return Response(RequisitionSerializer(req).data)

class RequisitionFulfillView(APIView):
    permission_classes = [HasPermission("phc.requisition.update")]

    @extend_schema(
        parameters=[OpenApiParameter("pk", int, OpenApiParameter.PATH)],
        responses={200: RequisitionSerializer}
    )
    def post(self, request, pk):
        req = fulfil_requisition(
            req_id=pk,
            actor_user_id=request.user.user_id,
        )
        return Response(RequisitionSerializer(req).data)
