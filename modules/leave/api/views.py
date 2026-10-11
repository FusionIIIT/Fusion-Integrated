from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType
from modules.leave.selectors.requests import visible_requests
from modules.leave.services import requests as service

MODULE = HasModuleGrant("leave")


class _OwnedRequest(BasePermission):
    def has_object_permission(self, request, view, obj):
        actor = request.principal
        return obj.user_id == actor.user_id and actor.has_permission("leave.request.cancel")


class MyLeaveView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.view_self")]

    @extend_schema(responses=dict)
    def get(self, request):
        uid = request.principal.user_id
        balances = LeaveBalance.objects.filter(user_id=uid).select_related("leave_type")
        rows = LeaveRequest.objects.filter(user_id=uid).select_related("leave_type")
        return Response({"balances": s.LeaveBalanceSerializer(balances, many=True).data,
                         "requests": s.LeaveRequestSerializer(rows, many=True).data,
                         "leave_types": s.LeaveTypeSerializer(
                             LeaveType.objects.filter(is_active=True), many=True).data})


class RequestCreateView(generics.CreateAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.LeaveRequestSerializer, responses=s.LeaveRequestSerializer)
    def create(self, request, *args, **kwargs):
        payload = s.LeaveRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = service.create_request(user_id=request.principal.user_id,
                                     leave_type_id=data["leave_type"].pk,
                                     start_date=data["start_date"], end_date=data["end_date"],
                                     reason=data["reason"])
        return Response(s.LeaveRequestSerializer(row).data, status=201)


class RequestListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission("leave.request.view", "leave.request.review")]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveRequest.objects.none()
        return visible_requests(self.request.principal)

    @extend_schema(responses=s.LeaveRequestSerializer(many=True))
    def list(self, request, *args, **kwargs):
        rows = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(s.LeaveRequestSerializer(page, many=True).data)
        return Response({"results": s.LeaveRequestSerializer(rows, many=True).data})


class RequestReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.review")]

    @extend_schema(request=s.ReviewSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = get_object_or_404(visible_requests(request.principal), pk=pk)
        row = service.review_request(leave_request=row, actor_id=request.principal.user_id,
                                     **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data)


class RequestCancelView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.cancel"), _OwnedRequest]

    @extend_schema(request=None, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        row = get_object_or_404(LeaveRequest, pk=pk, user_id=request.principal.user_id)
        self.check_object_permissions(request, row)
        if row.status != "pending":
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": "Only pending requests can be cancelled."})
        row.status = "cancelled"
        row.save(update_fields=["status", "updated_at"])
        return Response(s.LeaveRequestSerializer(row).data)
