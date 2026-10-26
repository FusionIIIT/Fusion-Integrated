from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from fusion_auth.permissions import HasPermission
from modules.elm import services
from modules.elm.api.serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveApplicationSerializer,
    ApplyInputSerializer,
    DecisionInputSerializer,
)

class LeaveTypeListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveTypeSerializer(many=True))
    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).order_by("name")
        serializer = LeaveTypeSerializer(types, many=True)
        return Response(serializer.data)


class MyApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = LeaveApplication.objects.filter(employee_id=request.user.user_id).order_by("-created_at")
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @extend_schema(request=ApplyInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = services.apply(request.user, serializer.validated_data["leave_type"], serializer.validated_data["start_date"], serializer.validated_data["end_date"], serializer.validated_data["reason"])
        return Response(LeaveApplicationSerializer(application).data, status=201)


class PendingApprovalsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.approve")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = LeaveApplication.objects.filter(status="SUBMITTED").exclude(employee_id=request.user.user_id).order_by("created_at")
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)


class DecideView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.approve")]

    @extend_schema(request=DecisionInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = services.decide(request.user, pk, serializer.validated_data["approve"], serializer.validated_data.get("remarks", ""))
        return Response(LeaveApplicationSerializer(application).data)


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.apply")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = services.withdraw(request.user, pk)
        return Response(LeaveApplicationSerializer(application).data)


class CancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.apply")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = services.cancel_approved(request.user, pk)
        return Response(LeaveApplicationSerializer(application).data)


class MyBalanceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        year = request.query_params.get("year")
        if year is None:
            year = timezone.localtime().year
        try:
            year = int(year)
        except (TypeError, ValueError):
            raise BadRequestError("year must be a number.", code="invalid_filter")
        balances = LeaveBalance.objects.filter(employee_id=request.user.user_id, year=year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)
