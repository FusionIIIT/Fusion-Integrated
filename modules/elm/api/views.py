from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
)
from modules.elm.models import LeaveApplication, LeaveBalance


class LeaveBalanceListView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.balance.view"),
    ]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        rows = LeaveBalance.objects.filter(employee_id=request.user.user_id)
        return Response(LeaveBalanceSerializer(rows, many=True).data)


class LeaveApplicationListCreateView(APIView):
    permission_classes = [
        HasModuleGrant("elm"),
        HasPermission("elm.application.create"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        rows = LeaveApplication.objects.filter(applicant_id=request.user.user_id)
        return Response(LeaveApplicationSerializer(rows, many=True).data)

    @extend_schema(
        request=LeaveApplicationSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def post(self, request):
        serializer = LeaveApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(applicant_id=request.user.user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
