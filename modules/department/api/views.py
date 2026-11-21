from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.department.api.serializers import (
    AnnouncementSerializer,
    DepartmentDetailChangeSerializer,
    DepartmentDetailSerializer,
    DepartmentProfileSerializer,
    DepartmentSerializer,
    FeedbackSerializer,
    InventoryItemSerializer,
    LabResourceSerializer,
    StockRequestSerializer,
    TimetableSerializer,
    TimetableSlotSerializer,
)
from modules.department.models import (
    Announcement,
    Department,
    DepartmentDetail,
    DepartmentDetailChange,
    DepartmentProfile,
    Feedback,
    InventoryItem,
    LabResource,
    StockRequest,
    Timetable,
    TimetableSlot,
)
from modules.department.services import (
    decide_detail_change,
    decide_stock_request,
    insert_stock,
    issue_stock_request,
    resolve_feedback,
    review_feedback,
)


def _actor_id(request):
    p = getattr(request, "principal", None)
    return getattr(p, "user_id", None) or 1


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.detail.update")]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]


class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all().order_by("-created_at")
    serializer_class = AnnouncementSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.announcement.publish"),
    ]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    def perform_create(self, serializer):
        serializer.save(created_by_user_id=_actor_id(self.request))


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("name")
    serializer_class = InventoryItemSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.inventory.manage"),
    ]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    @action(detail=True, methods=["post"], url_path="insert-stock")
    def insert_stock_action(self, request, pk=None):
        item = self.get_object()
        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            return Response({"error": "Quantity must be positive"}, status=status.HTTP_400_BAD_REQUEST)
        updated = insert_stock(
            department_id=item.department_id,
            item_id=item.id,
            quantity=quantity,
            actor_user_id=_actor_id(request),
        )
        return Response(InventoryItemSerializer(updated).data)


class StockRequestViewSet(viewsets.ModelViewSet):
    queryset = StockRequest.objects.all().order_by("-created_at")
    serializer_class = StockRequestSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.stock_request.create"),
    ]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    def perform_create(self, serializer):
        serializer.save(requester_user_id=_actor_id(self.request))

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, pk=None):
        to_status = request.data.get("status")
        if to_status not in ["approved", "rejected"]:
            return Response(
                {"error": "Status must be approved or rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        req = decide_stock_request(
            request_id=pk,
            to_status=to_status,
            actor_user_id=_actor_id(request),
        )
        return Response(StockRequestSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="issue")
    def issue(self, request, pk=None):
        req = issue_stock_request(request_id=pk, actor_user_id=_actor_id(request))
        return Response(StockRequestSerializer(req).data)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all().order_by("-created_at")
    serializer_class = FeedbackSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.feedback.submit")]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    def perform_create(self, serializer):
        serializer.save(submitter_user_id=_actor_id(self.request))

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        category = request.data.get("category", "")
        fb = review_feedback(
            feedback_id=pk,
            category=category,
            reviewer_user_id=_actor_id(request),
        )
        return Response(FeedbackSerializer(fb).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        to_status = request.data.get("status", "resolved")
        fb = resolve_feedback(
            feedback_id=pk,
            to_status=to_status,
            actor_user_id=_actor_id(request),
        )
        return Response(FeedbackSerializer(fb).data)


class DepartmentProfileViewSet(viewsets.ModelViewSet):
    queryset = DepartmentProfile.objects.all().order_by("user_id")
    serializer_class = DepartmentProfileSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.profile.view")]


class TimetableViewSet(viewsets.ModelViewSet):
    queryset = Timetable.objects.all().order_by("-created_at")
    serializer_class = TimetableSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.timetable.manage"),
    ]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    def perform_create(self, serializer):
        serializer.save(uploaded_by_user_id=_actor_id(self.request))


class TimetableSlotViewSet(viewsets.ModelViewSet):
    queryset = TimetableSlot.objects.all().order_by("day", "start_time")
    serializer_class = TimetableSlotSerializer
    permission_classes = [
        HasModuleGrant("department"),
        HasPermission("department.timetable.manage"),
    ]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]


class LabResourceViewSet(viewsets.ModelViewSet):
    queryset = LabResource.objects.all().order_by("name")
    serializer_class = LabResourceSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.resource.view")]

    def perform_create(self, serializer):
        serializer.save(updated_by_user_id=_actor_id(self.request))


class DepartmentDetailViewSet(viewsets.ModelViewSet):
    queryset = DepartmentDetail.objects.all()
    serializer_class = DepartmentDetailSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.detail.update")]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]


class DepartmentDetailChangeViewSet(viewsets.ModelViewSet):
    queryset = DepartmentDetailChange.objects.all().order_by("-created_at")
    serializer_class = DepartmentDetailChangeSerializer
    permission_classes = [HasModuleGrant("department"), HasPermission("department.detail.propose")]

    def get_permissions(self):
        classes = self.permission_classes
        if self.action in ["list", "retrieve"]:
            classes = [HasModuleGrant("department")]
        return [p() for p in classes]

    def perform_create(self, serializer):
        serializer.save(proposed_by_user_id=_actor_id(self.request))

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, pk=None):
        to_status = request.data.get("status")
        ch = decide_detail_change(
            change_id=pk,
            to_status=to_status,
            decided_by_user_id=_actor_id(request),
        )
        return Response(DepartmentDetailChangeSerializer(ch).data)
