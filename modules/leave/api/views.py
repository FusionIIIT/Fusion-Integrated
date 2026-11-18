"""HTTP layer: parse, scope, delegate, serialise.

Both gates on every view: the module grant, then the permission the action
needs. Querysets come from selectors, so a foreign request is a 404.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    RestrictedHoliday,
)
from modules.leave.selectors import queues
from modules.leave.services import leave as leave_service

MODULE = HasModuleGrant("leave")

P_CREATE = "leave.application.create"
P_VIEW_SELF = "leave.application.view_self"
P_WITHDRAW = "leave.application.withdraw"
P_SUBSTITUTE = "leave.substitute.respond"
P_REVIEW = "leave.request.review"
P_SANCTION = "leave.request.sanction"
P_MANAGE = "leave.policy.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _get(queryset, pk):
    row = queryset.filter(pk=pk).first()
    if row is None:
        raise NotFoundError("Not found.")
    return row


class MyBalancesView(generics.ListAPIView):
    """EL-UC-012. The year defaults to the current leave year."""

    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    pagination_class = None
    queryset = LeaveBalance.objects.none()      # for schema introspection only

    def get_queryset(self):
        from django.utils import timezone
        year = (self.request.query_params.get("year")
                or leave_service.leave_year_for(timezone.localdate()))
        return queues.my_balances(_actor(self.request), year)


class MyLeaveView(generics.ListAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]
    queryset = LeaveApplication.objects.none()      # for schema introspection only

    def get_queryset(self):
        return queues.my_applications(_actor(self.request))


class ApplyView(APIView):
    """EL-UC-001."""

    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ApplyLeaveSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request):
        payload = s.ApplyLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = leave_service.apply_for_leave(_actor(request),
                                                    **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(application).data,
                        status=201)


class WithdrawView(APIView):
    """EL-UC-007."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        application = _get(queues.my_applications(actor), pk)
        updated = leave_service.withdraw(
            actor, application, note=request.data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(updated).data)


class CancellationView(APIView):
    """EL-UC-008: a cancellation request routed like the original leave."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        application = _get(queues.my_applications(actor), pk)
        created = leave_service.request_cancellation(
            actor, application, reason=request.data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(created).data, status=201)


class ResumptionView(APIView):
    """EL-UC-010."""

    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.ResumptionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = _get(queues.my_applications(actor), pk)
        updated = leave_service.submit_resumption(actor, application,
                                                  **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(updated).data)


class NominationListView(generics.ListAPIView):
    """EL-UC-002, the substitute's side."""

    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]
    queryset = LeaveApplication.objects.none()      # for schema introspection only

    def get_queryset(self):
        return queues.nominations_for(_actor(self.request))


class NominationResponseView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(request=s.NominationResponseSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        payload = s.NominationResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = _get(queues.nominations_for(actor), pk)
        updated = leave_service.respond_to_nomination(actor, application,
                                                      **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(updated).data)


class ReviewQueueView(generics.ListAPIView):
    """EL-UC-003, the Unit Head's inbox."""

    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_REVIEW)]
    queryset = LeaveApplication.objects.none()      # for schema introspection only

    def get_queryset(self):
        return queues.review_queue(_actor(self.request))


class ReviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = _get(queues.review_queue(actor), pk)
        updated = leave_service.review(actor, application,
                                       **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(updated).data)


class SanctionQueueView(generics.ListAPIView):
    """EL-UC-004 and EL-UC-005."""

    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_SANCTION)]
    queryset = LeaveApplication.objects.none()      # for schema introspection only

    def get_queryset(self):
        return queues.sanction_queue(_actor(self.request))


class SanctionView(APIView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        actor = _actor(request)
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = _get(queues.sanction_queue(actor), pk)
        updated = leave_service.sanction(actor, application,
                                         **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(updated).data)


class HolidayCalendarView(generics.ListCreateAPIView):
    """The published holiday/RH calendar RH and day-counting read."""

    serializer_class = s.HolidaySerializer
    permission_classes = [MODULE, HasPermission(P_MANAGE, P_VIEW_SELF)]
    pagination_class = None

    def get_queryset(self):
        year = self.request.query_params.get("year")
        rows = RestrictedHoliday.objects.filter(is_published=True)
        if year:
            rows = rows.filter(year=year)
        return rows.order_by("on_date")

    def create(self, request, *args, **kwargs):
        if not _actor(request).has_permission(P_MANAGE):
            raise NotFoundError("Not found.")
        return super().create(request, *args, **kwargs)
