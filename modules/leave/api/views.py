"""API views for Employee Leave Management."""
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    LeaveActionResponseSerializer,
    LeaveHealthResponseSerializer,
)


class LeaveHealthView(APIView):
    """Health and status endpoint for Employee Leave Management."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.view_self")]

    @extend_schema(responses={200: LeaveHealthResponseSerializer})
    def get(self, request):
        return Response({"status": "active", "module": "leave"})


class LeaveApplicationStubView(APIView):
    """Stub view declaring leave creation and withdrawal permissions."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.create")]

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def post(self, request):
        return Response({"status": "stub_created"})

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def delete(self, request, pk=None):
        if not request.principal.has_permission("leave.request.delete"):
            return Response({"error": "forbidden"}, status=403)
        return Response({"status": "stub_withdrawn"})


class LeaveApprovalsStubView(APIView):
    """Stub view declaring leave approval permissions."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.request.approve")]

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def post(self, request):
        return Response({"status": "stub_decided"})


class LeaveAdminStubView(APIView):
    """Stub view declaring administrative balance update and policy management permissions."""

    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.update")]

    @extend_schema(request=None, responses={200: LeaveActionResponseSerializer})
    def post(self, request):
        if not request.principal.has_permission("leave.type.manage"):
            return Response({"error": "forbidden"}, status=403)
        return Response({"status": "stub_updated"})
