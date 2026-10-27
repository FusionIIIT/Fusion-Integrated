from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import selectors
from modules.leave.api.serializers import (
    DecisionSerializer,
    LeaveApplicationSerializer,
    LeaveApplySerializer,
    LeaveBalanceSerializer,
    ReplaceSubstituteSerializer,
    ReportingLineSerializer,
    SubstituteResponseSerializer,
)
from modules.leave.services import admin, applications, lifecycle


class ApplicationListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [HasModuleGrant("leave")(), HasPermission("leave.application.view_own")()]
        if self.request.method == "POST":
            return [HasModuleGrant("leave")(), HasPermission("leave.application.apply")()]
        return super().get_permissions()

    @extend_schema(
        operation_id="v1_leave_applications_list", responses=LeaveApplicationSerializer(many=True)
    )
    def get(self, request, *args, **kwargs):
        user_id = request.principal.user_id
        apps = selectors.my_applications(user_id)
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)

    @extend_schema(request=LeaveApplySerializer, responses={201: LeaveApplicationSerializer})
    def post(self, request, *args, **kwargs):
        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = request.principal.user_id
        app = applications.apply_leave(user_id, request.principal.kind, data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


@extend_schema(responses=LeaveApplicationSerializer)
class ApplicationDetailView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_own")]

    def get(self, request, pk, *args, **kwargs):
        app = selectors.visible_application(request.principal.user_id, pk)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(request=None, responses=LeaveApplicationSerializer)
class WithdrawView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.apply")]

    def post(self, request, pk, *args, **kwargs):
        applications.withdraw(request.principal.user_id, pk)
        app = selectors.visible_application(request.principal.user_id, pk)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(request=None, responses=LeaveApplicationSerializer)
class CancelView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.apply")]

    def post(self, request, pk, *args, **kwargs):
        today = timezone.localdate()
        app = lifecycle.request_cancellation(request.principal.user_id, pk, today)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(request=SubstituteResponseSerializer, responses=LeaveApplicationSerializer)
class SubstituteResponseView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.substitute.respond")]

    def post(self, request, pk, *args, **kwargs):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        accept = data["accept"]
        app = applications.respond_to_substitute(request.principal.user_id, pk, accept)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(request=ReplaceSubstituteSerializer, responses=LeaveApplicationSerializer)
class ReplaceSubstituteView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.apply")]

    def post(self, request, pk, *args, **kwargs):
        serializer = ReplaceSubstituteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        substitute_id = data["substitute_id"]
        app = applications.replace_substitute(request.principal.user_id, pk, substitute_id)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(responses=LeaveApplicationSerializer(many=True))
class InboxView(APIView):
    permission_classes = [
        HasModuleGrant("leave"),
        HasPermission("leave.application.review", "leave.substitute.respond"),
    ]

    def get(self, request, *args, **kwargs):
        user_id = request.principal.user_id
        apps = selectors.inbox(user_id)
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)


@extend_schema(request=DecisionSerializer, responses=LeaveApplicationSerializer)
class DecideView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.review")]

    def post(self, request, pk, *args, **kwargs):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        decision = data["decision"]
        remark = data.get("remark", "")

        app = selectors.visible_application(request.principal.user_id, pk)

        has_verify = request.principal.has_permission("leave.application.verify")
        if app.stage == "establishment" and not has_verify:
            raise NotFoundError("You do not have permission to decide at this stage.")
        has_sanction = request.principal.has_permission("leave.application.sanction")
        if app.stage == "sanction" and not has_sanction:
            raise NotFoundError("You do not have permission to decide at this stage.")

        app = lifecycle.decide(request.principal.user_id, pk, decision, remark)
        serializer = LeaveApplicationSerializer(app)
        return Response(serializer.data)


@extend_schema(
    parameters=[OpenApiParameter("year", int, required=False)],
    responses=LeaveBalanceSerializer(many=True),
)
class BalanceView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_own")]

    def get(self, request, *args, **kwargs):
        user_id = request.principal.user_id
        year = int(request.query_params.get("year", timezone.localdate().year))
        kind = request.principal.kind
        balances = admin.ensure_balances(user_id, kind, year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


@extend_schema(request=ReportingLineSerializer, responses=ReportingLineSerializer)
class ReportingLineView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.admin.manage")]

    def get(self, request, user_id, *args, **kwargs):
        line = selectors.get_reporting_line(user_id)
        if line is None:
            raise NotFoundError()
        serializer = ReportingLineSerializer(line)
        return Response(serializer.data)

    def put(self, request, user_id, *args, **kwargs):
        serializer = ReportingLineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        line = admin.set_reporting_line(
            user_id,
            data["unit_head_id"],
            data.get("establishment_id"),
            data.get("sanctioning_authority_id"),
        )
        serializer = ReportingLineSerializer(line)
        return Response(serializer.data)
