from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.department import permissions as p
from modules.department import selectors, services
from modules.department.api.common import CheckedFields, DepartmentAccess
from modules.department.models import Feedback, Notice, StockItem, StockRequest


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StockItem
        fields = ("id", "name", "quantity")


class StockInsertionSerializer(CheckedFields, serializers.Serializer):
    name = serializers.CharField(max_length=160)
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


@method_decorator(never_cache, name="dispatch")
class InventoryView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_STOCK
    write_permission = p.INSERT_STOCK
    queryset = StockItem.objects.none()
    serializer_class = InventorySerializer

    def get_queryset(self):
        return selectors.stock_items_for(self.request.principal)

    @extend_schema(request=StockInsertionSerializer, responses={201: InventorySerializer})
    def post(self, request):
        payload = StockInsertionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = services.insert_stock(actor=request.principal, **payload.validated_data)
        return Response(InventorySerializer(item).data, status=status.HTTP_201_CREATED)


class StockRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name")
    status = serializers.CharField(read_only=True)

    class Meta:
        model = StockRequest
        fields = ("id", "item_name", "quantity", "status", "created_at")


class StockRequestWriteSerializer(CheckedFields, serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1, max_value=9_223_372_036_854_775_807)
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


@method_decorator(never_cache, name="dispatch")
class StockRequestsView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_STOCK_REQUEST
    write_permission = p.REQUEST_STOCK
    queryset = StockRequest.objects.none()
    serializer_class = StockRequestSerializer

    def get_queryset(self):
        return selectors.stock_requests_for(self.request.principal)

    @extend_schema(request=StockRequestWriteSerializer, responses={201: StockRequestSerializer})
    def post(self, request):
        payload = StockRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.request_stock(actor=request.principal, **payload.validated_data)
        return Response(StockRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class StockActionSerializer(CheckedFields, serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "issue"])


class StockRequestActionView(DepartmentAccess, APIView):
    write_permission = (p.REVIEW_STOCK, p.ISSUE_STOCK)

    @extend_schema(request=StockActionSerializer, responses=StockRequestSerializer)
    def post(self, request, pk):
        payload = StockActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.advance_stock_request(actor=request.principal, request_id=pk,
                                             **payload.validated_data)
        return Response(StockRequestSerializer(row).data)


class FeedbackSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Feedback
        fields = ("id", "content", "category", "status", "created_at", "reviewed_at", "disposed_at")


class FeedbackSubmissionSerializer(CheckedFields, serializers.Serializer):
    content = serializers.CharField(max_length=8000)


class FeedbackReceiptSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Feedback
        fields = ("id", "status")


@method_decorator(never_cache, name="dispatch")
class FeedbackView(DepartmentAccess, generics.ListCreateAPIView):
    read_permission = p.VIEW_FEEDBACK
    write_permission = p.SUBMIT_FEEDBACK
    queryset = Feedback.objects.none()
    serializer_class = FeedbackSerializer

    def get_queryset(self):
        return selectors.feedback_for(self.request.principal)

    @extend_schema(request=FeedbackSubmissionSerializer, responses={201: FeedbackReceiptSerializer})
    def post(self, request):
        payload = FeedbackSubmissionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.submit_feedback(actor=request.principal, **payload.validated_data)
        return Response(FeedbackReceiptSerializer(row).data, status=status.HTTP_201_CREATED)


class FeedbackActionSerializer(CheckedFields, serializers.Serializer):
    action = serializers.ChoiceField(choices=["review", "close", "resolve"])
    category = serializers.CharField(max_length=100, required=False)
    close_simple = serializers.BooleanField(default=False)


class FeedbackActionView(DepartmentAccess, APIView):
    write_permission = (p.REVIEW_FEEDBACK, p.DISPOSE_FEEDBACK)

    @extend_schema(request=FeedbackActionSerializer, responses=FeedbackSerializer)
    def post(self, request, pk):
        payload = FeedbackActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.advance_feedback(actor=request.principal, feedback_id=pk,
                                        **payload.validated_data)
        return Response(FeedbackSerializer(row).data)


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = ("id", "message", "created_at")


@method_decorator(never_cache, name="dispatch")
class NoticesView(DepartmentAccess, generics.ListAPIView):
    read_permission = p.VIEW_NOTICE
    queryset = Notice.objects.none()
    serializer_class = NoticeSerializer

    def get_queryset(self):
        return selectors.notices_for(self.request.principal)
