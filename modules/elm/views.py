"""HTTP views for Employee Leave Management."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.selectors import (
    get_approval_queue,
    get_holidays,
    get_substitute_requests,
    get_user_applications,
    get_user_balances,
)
from modules.elm.serializers import (
    ApplyLeaveInputSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    ReviewLeaveInputSerializer,
    SubstituteRequestSerializer,
    SubstituteResponseInputSerializer,
)
from modules.elm.services import (
    apply_leave,
    cancel_leave,
    respond_to_substitute_request,
    review_leave,
)

MODULE_GRANT = HasModuleGrant("elm")


class LeaveBalancesView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        user_id = request.principal.user_id
        balances = get_user_balances(user_id)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class MyLeavesView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        user_id = request.principal.user_id
        apps = get_user_applications(user_id)
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=ApplyLeaveInputSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def post(self, request):
        if not request.principal.has_permission("elm.leave.create"):
            return Response(
                {"detail": "You do not have permission to apply for leave."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ApplyLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            application = apply_leave(
                user_id=request.principal.user_id,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                station_leave=data.get("station_leave", False),
                substitute_user_id=data.get("substitute_user_id"),
            )
        except ValidationError as e:
            raise DRFValidationError(e.message if hasattr(e, "message") else str(e)) from e

        output_serializer = LeaveApplicationSerializer(application)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class CancelLeaveView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.cancel")]

    @extend_schema(request=None, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        try:
            application = cancel_leave(
                application_id=pk,
                user_id=request.principal.user_id,
            )
        except ValidationError as e:
            raise DRFValidationError(e.message if hasattr(e, "message") else str(e)) from e
        return Response(LeaveApplicationSerializer(application).data)


class ApprovalQueueView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.review")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        queue = get_approval_queue()
        serializer = LeaveApplicationSerializer(queue, many=True)
        return Response(serializer.data)


class ReviewLeaveView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.review")]

    @extend_schema(
        request=ReviewLeaveInputSerializer,
        responses=LeaveApplicationSerializer,
    )
    def post(self, request, pk: int):
        serializer = ReviewLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            application = review_leave(
                application_id=pk,
                reviewer_user_id=request.principal.user_id,
                action=data["action"],
                remarks=data.get("remarks", ""),
            )
        except ValidationError as e:
            raise DRFValidationError(e.message if hasattr(e, "message") else str(e)) from e

        return Response(LeaveApplicationSerializer(application).data)


class HolidayCalendarView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.holiday.view")]

    @extend_schema(responses=HolidayCalendarSerializer(many=True))
    def get(self, request):
        holidays = get_holidays()
        serializer = HolidayCalendarSerializer(holidays, many=True)
        return Response(serializer.data)


class SubstituteRequestsView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    @extend_schema(responses=SubstituteRequestSerializer(many=True))
    def get(self, request):
        requests = get_substitute_requests(request.principal.user_id)
        serializer = SubstituteRequestSerializer(requests, many=True)
        return Response(serializer.data)


class RespondSubstituteView(APIView):
    permission_classes = [MODULE_GRANT, HasPermission("elm.leave.view_self")]

    @extend_schema(
        request=SubstituteResponseInputSerializer,
        responses=SubstituteRequestSerializer,
    )
    def post(self, request, pk: int):
        serializer = SubstituteResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sub_req = respond_to_substitute_request(
                substitute_request_id=pk,
                substitute_user_id=request.principal.user_id,
                accept=serializer.validated_data["accept"],
            )
        except ValidationError as e:
            raise DRFValidationError(e.message if hasattr(e, "message") else str(e)) from e
        return Response(SubstituteRequestSerializer(sub_req).data)
