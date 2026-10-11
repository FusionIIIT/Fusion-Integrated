"""DRF API views for Leave module."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    ApplyLeaveSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    TransitionLeaveSerializer,
)
from modules.leave.selectors import leave as selectors
from modules.leave.services import leave as services


class LeaveTypeListView(generics.ListAPIView):
    serializer_class = LeaveTypeSerializer
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create", "leave.request.view_self")]

    def get_queryset(self):
        return selectors.leave_types_active()


class MyBalanceListView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    def get_queryset(self):
        year = int(self.request.query_params.get("year", 2026))
        return selectors.balances_for_user(self.request.principal.user_id, year)


class MyLeaveListView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    def get_queryset(self):
        return selectors.requests_for_user(self.request.principal.user_id)


class PendingLeaveListView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    def get_queryset(self):
        return selectors.pending_requests()


class ApplyLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=ApplyLeaveSerializer, responses={201: LeaveRequestSerializer})
    def post(self, request):
        ser = ApplyLeaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = services.apply_for_leave(
            actor=request.principal,
            leave_type_id=ser.validated_data["leave_type_id"],
            start_date=ser.validated_data["start_date"],
            end_date=ser.validated_data["end_date"],
            half_day=ser.validated_data.get("half_day"),
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class TransitionLeaveView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create", "leave.request.approve", "leave.request.delete")]

    @extend_schema(request=TransitionLeaveSerializer, responses={200: LeaveRequestSerializer})
    def post(self, request, request_id: int):
        ser = TransitionLeaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = services.transition(
            request_id=request_id,
            to_status=ser.validated_data["to_status"],
            actor=request.principal,
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_200_OK)
