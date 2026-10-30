from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveTypeSerializer,
)
from modules.elm.domain.state_machine import InvalidTransition, initial_state
from modules.elm.models.leave_application import LeaveApplication
from modules.elm.models.leave_types import LeaveBalance, LeaveType
from modules.elm.services.leave_service import LeaveService
from modules.elm.services.workflow_service import WorkflowService


class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view")]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveBalance.objects.none()
        user_id = self.request.principal.user_id
        return LeaveBalance.objects.filter(user_id=user_id)

    serializer_class = LeaveBalanceSerializer
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view")]


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all()
    serializer_class = LeaveApplicationSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        user_id = self.request.principal.user_id
        return LeaveApplication.objects.filter(user_id=user_id)

    def perform_create(self, serializer):
        serializer.save(
            user_id=self.request.principal.user_id,
            status=initial_state(
                substitute_required=bool(serializer.validated_data.get("substitute_id")),
                applicant_is_director="Director" in self.request.principal.roles,
            ),
        )

    def create(self, request, *args, **kwargs):
        data = request.data
        leave_type_code = data.get("leave_type")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        purpose = data.get("purpose")

        validation = LeaveService.validate_application(
            self.request.principal.user_id, leave_type_code, start_date, end_date, purpose
        )

        if not validation["valid"]:
            return Response({"error": validation["reason"]}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [HasModuleGrant("elm")(), HasPermission("elm.leave.view_self")()]
        elif self.action in ["create"]:
            permission_classes = [HasModuleGrant("elm")(), HasPermission("elm.leave.create")()]
        else:
            permission_classes = [HasModuleGrant("elm")()]
        return [permission for permission in permission_classes if permission]


@extend_schema(
    request=inline_serializer(
        name="RecordDecisionRequest",
        fields={
            "application_id": serializers.IntegerField(),
            "action": serializers.ChoiceField(
                choices=["approve", "reject", "recommend", "not_recommend", "route"]
            ),
        },
    ),
    responses=LeaveApplicationSerializer,
)
@api_view(["POST"])
def record_decision(request):

    if not request.principal.has_module("elm") or not request.principal.has_permission(
        "elm.leave.approve"
    ):
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    application_id = request.data.get("application_id")
    action = request.data.get("action")
    decision_maker_id = request.principal.user_id

    application = get_object_or_404(LeaveApplication, id=application_id)

    if application.user_id == decision_maker_id:
        return Response(
            {"error": "Cannot approve your own application."}, status=status.HTTP_403_FORBIDDEN
        )

    try:
        WorkflowService.process_decision(application, action, decision_maker_id)
    except InvalidTransition as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(LeaveApplicationSerializer(application).data)
