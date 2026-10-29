"""DRF views for Employee Leave Management (ELM).

Authorization is fail-closed: HasModuleGrant("elm") gates the module,
selectors scope querysets to what the caller may touch, and service
functions enforce state machine transitions and balance mutations.
"""
from __future__ import annotations

import datetime
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.selectors import leave as selectors
from modules.elm.services import leave_service

MODULE = HasModuleGrant("elm")


def _actor(request):
    return getattr(request, "principal", None)


class LeaveRequestListView(generics.ListCreateAPIView):
    """List leaves visible to this caller, or submit a new leave application."""
    permission_classes = [MODULE]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return s.ApplyLeaveWriteSerializer
        return s.LeaveRequestListSerializer

    def get_queryset(self):
        qs = selectors.visible_leave_requests(_actor(self.request))
        status_param = self.request.query_params.get("status")
        category_param = self.request.query_params.get("category")
        if status_param:
            qs = qs.filter(status=status_param)
        if category_param:
            qs = qs.filter(category=category_param.upper())
        return qs

    def create(self, request, *args, **kwargs):
        payload = s.ApplyLeaveWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.create_leave_request(
            actor=_actor(request),
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            half=data.get("half", "full"),
            purpose=data.get("purpose", ""),
            substitute_id=data.get("substitute_id"),
            station_leave_required=data.get("station_leave_required", False),
            station_leave_address=data.get("station_leave_address", ""),
            submit=data.get("submit", True),
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(APIView):
    """Detail view of a single leave application, or withdrawal by applicant."""
    permission_classes = [MODULE]

    def _get_request(self, pk: int):
        req = selectors.visible_leave_requests(_actor(self.request)).filter(pk=pk).first()
        if not req:
            raise NotFoundError(f"Leave request #{pk} not found.", code="not_found")
        return req

    def get(self, request, pk: int):
        req = self._get_request(pk)
        return Response(s.LeaveRequestSerializer(req).data)

    def delete(self, request, pk: int):
        self._get_request(pk)
        reason = request.data.get("reason", "") if hasattr(request, "data") else ""
        req = leave_service.withdraw_leave(_actor(request), pk, reason=reason)
        return Response(s.LeaveRequestSerializer(req).data)


class LeaveRequestHistoryView(APIView):
    """Audit trail of status changes for a leave application."""
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        req = selectors.visible_leave_requests(_actor(self.request)).filter(pk=pk).first()
        if not req:
            raise NotFoundError(f"Leave request #{pk} not found.", code="not_found")
        transitions = req.transitions.order_by("at")
        return Response(s.LeaveTransitionSerializer(transitions, many=True).data)


class SubstituteRequestsListView(generics.ListAPIView):
    """Leave applications where this user is nominated as substitute."""
    permission_classes = [MODULE, HasPermission("elm.leave.respond_substitute")]
    serializer_class = s.LeaveRequestListSerializer

    def get_queryset(self):
        return selectors.visible_substitute_requests(_actor(self.request))


class SubstituteResponseView(APIView):
    """Accept or decline substitute nomination."""
    permission_classes = [MODULE, HasPermission("elm.leave.respond_substitute")]

    def post(self, request, pk: int):
        payload = s.SubstituteResponseWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.respond_substitute(
            actor=_actor(request),
            request_id=pk,
            accept=data["accept"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class PendingApprovalsListView(generics.ListAPIView):
    """Queue of leave requests awaiting review or sanction."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]
    serializer_class = s.LeaveRequestListSerializer

    def get_queryset(self):
        return selectors.pending_approvals(_actor(self.request))


class UnitHeadReviewView(APIView):
    """Unit Head review: direct sanction for CL/RH, recommendation for other categories."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk: int):
        payload = s.UnitHeadReviewWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.review_unit_head(
            actor=_actor(request),
            request_id=pk,
            action=data["action"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class SanctionDecisionView(APIView):
    """Sanctioning authority final approval or rejection."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk: int):
        payload = s.SanctionDecisionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.sanction_leave(
            actor=_actor(request),
            request_id=pk,
            approve=data["approve"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class CancelRequestView(APIView):
    """Request cancellation of approved leave before start date."""
    permission_classes = [MODULE, HasPermission("elm.leave.cancel")]

    def post(self, request, pk: int):
        payload = s.CancelRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.request_cancellation(
            actor=_actor(request),
            request_id=pk,
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class CancelDecisionView(APIView):
    """Sanctioning authority decides cancellation request."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk: int):
        payload = s.CancelDecisionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.decide_cancellation(
            actor=_actor(request),
            request_id=pk,
            approve=data["approve"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ExtensionRequestView(APIView):
    """Request extension of ongoing leave."""
    permission_classes = [MODULE, HasPermission("elm.leave.modify")]

    def post(self, request, pk: int):
        payload = s.ExtensionRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.request_extension(
            actor=_actor(request),
            request_id=pk,
            new_end_date=data["new_end_date"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ExtensionDecisionView(APIView):
    """Sanctioning authority decides extension request."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk: int):
        payload = s.ExtensionDecisionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.decide_extension(
            actor=_actor(request),
            request_id=pk,
            approve=data["approve"],
            new_end_date=data.get("new_end_date"),
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ResumptionRequestView(APIView):
    """Submit duty resumption report (early return or completion)."""
    permission_classes = [MODULE, HasPermission("elm.leave.modify")]

    def post(self, request, pk: int):
        payload = s.ResumptionRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.submit_resumption(
            actor=_actor(request),
            request_id=pk,
            resumption_date=data["resumption_date"],
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ResumptionReviewView(APIView):
    """Sanctioning authority verifies resumption and refunds unused days."""
    permission_classes = [MODULE, HasPermission("elm.leave.approve")]

    def post(self, request, pk: int):
        payload = s.ResumptionReviewWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.review_resumption(
            actor=_actor(request),
            request_id=pk,
            reason=data.get("reason", ""),
        )
        return Response(s.LeaveRequestSerializer(req).data)


class MyBalancesView(generics.ListAPIView):
    """Caller's leave balances for current year."""
    permission_classes = [MODULE, HasPermission("elm.leave.view_self")]
    serializer_class = s.LeaveBalanceSerializer

    def get_queryset(self):
        year_param = self.request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year
        return selectors.visible_balances(_actor(self.request), year=year)


class UserBalancesView(generics.ListAPIView):
    """Leave balances for an employee (requires elm.leave.view_all or self)."""
    permission_classes = [MODULE]
    serializer_class = s.LeaveBalanceSerializer

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        year_param = self.request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year
        return selectors.visible_balances(_actor(self.request), user_id=user_id, year=year)


class HolidayCalendarListView(generics.ListAPIView):
    """Published holiday calendar."""
    permission_classes = [MODULE]
    serializer_class = s.HolidayCalendarSerializer

    def get_queryset(self):
        year_param = self.request.query_params.get("year")
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year
        return selectors.published_holidays(year=year)


class OfflineLeaveView(APIView):
    """Record leave sanctioned offline (Admin action)."""
    permission_classes = [MODULE, HasPermission("elm.admin.record_offline")]

    def post(self, request):
        payload = s.OfflineLeaveWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        req = leave_service.record_offline_leave(
            actor=_actor(request),
            target_user_id=data["target_user_id"],
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            offline_reference=data["offline_reference"],
            purpose=data.get("purpose", ""),
            half=data.get("half", "full"),
        )
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
