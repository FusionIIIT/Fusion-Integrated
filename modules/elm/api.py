from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.urls import path
from modules.elm.models import LeaveBalance, LeaveApplication, LeaveActionHistory
from modules.elm.services import init_user_quotas, create_leave_request, resolve_leave_request, withdraw_leave_request


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "year", "leave_type", "allocated", "availed", "pending", "remaining"]


class LeaveHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = ["id", "actor_id", "action", "remark", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["id", "user_id", "leave_type", "start_date", "end_date", "days_count", "reason", "station_leave", "station_address", "status", "admin_remark", "created_at", "actions"]


def _get_current_user_id(request):
    return getattr(request.user, "user_id", 1)


class MyBalancesEndpoint(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = _get_current_user_id(request)
        init_user_quotas(uid)
        return Response(LeaveBalanceSerializer(LeaveBalance.objects.filter(user_id=uid), many=True).data)


class MyLeavesEndpoint(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(LeaveRequestSerializer(LeaveApplication.objects.filter(user_id=_get_current_user_id(request)), many=True).data)

    def post(self, request):
        p = request.data
        try:
            req = create_leave_request(
                user_id=_get_current_user_id(request), leave_type=p["leave_type"],
                start_date=serializers.DateField().to_internal_value(p["start_date"]),
                end_date=serializers.DateField().to_internal_value(p["end_date"]),
                reason=p.get("reason", ""), station_leave=p.get("station_leave", False),
                station_address=p.get("station_address", "")
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except Exception as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class PendingApprovalsEndpoint(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(LeaveRequestSerializer(LeaveApplication.objects.filter(status="PENDING"), many=True).data)


class ProcessLeaveEndpoint(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        action = request.data.get("action")
        try:
            if action == "WITHDRAW":
                req = withdraw_leave_request(pk, _get_current_user_id(request))
            else:
                req = resolve_leave_request(pk, _get_current_user_id(request), action, request.data.get("remark", ""))
            return Response(LeaveRequestSerializer(req).data)
        except Exception as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


urlpatterns = [
    path("balances", MyBalancesEndpoint.as_view()),
    path("applications", MyLeavesEndpoint.as_view()),
    path("approvals", PendingApprovalsEndpoint.as_view()),
    path("applications/<int:pk>/action", ProcessLeaveEndpoint.as_view()),
]
