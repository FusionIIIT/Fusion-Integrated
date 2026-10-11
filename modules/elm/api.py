from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.urls import path
from modules.elm.models import LeaveBalance, LeaveApplication, LeaveActionHistory
from modules.elm.services import ensure_balances, apply_leave, review_leave, cancel_leave


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "year", "leave_type", "allocated", "availed", "pending", "available_balance"]


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = ["id", "actor_user_id", "action", "comments", "created_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["id", "user_id", "leave_type", "start_date", "end_date", "days_requested", "reason", "station_leave", "station_address", "status", "remarks", "created_at", "actions"]


def _get_uid(request):
    return getattr(request.user, "user_id", 1)


class BalancesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uid = _get_uid(request)
        ensure_balances(uid)
        return Response(LeaveBalanceSerializer(LeaveBalance.objects.filter(user_id=uid), many=True).data)


class ApplicationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(LeaveApplicationSerializer(LeaveApplication.objects.filter(user_id=_get_uid(request)), many=True).data)

    def post(self, request):
        data = request.data
        try:
            app = apply_leave(
                user_id=_get_uid(request), leave_type=data["leave_type"],
                start_date=serializers.DateField().to_internal_value(data["start_date"]),
                end_date=serializers.DateField().to_internal_value(data["end_date"]),
                reason=data.get("reason", ""), station_leave=data.get("station_leave", False),
                station_address=data.get("station_address", "")
            )
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApprovalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(LeaveApplicationSerializer(LeaveApplication.objects.filter(status__in=["SUBMITTED", "RECOMMENDED"]), many=True).data)


class ActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        action = request.data.get("action")
        try:
            if action == "CANCEL":
                app = cancel_leave(pk, _get_uid(request))
            else:
                app = review_leave(pk, _get_uid(request), action, request.data.get("remarks", ""))
            return Response(LeaveApplicationSerializer(app).data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


urlpatterns = [
    path("balances", BalancesView.as_view()),
    path("applications", ApplicationsView.as_view()),
    path("approvals", ApprovalsView.as_view()),
    path("applications/<int:pk>/action", ActionView.as_view()),
]
