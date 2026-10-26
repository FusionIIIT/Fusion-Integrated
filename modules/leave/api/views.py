"""HTTP API endpoints for Employee Leave Management (ELM)."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.selectors import scoping
from modules.leave.services import applications as app_service

MODULE = HasModuleGrant("leave")

P_VIEW = "leave.application.view"
P_CREATE = "leave.application.create"
P_REVIEW = "leave.application.review"
P_APPROVE = "leave.application.approve"
P_DELETE = "leave.application.delete"
P_SUBSTITUTE = "leave.substitute.respond"
P_BALANCE = "leave.balance.view"


def _actor(request):
    return getattr(request, "principal", None)


class LeaveApplicationListCreateView(APIView):
    """List applications in scope, or submit a new leave application (EL-UC-001)."""

    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        qs = scoping.applications_for(actor)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if scoping.is_approver(actor):
            user_id = request.query_params.get("user_id")
            if user_id:
                try:
                    qs = qs.filter(user_id=int(user_id))
                except ValueError as exc:
                    raise BadRequestError(
                        "user_id must be an integer.",
                        code="invalid_filter",
                    ) from exc
        return Response(s.LeaveApplicationSerializer(qs.order_by("-created_at"), many=True).data)

    @extend_schema(
        request=s.LeaveApplicationCreateSerializer,
        responses=s.LeaveApplicationSerializer,
    )
    def post(self, request):
        actor = _actor(request)
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.apply_leave(
            actor=actor,
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveApplicationDetailView(APIView):
    """Retrieve details of a single leave application."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer)
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.applications_for(actor)
        try:
            app = qs.get(pk=pk)
        except qs.model.DoesNotExist as exc:
            raise NotFoundError(f"Leave application #{pk} not found.") from exc
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveApplicationHistoryView(APIView):
    """Retrieve audit history for a leave application."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationAuditSerializer(many=True))
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.applications_for(actor)
        try:
            app = qs.get(pk=pk)
        except qs.model.DoesNotExist as exc:
            raise NotFoundError(f"Leave application #{pk} not found.") from exc
        audits = app.audits.order_by("at")
        return Response(s.LeaveApplicationAuditSerializer(audits, many=True).data)


class SubstituteResponseView(APIView):
    """Substitute accepts or declines responsibility (EL-UC-002)."""

    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk: int):
        actor = _actor(request)
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.respond_substitute(
            actor=actor,
            application_id=pk,
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class ReviewApplicationView(APIView):
    """Review and recommend or reject a leave application (EL-UC-003)."""

    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.ReviewActionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk: int):
        actor = _actor(request)
        payload = s.ReviewActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.review_application(
            actor=actor,
            application_id=pk,
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class SanctionApplicationView(APIView):
    """Sanction or reject a leave application (EL-UC-004)."""

    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(request=s.SanctionActionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk: int):
        actor = _actor(request)
        payload = s.SanctionActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.sanction_application(
            actor=actor,
            application_id=pk,
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class WithdrawApplicationView(APIView):
    """Withdraw an application (EL-UC-005)."""

    permission_classes = [MODULE, HasPermission(P_DELETE)]

    @extend_schema(request=s.WithdrawActionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk: int):
        actor = _actor(request)
        payload = s.WithdrawActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = app_service.withdraw_application(
            actor=actor,
            application_id=pk,
            **payload.validated_data,
        )
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveBalanceListView(APIView):
    """View leave balances (EL-UC-006)."""

    permission_classes = [MODULE, HasPermission(P_BALANCE, P_VIEW)]

    @extend_schema(responses=s.LeaveBalanceSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        qs = scoping.balances_for(actor)
        year = request.query_params.get("year")
        if year:
            try:
                qs = qs.filter(year=int(year))
            except ValueError as exc:
                raise BadRequestError("year must be an integer.", code="invalid_filter") from exc
        return Response(s.LeaveBalanceSerializer(qs.order_by("-year"), many=True).data)
