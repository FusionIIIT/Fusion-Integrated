from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from fusion_auth.permissions import HasPermission
from modules.elm.models import LeaveType, LeaveApplication, LeaveBalance
from modules.elm.services.leave import apply, decide, withdraw, cancel_approved
from modules.elm.api.serializers import LeaveTypeSerializer, LeaveApplicationSerializer, ApplyInputSerializer, DecisionInputSerializer, LeaveBalanceSerializer
from django.utils import timezone
from core.api.exceptions import BadRequestError


class LeaveTypeListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveTypeSerializer(many=True))
    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).order_by("name")
        serializer = LeaveTypeSerializer(types, many=True)
        return Response(serializer.data)


class MyApplicationsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = LeaveApplication.objects.filter(employee_id=request.user.user_id).order_by("-created_at")
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @extend_schema(request=ApplyInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = apply(request.user, serializer.validated_data["leave_type"], serializer.validated_data["start_date"], serializer.validated_data["end_date"], serializer.validated_data["reason"])
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data, status=201)


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
        application = decide(request.user, pk, serializer.validated_data["approve"], serializer.validated_data.get("remarks", ""))
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.withdraw")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = withdraw(request.user, pk)
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class CancelView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.cancel")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        application = cancel_approved(request.user, pk)
        serializer = LeaveApplicationSerializer(application)
        return Response(serializer.data)


class MyBalanceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        year = request.query_params.get("year")
        if year is None:
            year = timezone.localtime().year
        try:
            year = int(year)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("year must be a number.", code="invalid_filter") from exc
        balances = LeaveBalance.objects.filter(employee_id=request.user.user_id, year=year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)
