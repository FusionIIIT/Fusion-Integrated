from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.elm.api.serializers import (
    AllotInputSerializer,
    ApplyInputSerializer,
    DecisionInputSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveTypeCreateInputSerializer,
    LeaveTypeSerializer,
)
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType
from modules.elm.services.leave import apply, cancel_approved, decide, withdraw
from modules.elm.services.policy import allot_balance, create_leave_type


class LeaveTypeListView(APIView):
    permission_classes = [HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveTypeSerializer(many=True))
    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).order_by("name")
        serializer = LeaveTypeSerializer(types, many=True)
        return Response(serializer.data)


class MyApplicationsView(APIView):
    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = LeaveApplication.objects.filter(
            employee_id=request.user.user_id
        ).order_by("-created_at")
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @extend_schema(request=ApplyInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        application = apply(
            request.user, data["leave_type"], data["start_date"], data["end_date"], data["reason"]
        )
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data, status=201)

    def get_permissions(self):
        action = "apply" if self.request.method == "POST" else "view"
        return [HasPermission("leave_elm.application." + action)()]


class PendingApprovalsView(APIView):
    permission_classes = [HasPermission("leave_elm.application.approve")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = (
            LeaveApplication.objects.filter(status="SUBMITTED")
            .exclude(employee_id=request.user.user_id)
            .order_by("created_at")
        )
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class DecideView(APIView):
    permission_classes = [HasPermission("leave_elm.application.approve")]

    @extend_schema(request=DecisionInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        application = decide(request.user, pk, data["approve"], data.get("remarks", ""))
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class WithdrawView(APIView):
    permission_classes = [HasPermission("leave_elm.application.apply")]

    @extend_schema(request=None, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = withdraw(request.user, pk)
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class CancelView(APIView):
    permission_classes = [HasPermission("leave_elm.application.apply")]

    @extend_schema(request=None, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = cancel_approved(request.user, pk)
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class MyBalanceView(APIView):
    permission_classes = [HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        year = request.query_params.get("year")
        if year is None:
            year = timezone.localtime().year
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("year must be a number.", code="invalid_filter") from exc
        balances = (
            LeaveBalance.objects.filter(employee_id=request.user.user_id, year=year)
            .select_related("leave_type")
            .order_by("leave_type__name")
        )
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class AdminLeaveTypeView(APIView):
    permission_classes = [HasPermission("leave_elm.policy.manage")]

    @extend_schema(request=LeaveTypeCreateInputSerializer, responses=LeaveTypeSerializer)
    def post(self, request):
        serializer = LeaveTypeCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_type = create_leave_type(request.user, **serializer.validated_data)
        serializer = LeaveTypeSerializer(leave_type)
        return Response(serializer.data, status=201)


class AdminAllotBalanceView(APIView):
    permission_classes = [HasPermission("leave_elm.policy.manage")]

    @extend_schema(request=AllotInputSerializer, responses=LeaveBalanceSerializer)
    def post(self, request):
        serializer = AllotInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        balance = allot_balance(request.user, **serializer.validated_data)
        serializer = LeaveBalanceSerializer(balance)
        return Response(serializer.data)
