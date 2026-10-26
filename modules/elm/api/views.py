"""HTTP layer: parse, delegate to services/selectors, serialise. Mirrors
modules/placement/api/views.py's shape."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    DecisionSerializer,
    LeaveRequestSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.selectors import leave_requests as sel
from modules.elm.services import leave_requests as svc

MODULE = HasModuleGrant("elm")


class MyLeaveRequestsView(APIView):
    """Listing and submitting share a URL but are different capabilities:
    view_self only lets you see your own requests, create is what actually
    lets you submit one. Each method is gated on its own permission."""

    def get_permissions(self):
        code = ("elm.leave_request.create" if self.request.method == "POST"
               else "elm.leave_request.view_self")
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = sel.for_applicant(request.principal.user_id)
        return Response(LeaveRequestSerializer(rows, many=True).data)

    @extend_schema(request=LeaveRequestSerializer, responses=LeaveRequestSerializer)
    def post(self, request):
        s = LeaveRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        row = svc.submit(
            applicant_user_id=request.principal.user_id,
            category=s.validated_data["category"],
            start_date=s.validated_data["start_date"],
            end_date=s.validated_data["end_date"],
            unit_head_user_id=s.validated_data["unit_head_user_id"],
            half_day=s.validated_data.get("half_day", "none"),
            station_leave=s.validated_data.get("station_leave", False),
            station_leave_details=s.validated_data.get("station_leave_details", ""),
            reason=s.validated_data.get("reason", ""),
            substitute_user_id=s.validated_data.get("substitute_user_id"),
        )
        return Response(LeaveRequestSerializer(row).data, status=201)


class ApprovalsQueueView(APIView):
    permission_classes = [MODULE, HasPermission("elm.leave_request.view")]

    @extend_schema(responses=LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = sel.for_unit_head(request.principal.user_id)
        return Response(LeaveRequestSerializer(rows, many=True).data)


class LeaveRequestDecideView(APIView):
    permission_classes = [MODULE, HasPermission("elm.leave_request.decide")]

    @extend_schema(request=DecisionSerializer, responses=LeaveRequestSerializer)
    def post(self, request, pk):
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        row = svc.decide_as_unit_head(
            acting_user_id=request.principal.user_id,
            leave_request_id=pk,
            approve=s.validated_data["approve"],
            remarks=s.validated_data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(row).data)


@extend_schema(request=None, responses=LeaveRequestSerializer)
class LeaveRequestWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("elm.leave_request.withdraw")]

    def post(self, request, pk):
        row = svc.withdraw(acting_user_id=request.principal.user_id,
                           leave_request_id=pk)
        return Response(LeaveRequestSerializer(row).data)


@extend_schema(request=None, responses=LeaveRequestSerializer)
class LeaveRequestCancelView(APIView):
    permission_classes = [MODULE, HasPermission("elm.leave_request.cancel")]

    def post(self, request, pk):
        row = svc.cancel(acting_user_id=request.principal.user_id,
                         leave_request_id=pk)
        return Response(LeaveRequestSerializer(row).data)


class SubstituteResponseView(APIView):
    """Any authenticated principal may respond if they are the nominated
    substitute — gated in the service layer (service checks
    substitute_user_id == acting user), not by a leave-request permission,
    since the substitute need not hold any ELM permission at all."""
    permission_classes = [MODULE]

    @extend_schema(request=SubstituteResponseSerializer, responses=LeaveRequestSerializer)
    def post(self, request, pk):
        s = SubstituteResponseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        row = svc.substitute_respond(
            acting_user_id=request.principal.user_id,
            leave_request_id=pk,
            accept=s.validated_data["accept"],
        )
        return Response(LeaveRequestSerializer(row).data)
