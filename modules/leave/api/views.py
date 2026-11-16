"""Views for Leave Management endpoints."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import AuthenticationFailedError, BadRequestError, NotFoundError
from modules.leave.api import permissions as p
from modules.leave.api import serializers as s
from modules.leave.models import LeaveRequest
from modules.leave.selectors import leaves as selectors
from modules.leave.services import balances as balance_service
from modules.leave.services import cancellation as cancellation_service
from modules.leave.services import decisions as decision_service
from modules.leave.services import submission as submission_service


def _user_id(request) -> int:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None):
        return int(principal.user_id)
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False) and getattr(user, "id", None):
        return int(user.id)
    raise AuthenticationFailedError("Authentication required.")


class LeaveRequestListCreateView(APIView):
    permission_classes = [p.MODULE, p.MayViewSelf]

    @extend_schema(responses={200: s.LeaveRequestSerializer(many=True)})
    def get(self, request):
        """List leave requests with optional status/type filtering and scope support."""
        uid = _user_id(request)
        principal = getattr(request, "principal", None)
        can_view_all = principal and principal.has_permission(p.P_VIEW)

        target_user = uid
        if can_view_all and request.query_params.get("user_id"):
            try:
                target_user = int(request.query_params["user_id"])
            except ValueError:
                raise BadRequestError("Invalid user_id parameter.")

        if can_view_all and request.query_params.get("all") == "true":
            qs = LeaveRequest.objects.all().prefetch_related("decisions")
        else:
            qs = selectors.get_requests_for_user(target_user)

        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        type_param = request.query_params.get("leave_type")
        if type_param:
            qs = qs.filter(leave_type=type_param)

        return Response(s.LeaveRequestSerializer(qs, many=True).data)

    @extend_schema(
        request=s.SubmitLeaveRequestInputSerializer,
        responses={201: s.LeaveRequestSerializer},
    )
    def post(self, request):
        """Submit a new leave request (HR-UC-003 / BW-HR-01 Entry)."""
        serializer = s.SubmitLeaveRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        uid = _user_id(request)
        req = submission_service.submit_leave_request(
            user_id=uid,
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            duration_days=data["duration_days"],
            justification=data["justification"],
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveBalanceListView(APIView):
    permission_classes = [p.MODULE, p.MayViewSelf]

    @extend_schema(responses={200: s.LeaveBalanceSerializer(many=True)})
    def get(self, request):
        """Retrieve current leave balances for the authenticated user."""
        uid = _user_id(request)
        principal = getattr(request, "principal", None)
        can_manage_balances = principal and principal.has_permission(p.P_BALANCE_UPDATE)

        target_user = uid
        if can_manage_balances and request.query_params.get("user_id"):
            try:
                target_user = int(request.query_params["user_id"])
            except ValueError:
                raise BadRequestError("Invalid user_id parameter.")

        balance_service.ensure_balances_for_user(target_user)
        qs = selectors.get_balances_for_user(target_user)
        return Response(s.LeaveBalanceSerializer(qs, many=True).data)


class PendingApprovalsListView(APIView):
    permission_classes = [p.MODULE, p.MayApproveRequest]

    @extend_schema(responses={200: s.LeaveRequestSerializer(many=True)})
    def get(self, request):
        """List leave requests pending review by the current authority."""
        uid = _user_id(request)
        qs = selectors.get_pending_requests_for_authority(uid)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)


class LeaveRequestDetailView(APIView):
    permission_classes = [p.MODULE, p.MayViewSelf]

    @extend_schema(responses={200: s.LeaveRequestSerializer})
    def get(self, request, pk: int):
        """Retrieve details of a specific leave request."""
        req = selectors.get_request_by_id(pk)
        if not req:
            raise NotFoundError("Leave request not found.")

        uid = _user_id(request)
        # Authorize: applicant or current authority or broad view permission
        if req.user_id != uid and req.current_authority_id != uid:
            principal = getattr(request, "principal", None)
            if not principal or not principal.has_permission(p.P_VIEW):
                raise NotFoundError("Leave request not found.")

        return Response(s.LeaveRequestSerializer(req).data)


class DecideLeaveRequestView(APIView):
    permission_classes = [p.MODULE, p.MayApproveRequest]

    @extend_schema(
        request=s.DecideLeaveRequestInputSerializer,
        responses={200: s.ApprovalDecisionSerializer},
    )
    def post(self, request, pk: int):
        """Record an approval, rejection, or forward decision (HR-UC-004 / BW-HR-01 / BW-HR-03)."""
        serializer = s.DecideLeaveRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        uid = _user_id(request)
        decision = decision_service.decide_leave_request(
            request_id=pk,
            authority_user_id=uid,
            outcome=data["outcome"],
            remarks=data.get("remarks", ""),
            next_authority_id=data.get("next_authority_id"),
        )
        return Response(s.ApprovalDecisionSerializer(decision).data, status=status.HTTP_200_OK)


class CancelLeaveRequestView(APIView):
    permission_classes = [p.MODULE, p.MayCancelRequest]

    @extend_schema(
        request=s.CancelLeaveRequestInputSerializer,
        responses={200: s.LeaveRequestSerializer},
    )
    def post(self, request, pk: int):
        """Cancel an in-flight pending leave request by applicant (HR-UC-003)."""
        serializer = s.CancelLeaveRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        uid = _user_id(request)
        req = cancellation_service.cancel_leave_request(
            request_id=pk,
            user_id=uid,
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_200_OK)
