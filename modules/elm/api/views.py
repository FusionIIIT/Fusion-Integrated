"""HTTP layer: parse, check the grant, delegate to a service, serialise."""
from __future__ import annotations

from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import LeaveApplication
from modules.elm.selectors import applications as sel
from modules.elm.selectors import queues
from modules.elm.services import applications, balances, calendar, decisions, lifecycle, offline
from modules.elm.services import year_end as year_end_service

MODULE = HasModuleGrant("elm")
P_APPLY = "elm.leave.apply"
P_VIEW = "elm.leave.view"
P_REVIEW = queues.P_REVIEW
P_ROUTE = queues.P_ROUTE
P_SANCTION = queues.P_SANCTION
P_SELF_SANCTION = queues.P_SELF_SANCTION
P_ADMINISTER = "elm.leave.administer"

EMPLOYEE_KINDS = ("faculty", "staff")


def _one(application: LeaveApplication) -> Response:
    return Response(s.LeaveApplicationSerializer(application).data)


def _caller(request) -> int:
    return request.principal.user_id


class ApplicationsView(APIView):
    """GET: your own applications. POST: apply for leave."""

    def get_permissions(self):
        code = P_APPLY if self.request.method == "POST" else P_VIEW
        return [MODULE(), HasPermission(code)()]

    @extend_schema(operation_id="elm_applications_list", responses=s.ApplicationListSerializer)
    def get(self, request):
        rows = sel.own_applications(_caller(request))
        status_filter = request.query_params.get("status")
        if status_filter:
            rows = rows.filter(status=status_filter)
        return Response({"results": s.LeaveApplicationSerializer(rows[:200], many=True).data})

    @extend_schema(request=s.ApplyInputSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        data = s.ApplyInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        application = applications.submit(request.principal, data.validated_data)
        return Response(s.LeaveApplicationSerializer(application).data,
                        status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(operation_id="elm_application_retrieve",
                   responses=s.LeaveApplicationDetailSerializer)
    def get(self, request, pk):
        application = sel.application(pk)
        if application is None or not queues.can_view(request.principal, application):
            raise NotFoundError("Application not found.")
        return Response(s.LeaveApplicationDetailSerializer(application).data)


class _Action(APIView):
    """Shared shape of an action on one application."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]


class ModifyView(_Action):
    @extend_schema(request=s.ApplyInputSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.ApplyInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(applications.modify(request.principal, pk, data.validated_data))


class WithdrawView(_Action):
    @extend_schema(request=None, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        return _one(applications.withdraw(request.principal, pk))


class CancelView(_Action):
    @extend_schema(request=s.ReasonSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(lifecycle.request_cancellation(
            request.principal, pk, reason=data.validated_data["reason"]))


class ExtendView(_Action):
    @extend_schema(request=s.ExtendInputSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request, pk):
        data = s.ExtendInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        extension = lifecycle.request_extension(request.principal, pk, data.validated_data)
        return Response(s.LeaveApplicationSerializer(extension).data,
                        status=status.HTTP_201_CREATED)


class ResumeView(_Action):
    @extend_schema(request=s.ResumeSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.ResumeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(lifecycle.submit_resumption(
            request.principal, pk, resumed_on=data.validated_data["resumed_on"]))


class SubstituteResponseView(_Action):
    @extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.SubstituteResponseSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(decisions.respond_as_substitute(
            request.principal, pk, accept=data.validated_data["accept"]))


class UnitHeadView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.UnitHeadDecisionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.UnitHeadDecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(decisions.unit_head_decide(
            request.principal, pk, decision=data.validated_data["decision"],
            reason=data.validated_data["reason"]))


class RouteView(APIView):
    permission_classes = [MODULE, HasPermission(P_ROUTE)]

    @extend_schema(request=s.RouteSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.RouteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(decisions.establishment_route(
            request.principal, pk, note=data.validated_data["note"]))


class SanctionView(APIView):
    permission_classes = [MODULE, HasPermission(P_SANCTION)]

    @extend_schema(request=s.SanctionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.SanctionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        return _one(decisions.final_decide(
            request.principal, pk, approve=v["approve"], reason=v["reason"],
            special_purpose_admissible=v["special_purpose_admissible"]))


class SelfSanctionView(APIView):
    permission_classes = [MODULE, HasPermission(P_SELF_SANCTION)]

    @extend_schema(request=s.ReasonSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(decisions.director_self_sanction(
            request.principal, pk, reason=data.validated_data["reason"]))


class VerifyResumptionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.VerifyResumptionSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        data = s.VerifyResumptionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return _one(lifecycle.verify_resumption(
            request.principal, pk, verified=data.validated_data["verified"]))


class TasksView(APIView):
    """The applications waiting on the caller's role."""

    permission_classes = [MODULE, HasPermission(P_REVIEW, P_ROUTE, P_SANCTION, P_SELF_SANCTION)]

    @extend_schema(responses=s.ApplicationListSerializer)
    def get(self, request):
        rows = queues.tasks_for(request.principal)
        return Response({"results": s.LeaveApplicationSerializer(rows, many=True).data})


class BalancesView(APIView):
    """The caller's balances for a year (default: this one)."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.BalanceListSerializer)
    def get(self, request):
        try:
            year = int(request.query_params.get("year", date.today().year))
        except ValueError:
            year = date.today().year
        balances.ensure_balances(_caller(request), year, request.principal.kind)
        return Response({"results": s.LeaveBalanceSerializer(
            sel.balances(_caller(request), year), many=True).data})


class NotificationsView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(responses=s.NotificationListSerializer)
    def get(self, request):
        rows = sel.notifications_for(_caller(request), request.principal.permissions)[:100]
        return Response({"results": s.LeaveNotificationSerializer(rows, many=True).data})


class CalendarView(APIView):
    """GET: the published calendar. POST: add an entry (administrators)."""

    def get_permissions(self):
        code = P_ADMINISTER if self.request.method == "POST" else P_VIEW
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=s.CalendarSerializer)
    def get(self, request):
        return Response(sel.calendar())

    @extend_schema(request=s.CalendarEntryInputSerializer, responses={201: s.CalendarSerializer})
    def post(self, request):
        data = s.CalendarEntryInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        calendar.add_entry(request.principal, data.validated_data)
        return Response(sel.calendar(), status=status.HTTP_201_CREATED)


class OfflineView(APIView):
    """Record leave that was sanctioned on paper (BR-EL-029)."""

    permission_classes = [MODULE, HasPermission(P_ADMINISTER)]

    @extend_schema(request=s.OfflineInputSerializer, responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        data = s.OfflineInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        application = offline.record(request.principal, data.validated_data)
        return Response(s.LeaveApplicationSerializer(application).data,
                        status=status.HTTP_201_CREATED)


class YearEndView(APIView):
    permission_classes = [MODULE, HasPermission(P_ADMINISTER)]

    @extend_schema(request=s.YearEndInputSerializer, responses=s.YearEndReportSerializer)
    def post(self, request):
        data = s.YearEndInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        report = year_end_service.run(data.validated_data["year"],
                                      force=data.validated_data["force"])
        return Response(s.YearEndReportSerializer(report).data)


