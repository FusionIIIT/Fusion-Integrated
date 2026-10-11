from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission
from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    ReviewLeaveInputSerializer,
    SubmitLeaveInputSerializer,
)
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType
from modules.elm.services.leave_service import (
    cancel_approved_leave,
    review_leave_request,
    submit_leave_request,
    withdraw_leave_request,
)


class LeaveTypeListAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveTypeSerializer(many=True))
    def get(self, request):
        leave_types = LeaveType.objects.filter(is_active=True)
        return Response(LeaveTypeSerializer(leave_types, many=True).data)


class MyLeaveBalanceAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        balances = LeaveBalance.objects.filter(
            employee_id=request.user.user_id
        ).select_related("leave_type")
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class MyLeaveRequestListCreateAPIView(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [HasPermission("leave_elm.application.apply")()]
        return [HasPermission("leave_elm.application.view")()]

    @extend_schema(responses=LeaveRequestSerializer(many=True))
    def get(self, request):
        requests = LeaveRequest.objects.filter(
            employee_id=request.user.user_id
        ).select_related("leave_type")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    @extend_schema(request=SubmitLeaveInputSerializer, responses=LeaveRequestSerializer)
    def post(self, request):
        serializer = SubmitLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        leave_req = submit_leave_request(
            employee_id=request.user.user_id,
            leave_type_id=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            is_half_day=data["is_half_day"],
            reason=data["reason"],
            contact_address=data["contact_address"],
            substitute_employee_id=data["substitute_employee_id"],
        )
        return Response(LeaveRequestSerializer(leave_req).data, status=201)


class PendingApprovalsAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.application.approve")]

    @extend_schema(responses=LeaveRequestSerializer(many=True))
    def get(self, request):
        pending = (
            LeaveRequest.objects.filter(status="PENDING")
            .exclude(employee_id=request.user.user_id)
            .select_related("leave_type")
        )
        return Response(LeaveRequestSerializer(pending, many=True).data)


class ReviewLeaveRequestAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.application.approve")]

    @extend_schema(request=ReviewLeaveInputSerializer, responses=LeaveRequestSerializer)
    def post(self, request, pk: int):
        serializer = ReviewLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_req = review_leave_request(
            reviewer_id=request.user.user_id,
            request_id=pk,
            decision=serializer.validated_data["decision"],
            review_comment=serializer.validated_data.get("review_comment", ""),
        )
        return Response(LeaveRequestSerializer(leave_req).data)


class WithdrawLeaveRequestAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.application.apply")]

    @extend_schema(request=None, responses=LeaveRequestSerializer)
    def post(self, request, pk: int):
        leave_req = withdraw_leave_request(employee_id=request.user.user_id, request_id=pk)
        return Response(LeaveRequestSerializer(leave_req).data)


class CancelLeaveRequestAPIView(APIView):
    permission_classes = [HasPermission("leave_elm.application.apply")]

    @extend_schema(request=None, responses=LeaveRequestSerializer)
    def post(self, request, pk: int):
        leave_req = cancel_approved_leave(employee_id=request.user.user_id, request_id=pk)
        return Response(LeaveRequestSerializer(leave_req).data)
