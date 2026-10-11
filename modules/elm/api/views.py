"""HTTP layer: parse, scope, delegate, serialise."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.domain import policy
from modules.elm.models import (
    CategoryPolicy,
    HolidayCalendar,
    SanctionRoute,
    SlaPolicy,
    UnitHead,
    VacationPeriod,
)
from modules.elm.selectors import accounts as acc
from modules.elm.selectors import scoping
from modules.elm.services import accounts as ledger
from modules.elm.services import admin
from modules.elm.services import requests as leave

MODULE = HasModuleGrant("elm")
P_VIEW = "elm.leave_request.view"
P_CREATE = "elm.leave_request.create"
P_TASKS = "elm.leave_task.view"
P_DECIDE = ("elm.leave_request.review", "elm.leave_request.assign",
            "elm.leave_request.approve")
P_POLICY = "elm.policy.update"
P_CALENDAR = "elm.holiday_calendar.publish"
P_RECORD = "elm.leave_record.create"


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name, default=None):
    raw = params.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc


def _detail(req):
    return Response(s.LeaveRequestDetailSerializer(req).data)


# -- employee -----------------------------------------------------------------
@extend_schema(responses=s.BalanceSerializer,
               parameters=[OpenApiParameter("year", int)])
class BalanceView(APIView):
    """EL-UC-012."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request):
        p = _actor(request)
        year = _int_param(request.query_params, "year", timezone.localdate().year)
        if p.kind in policy.EMPLOYEE_KINDS:
            ledger.ensure_annual_credits(p.user_id, p.kind, year)
        entries = acc.ledger_entries(p.user_id, year)
        return Response({
            "year": year,
            "balances": acc.balances(p.user_id, year),
            "ledger": s.LedgerEntrySerializer(entries, many=True).data,
        })


class MyRequestListView(generics.ListCreateAPIView):
    """EL-UC-012 history, and EL-UC-001 apply."""

    serializer_class = s.LeaveRequestSerializer

    def get_permissions(self):
        code = P_CREATE if self.request.method == "POST" else P_VIEW
        return [MODULE(), HasPermission(code)()]

    def get_queryset(self):
        qs = scoping.own_requests(_actor(self.request))
        kind = self.request.query_params.get("kind")
        return qs.filter(kind=kind) if kind else qs

    @extend_schema(request=s.ApplySerializer, responses=s.LeaveRequestDetailSerializer)
    def create(self, request, *args, **kwargs):
        payload = s.ApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = leave.apply(_actor(request), **payload.validated_data)
        return Response(s.LeaveRequestDetailSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class RequestDetailView(generics.RetrieveAPIView):
    """EL-UC-013: the printable representation is this, rendered by the client."""

    serializer_class = s.LeaveRequestDetailSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE, P_TASKS)]

    def get_queryset(self):
        return scoping.visible_requests(_actor(self.request)).prefetch_related(
            "events")


class _OwnAction(APIView):
    permission_classes = [MODULE, HasPermission(P_CREATE)]


class WithdrawView(_OwnAction):
    @extend_schema(request=None, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        return _detail(leave.withdraw(_actor(request), pk))


class CancelView(_OwnAction):
    @extend_schema(request=s.ReasonSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.ReasonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.request_cancellation(
            _actor(request), parent_id=pk, reason=payload.validated_data["reason"]))


class ExtendView(_OwnAction):
    @extend_schema(request=s.ExtendSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.ExtendSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.request_extension(_actor(request), parent_id=pk,
                                               **payload.validated_data))


class ResumeView(_OwnAction):
    @extend_schema(request=s.ResumeSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.ResumeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.submit_resumption(_actor(request), parent_id=pk,
                                               **payload.validated_data))


class RenominateView(_OwnAction):
    @extend_schema(request=s.SubstituteSerializer,
                   responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.SubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.renominate(_actor(request), pk,
                                        **payload.validated_data))


class SubstituteTaskListView(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_CREATE)]

    def get_queryset(self):
        return scoping.substitute_tasks(_actor(self.request))


class SubstituteRespondView(_OwnAction):
    @extend_schema(request=s.RespondSerializer,
                   responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.RespondSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.respond_as_substitute(
            _actor(request), pk, accept=payload.validated_data["accept"]))


class NotificationListView(generics.ListAPIView):
    serializer_class = s.NotificationSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW, P_TASKS)]

    def get_queryset(self):
        return scoping.own_notifications(_actor(self.request))


@extend_schema(responses=s.EmployeeSerializer(many=True),
               parameters=[OpenApiParameter("q", str)])
class EmployeeSearchView(APIView):
    """Substitute picker: faculty and staff only (BR-EL-014)."""

    permission_classes = [MODULE, HasPermission(P_CREATE, P_POLICY, P_RECORD)]

    def get(self, request):
        q = request.query_params.get("q", "")[:60]
        rows = [u for kind in sorted(policy.EMPLOYEE_KINDS)
                for u in directory.search(q, kind=kind, limit=15)]
        return Response(s.EmployeeSerializer(rows, many=True).data)


@extend_schema(responses=s.HolidayCalendarSerializer,
               parameters=[OpenApiParameter("year", int)])
class PublishedCalendarView(APIView):
    """BR-EL-031: what applicants validate against."""

    permission_classes = [MODULE, HasPermission(P_VIEW, P_CREATE, P_CALENDAR)]

    def get(self, request):
        year = _int_param(request.query_params, "year", timezone.localdate().year)
        cal = acc.published_calendar(year)
        if cal is None:
            raise NotFoundError(f"No holiday calendar is published for {year}.")
        return Response(s.HolidayCalendarSerializer(cal).data)


# -- reviewers ------------------------------------------------------------------
class TaskListView(generics.ListAPIView):
    """EL-UC-003/004/005/011 work queue for the acting role."""

    serializer_class = s.LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission(P_TASKS)]

    def get_queryset(self):
        return scoping.review_tasks(_actor(self.request))


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(*P_DECIDE)]

    @extend_schema(request=s.DecideSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk):
        payload = s.DecideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return _detail(leave.decide(_actor(request), pk, **payload.validated_data))


# -- administration -------------------------------------------------------------
class CategoryPolicyView(generics.ListAPIView):
    """EL-UC-014: current entitlements, edited in place (BR-EL-030)."""

    serializer_class = s.CategoryPolicySerializer
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    pagination_class = None
    queryset = CategoryPolicy.objects.order_by("category")

    @extend_schema(request=s.CategoryPolicySerializer,
                   responses=s.CategoryPolicySerializer)
    def put(self, request):
        payload = s.CategoryPolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = admin.set_category_days(payload.validated_data["category"],
                                      payload.validated_data["annual_days"],
                                      _actor(request).user_id)
        return Response(s.CategoryPolicySerializer(row).data)


class UnitHeadView(generics.ListCreateAPIView):
    serializer_class = s.UnitHeadSerializer
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    pagination_class = None
    queryset = UnitHead.objects.order_by("unit")

    def create(self, request, *args, **kwargs):
        payload = s.UnitHeadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = admin.set_unit_head(payload.validated_data["unit"],
                                  payload.validated_data["head_user_id"])
        return Response(s.UnitHeadSerializer(row).data, status=status.HTTP_201_CREATED)


class SanctionRouteView(generics.ListCreateAPIView):
    serializer_class = s.SanctionRouteSerializer
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    pagination_class = None
    queryset = SanctionRoute.objects.order_by("category", "applicant_kind")

    def create(self, request, *args, **kwargs):
        payload = s.SanctionRouteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        row = admin.set_route(d["category"], d["applicant_kind"],
                              d["authority_user_id"], d.get("establishment_user_id"))
        return Response(s.SanctionRouteSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class SlaPolicyView(generics.ListCreateAPIView):
    """EL-UC-018. The newest row is the one in force."""

    serializer_class = s.SlaPolicySerializer
    permission_classes = [MODULE, HasPermission(P_POLICY)]
    pagination_class = None

    def get_queryset(self):
        return SlaPolicy.objects.order_by("-created_at", "-id")[:1]

    def create(self, request, *args, **kwargs):
        payload = s.SlaPolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        row = admin.set_sla(d["reminder_hours"], d["escalation_hours"],
                            d.get("escalation_user_id"))
        return Response(s.SlaPolicySerializer(row).data, status=status.HTTP_201_CREATED)


class CalendarListView(generics.ListCreateAPIView):
    """EL-UC-015."""

    serializer_class = s.HolidayCalendarSerializer
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    pagination_class = None
    queryset = HolidayCalendar.objects.prefetch_related("holidays")

    @extend_schema(request=s.CalendarCreateSerializer,
                   responses=s.HolidayCalendarSerializer)
    def create(self, request, *args, **kwargs):
        payload = s.CalendarCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cal = admin.draft_calendar(payload.validated_data["year"])
        return Response(s.HolidayCalendarSerializer(cal).data,
                        status=status.HTTP_201_CREATED)


class HolidayCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=s.HolidaySerializer, responses=s.HolidaySerializer)
    def post(self, request, pk):
        payload = s.HolidaySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        row = admin.add_holiday(pk, on=d["date"], name=d["name"], kind=d["kind"])
        return Response(s.HolidaySerializer(row).data, status=status.HTTP_201_CREATED)


class HolidayDeleteView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, pk, holiday_id):
        admin.remove_holiday(pk, holiday_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=None, responses=s.HolidayCalendarSerializer)
    def post(self, request, pk):
        return Response(s.HolidayCalendarSerializer(admin.publish_calendar(pk)).data)


class VacationPeriodView(generics.ListCreateAPIView):
    serializer_class = s.VacationPeriodSerializer
    permission_classes = [MODULE, HasPermission(P_CALENDAR)]
    pagination_class = None
    queryset = VacationPeriod.objects.all()

    def create(self, request, *args, **kwargs):
        payload = s.VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        row = admin.add_vacation(d["label"], d["start_date"], d["end_date"])
        return Response(s.VacationPeriodSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class OfflineRecordView(APIView):
    """EL-UC-016."""

    permission_classes = [MODULE, HasPermission(P_RECORD)]

    @extend_schema(request=s.OfflineRecordSerializer,
                   responses=s.LeaveRequestDetailSerializer)
    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        req = admin.record_offline(_actor(request).user_id, **payload.validated_data)
        return Response(s.LeaveRequestDetailSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class AdjustmentView(APIView):
    """EL-UC-017."""

    permission_classes = [MODULE, HasPermission(P_RECORD)]

    @extend_schema(request=s.AdjustmentSerializer, responses=s.LedgerEntrySerializer)
    def post(self, request):
        payload = s.AdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = admin.adjust_balance(_actor(request).user_id, **payload.validated_data)
        return Response(s.LedgerEntrySerializer(row).data,
                        status=status.HTTP_201_CREATED)
