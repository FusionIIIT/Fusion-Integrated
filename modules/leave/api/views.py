from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.models import (
    LeaveBalance,
    LeaveManagerAssignment,
    LeaveRequest,
    LeaveType,
)
from modules.leave.selectors.requests import visible_requests
from modules.leave.services import configuration
from modules.leave.services import requests as service

MODULE = HasModuleGrant("leave")
CONFIGURATION = HasPermission("leave.configuration.manage")


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
        visible = list(page if page is not None else rows)
        people = directory.get_users([row.user_id for row in visible])
        context = {"employee_names": {
            user_id: person.display_name for user_id, person in people.items()
        }}
        data = s.LeaveRequestSerializer(visible, many=True, context=context).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response({"results": data})


class RequestReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.review")]

    @extend_schema(request=s.ReviewSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = get_object_or_404(visible_requests(request.principal), pk=pk)
        row = service.review_request(leave_request=row, actor_id=request.principal.user_id,
                                     scope=visible_requests(request.principal),
                                     **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data)


class RequestCancelView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.cancel")]

    @extend_schema(request=None, responses=s.LeaveRequestSerializer)
    def post(self, request, pk):
        row = service.cancel_request(leave_request_id=pk,
                                     user_id=request.principal.user_id)
        return Response(s.LeaveRequestSerializer(row).data)


class LeaveTypeConfigurationView(generics.ListCreateAPIView):
    permission_classes = [MODULE, CONFIGURATION]
    serializer_class = s.LeaveTypeConfigurationSerializer
    queryset = LeaveType.objects.all()

    def perform_create(self, serializer):
        row = configuration.save_leave_type(values=serializer.validated_data)
        serializer.instance = row


class LeaveTypeConfigurationDetailView(generics.UpdateAPIView):
    permission_classes = [MODULE, CONFIGURATION]
    serializer_class = s.LeaveTypeConfigurationSerializer
    queryset = LeaveType.objects.all()
    http_method_names = ["patch", "put", "head", "options"]

    def perform_update(self, serializer):
        row = configuration.save_leave_type(
            leave_type_id=serializer.instance.pk,
            values=serializer.validated_data)
        if row is None:
            raise NotFound("No such leave type.")
        serializer.instance = row


class LeaveBalanceConfigurationView(APIView):
    permission_classes = [MODULE, CONFIGURATION]

    @extend_schema(responses=s.LeaveBalanceConfigurationSerializer(many=True))
    def get(self, request):
        rows = LeaveBalance.objects.select_related("leave_type").all()
        return Response(s.LeaveBalanceConfigurationSerializer(rows, many=True).data)

    @extend_schema(request=s.LeaveBalanceConfigurationSerializer,
                    responses=s.LeaveBalanceConfigurationSerializer)
    def put(self, request):
        payload = s.LeaveBalanceConfigurationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = configuration.set_balance(values=payload.validated_data)
        return Response(s.LeaveBalanceConfigurationSerializer(row).data)


class LeaveManagerAssignmentConfigurationView(APIView):
    permission_classes = [MODULE, CONFIGURATION]

    @extend_schema(responses=s.LeaveManagerAssignmentSerializer(many=True))
    def get(self, request):
        rows = LeaveManagerAssignment.objects.all()
        return Response(s.LeaveManagerAssignmentSerializer(rows, many=True).data)

    @extend_schema(request=s.LeaveManagerAssignmentSerializer,
                    responses=s.LeaveManagerAssignmentSerializer)
    def post(self, request):
        payload = s.LeaveManagerAssignmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row, created = configuration.assign_manager(
            manager_user_id=payload.validated_data["manager_user_id"],
            employee_user_id=payload.validated_data["employee_user_id"],
            assigned_by_user_id=request.principal.user_id)
        return Response(s.LeaveManagerAssignmentSerializer(row).data,
                        status=201 if created else 200)


class LeaveManagerAssignmentDeleteView(APIView):
    permission_classes = [MODULE, CONFIGURATION]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk):
        row = get_object_or_404(LeaveManagerAssignment, pk=pk)
        row.delete()
        return Response(status=204)
