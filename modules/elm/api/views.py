from rest_framework import status, views, permissions
from rest_framework.response import Response
from modules.elm.models import LeaveRequest
from modules.elm.services.leave_service import LeaveService
from modules.elm.selectors.leave_selectors import (
    get_user_leaves, get_user_balances, get_pending_substitute_requests, get_pending_unit_head_approvals
)
from .serializers import (
    LeaveRequestSerializer, LeaveBalanceSerializer, LeaveCreateSerializer,
    SubstituteDecisionSerializer, ApproverDecisionSerializer
)


class LeaveListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.username)
        leaves = get_user_leaves(user_id)
        serializer = LeaveRequestSerializer(leaves, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id = str(request.user.username)
        serializer = LeaveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            leave = LeaveService.apply_leave(
                applicant_id=user_id,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                duration_days=data["duration_days"],
                reason=data["reason"],
                is_half_day=data.get("is_half_day", False),
                half_day_session=data.get("half_day_session", ""),
                station_leave=data.get("station_leave", False),
                station_leave_address=data.get("station_leave_address", ""),
                out_of_station_from=data.get("out_of_station_from"),
                out_of_station_to=data.get("out_of_station_to"),
                substitute_id=data.get("substitute_id", ""),
            )
            return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)
        except (ValueError, PermissionError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveBalanceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.username)
        balances = get_user_balances(user_id)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class SubstituteQueueView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = str(request.user.username)
        requests = get_pending_substitute_requests(user_id)
        return Response(LeaveRequestSerializer(requests, many=True).data)


class SubstituteDecisionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user_id = str(request.user.username)
        serializer = SubstituteDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            leave = LeaveService.respond_substitute(
                leave_id=pk,
                substitute_id=user_id,
                accept=serializer.validated_data["accept"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(leave).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApprovalsQueueView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        leaves = get_pending_unit_head_approvals()
        return Response(LeaveRequestSerializer(leaves, many=True).data)


class ApproverDecisionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user_id = str(request.user.username)
        serializer = ApproverDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            leave = LeaveService.review_unit_head(
                leave_id=pk,
                approver_id=user_id,
                approve=serializer.validated_data["approve"],
                remarks=serializer.validated_data.get("remarks", ""),
                forward_higher=serializer.validated_data.get("forward_higher", False),
            )
            return Response(LeaveRequestSerializer(leave).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveWithdrawView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user_id = str(request.user.username)
        reason = request.data.get("reason", "")
        try:
            leave = LeaveService.withdraw_leave(leave_id=pk, user_id=user_id, reason=reason)
            return Response(LeaveRequestSerializer(leave).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
