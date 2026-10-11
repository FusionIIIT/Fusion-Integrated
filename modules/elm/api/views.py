"""HTTP layer: parse, scope, delegate, serialise.

Every list starts from `selectors.scoping`, so a row outside the caller's scope
is simply absent — which is why detail views 404 rather than 403.
"""
from __future__ import annotations

from datetime import date

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.models import Holiday, LeaveType
from modules.elm.selectors import queries, scoping
from modules.elm.services import applications as application_service
from modules.elm.services import balances as balance_service
from modules.elm.services import policy_admin

MODULE = HasModuleGrant("elm")

P_APPLY = "elm.application.create"
P_VIEW = "elm.application.view"
P_APPROVE = "elm.application.approve"
P_DELETE = "elm.application.delete"
P_BALANCE_VIEW = "elm.balance.view"
P_BALANCE_MANAGE = "elm.balance.manage"
P_POLICY_MANAGE = "elm.policy.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name: str) -> int | None:
    """A non-integer filter is a 400, not a ValueError deep in the ORM."""
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc


def _date_param(params, name: str) -> date | None:
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise BadRequestError(f"{name} must be a date like 2026-04-01.",
                              code="invalid_filter") from exc


def _people(rows) -> dict:
    """One batched directory call for a page of rows, never one per row."""
    ids = sorted({row.user_id for row in rows})
    return directory.get_users(ids) if ids else {}


class _PeopleMixin(generics.GenericAPIView):
    """Adds applicant names to a page without an N+1 lookup."""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = list(page if page is not None else queryset)
        context = self.get_serializer_context()
        context["actor"] = _actor(request)
        context["people"] = _people(rows)
        data = self.get_serializer(rows, many=True, context=context).data
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)


# -- Leave types ---------------------------------------------------------------
@extend_schema(responses=s.LeaveTypeSerializer(many=True))
class LeaveTypeListView(generics.ListAPIView):
    """Every leave type effective today — what the apply form can offer."""

    serializer_class = s.LeaveTypeSerializer
    permission_classes = [MODULE, HasPermission(P_APPLY, P_VIEW)]
    pagination_class = None                     # five rows, not a collection

    def get_queryset(self):
        # Schema generation happens with no database; the effective-date
        # lookup needs one, so it is skipped for the fake view.
        if getattr(self, "swagger_fake_view", False):
            return LeaveType.objects.none()
        return queries.types_effective_on(timezone.localdate())


@extend_schema(request=s.LeaveTypeWriteSerializer,
               responses=s.LeaveTypeSerializer,
               examples=[OpenApiExample(
                   "A new casual-leave version",
                   request_only=True,
                   value={"code": "CL", "name": "Casual Leave",
                          "annual_entitlement_days": "8.0",
                          "allows_half_day": True,
                          "effective_from": "2026-04-01"})])
class LeaveTypeCreateView(APIView):
    """A changed entitlement is a new version, never an edit."""

    permission_classes = [MODULE, HasPermission(P_POLICY_MANAGE)]

    def post(self, request):
        payload = s.LeaveTypeWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave_type = policy_admin.create_leave_type(
            actor=_actor(request), **payload.validated_data)
        return Response(s.LeaveTypeSerializer(leave_type).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.LeaveTypeSerializer)
class LeaveTypeStatusView(APIView):
    """Retire or restore one version of a type."""

    permission_classes = [MODULE, HasPermission(P_POLICY_MANAGE)]

    def post(self, request, pk: int, action: str):
        if action not in ("activate", "deactivate"):
            raise BadRequestError("Action must be 'activate' or 'deactivate'.",
                                  code="unknown_action")
        leave_type = policy_admin.set_leave_type_active(
            actor=_actor(request), leave_type_id=pk, is_active=action == "activate")
        return Response(s.LeaveTypeSerializer(leave_type).data)


# -- Holidays ------------------------------------------------------------------
@extend_schema(responses=s.HolidaySerializer(many=True))
class HolidayListView(generics.ListAPIView):
    serializer_class = s.HolidaySerializer
    permission_classes = [MODULE, HasPermission(P_APPLY, P_VIEW)]
    pagination_class = None

    def get_queryset(self):
        params = self.request.query_params
        start, end = _date_param(params, "from"), _date_param(params, "to")
        qs = Holiday.objects.order_by("date")
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs


@extend_schema(request=s.HolidayWriteSerializer, responses=s.HolidaySerializer)
class HolidayCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY_MANAGE)]

    def post(self, request):
        payload = s.HolidayWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        holiday = policy_admin.create_holiday(actor=_actor(request),
                                              **payload.validated_data)
        return Response(s.HolidaySerializer(holiday).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses={204: None})
class HolidayDeleteView(APIView):
    permission_classes = [MODULE, HasPermission(P_POLICY_MANAGE)]

    def delete(self, request, pk: int):
        policy_admin.delete_holiday(actor=_actor(request), holiday_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


# -- Applications --------------------------------------------------------------
@extend_schema(responses=s.LeaveApplicationSerializer(many=True))
class ApplicationListView(_PeopleMixin, generics.ListAPIView):
    """Own requests for an applicant; everything for an approver."""

    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW, P_APPLY)]

    def get_queryset(self):
        params = self.request.query_params
        qs = scoping.applications_for(_actor(self.request))
        status_filter = params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        leave_type_id = _int_param(params, "leave_type")
        if leave_type_id is not None:
            qs = qs.filter(leave_type_id=leave_type_id)
        start, end = _date_param(params, "from"), _date_param(params, "to")
        if start:
            qs = qs.filter(end_date__gte=start)
        if end:
            qs = qs.filter(start_date__lte=end)
        return qs.order_by("-start_date", "-id")


@extend_schema(request=s.LeaveApplicationCreateSerializer,
               responses=s.LeaveApplicationSerializer,
               examples=[OpenApiExample(
                   "Two days of casual leave",
                   request_only=True,
                   value={"leave_type_id": 1, "start_date": "2026-04-20",
                          "end_date": "2026-04-21",
                          "reason": "Family function"})])
class ApplicationSubmitView(APIView):
    """Submits a request; the rules refuse before any row exists."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]
    throttle_scope = "apply"

    def post(self, request):
        payload = s.LeaveApplicationCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = application_service.submit_application(
            actor=_actor(request), **payload.validated_data)
        return Response(
            s.LeaveApplicationSerializer(application, context={
                "actor": _actor(request),
                "people": _people([application])}).data,
            status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LeaveApplicationSerializer)
class ApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW, P_APPLY)]

    def get_queryset(self):
        return scoping.applications_for(_actor(self.request))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["actor"] = _actor(self.request)
        application = self.get_object()
        context["people"] = _people([application])
        return context


@extend_schema(request=s.LeaveTransitionSerializer,
               responses=s.LeaveApplicationSerializer)
class ApplicationTransitionView(APIView):
    """The single write path: decide, withdraw or cancel."""

    permission_classes = [MODULE, HasPermission(P_APPROVE, P_DELETE)]

    def post(self, request, pk: int):
        payload = s.LeaveTransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        application = application_service.transition(
            actor=_actor(request), application_id=pk, **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(application, context={
            "actor": _actor(request),
            "people": _people([application])}).data)


@extend_schema(responses=s.LeaveEventSerializer(many=True))
class ApplicationHistoryView(APIView):
    """The append-only trail, for "why is my request at this status?"."""

    permission_classes = [MODULE, HasPermission(P_VIEW, P_APPROVE, P_DELETE)]

    def get(self, request, pk: int):
        application = (scoping.applications_for(_actor(request))
                       .filter(pk=pk).first())
        if application is None:
            raise NotFoundError("That leave request does not exist.",
                                code="not_found")
        events = application.events.all()
        return Response(s.LeaveEventSerializer(events, many=True).data)


@extend_schema(responses=s.LeaveApplicationSerializer(many=True))
class ApprovalsInboxView(_PeopleMixin, generics.ListAPIView):
    """Pending requests in scope; never the approver's own (BR-08)."""

    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def get_queryset(self):
        return scoping.approvals_inbox(_actor(self.request)).order_by(
            "start_date", "id")


# -- Balances ------------------------------------------------------------------
@extend_schema(responses=s.BalanceSerializer(many=True))
class BalanceListView(APIView):
    """Own buckets; an approver may ask for one person's."""

    permission_classes = [MODULE, HasPermission(P_BALANCE_VIEW, P_APPROVE)]

    def get(self, request):
        actor = _actor(request)
        year = _int_param(request.query_params, "year") or timezone.localdate().year
        user_id = _int_param(request.query_params, "user_id")
        # Narrowing, never a 403: an applicant asking for someone else simply
        # reads their own buckets.
        if user_id is None or not scoping.is_approver(actor):
            user_id = getattr(actor, "user_id", None)
        rows = queries.balances_for(user_id, year) if user_id is not None else []
        data = [{
            "user_id": user_id,
            "leave_type_code": row.leave_type.code,
            "leave_type_name": row.leave_type.name,
            "entitled_days": row.entitled,
            "used_days": row.used,
            "available_days": row.available,
        } for row in rows]
        return Response(s.BalanceSerializer(data, many=True).data)


@extend_schema(request=s.BalanceAdjustmentSerializer, responses={201: None},
               examples=[OpenApiExample(
                   "Credit three compensatory days",
                   request_only=True,
                   value={"user_id": 1001, "leave_type_id": 4, "year": 2026,
                          "days": "3.0",
                          "note": "Worked the verification weekend"})])
class BalanceGrantView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE_MANAGE)]

    def post(self, request):
        payload = s.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        entry = balance_service.adjust_balance(actor=_actor(request),
                                               **payload.validated_data)
        return Response({"id": entry.pk, "days": str(entry.days)},
                        status=status.HTTP_201_CREATED)
