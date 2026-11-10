from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from fusion_auth.permissions import HasPermission
from modules.phc.models import InventoryItem, Requisition
from modules.phc.api.serializers import InventoryItemSerializer, RequisitionSerializer, DecisionSerializer
from modules.phc.services.inventory import adjust_stock, create_requisition, decide_requisition, fulfill_requisition

class InventoryListView(APIView):
    permission_classes = [HasPermission("phc.inventory.view")]

    @extend_schema(
        responses={200: InventoryItemSerializer(many=True)}
    )
    def get(self, request):
        qs = InventoryItem.objects.all().order_by("-name")
        serializer = InventoryItemSerializer(qs, many=True)
        return Response(serializer.data)

class InventoryCreateView(APIView):
    permission_classes = [HasPermission("phc.inventory.create")]

    @extend_schema(
        request=InventoryItemSerializer,
        responses={201: InventoryItemSerializer}
    )
    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inventory_item = serializer.save()
        return Response(serializer.data, status=201)

class InventoryAdjustView(APIView):
    permission_classes = [HasPermission("phc.inventory.update")]

    @extend_schema(
        request={"application/json": DecisionSerializer},
        responses={200: InventoryItemSerializer}
    )
    def post(self, request, pk):
        inventory_item = InventoryItem.objects.get(id=pk)
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        adjust_stock(inventory_item, serializer.validated_data["delta"], serializer.validated_data["reason"], request.user.user_id)
        return Response({"message": "Stock adjusted successfully"})

class RequisitionListView(APIView):
    permission_classes = [HasPermission("phc.requisition.create")]

    @extend_schema(
        request=RequisitionSerializer,
        responses={201: RequisitionSerializer}
    )
    def post(self, request):
        serializer = RequisitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requisition = create_requisition(serializer.validated_data["lines"], request.user.user_id)
        return Response(serializer.to_representation(requisition), status=201)

class RequisitionDetailView(APIView):
    permission_classes = [HasPermission("phc.requisition.view")]

    @extend_schema(
        responses={200: RequisitionSerializer}
    )
    def get(self, request, pk):
        requisition = Requisition.objects.get(id=pk)
        serializer = RequisitionSerializer(requisition)
        return Response(serializer.data)

class RequisitionDecideView(APIView):
    permission_classes = [HasPermission("phc.requisition.approve")]

    @extend_schema(
        request=DecisionSerializer,
        responses={200: RequisitionSerializer}
    )
    def post(self, request, pk):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        decide_requisition(pk, decision, request.user.user_id)
        return Response({"message": f"Requisition {pk} decided as {decision}"})

class RequisitionFulfillView(APIView):
    permission_classes = [HasPermission("phc.requisition.update")]

    @extend_schema(
        responses={200: RequisitionSerializer}
    )
    def post(self, request, pk):
        fulfill_requisition(pk, request.user.user_id)
        return Response({"message": f"Requisition {pk} fulfilled"})
