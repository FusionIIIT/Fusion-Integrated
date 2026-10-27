"""Leave endpoints (AFR-EL-024..032).

Two gates on every view: `HasModuleGrant("leave")` and the fine-grained permission
the action needs. Both are declared on the view, so forgetting a permission fails
closed. Row-level authority lives in `selectors.scoping` and the service layer;
a row the caller may not see is a 404.
"""
from __future__ import annotations

from django.db.models import Prefetch
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from fusion_auth.permissions import IsAuthenticatedPrincipal
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import services
from modules.leave.api import serializers as ser
from modules.leave.models import (
    ApprovalTask,
    CancellationRequest,
    ExtensionRequest,
    HierarchyRoute,
    LeaveBalance,
    LeaveRequest,
    OrganizationalUnit,
    ResumptionRequest,
    SlaThreshold,
    SubstituteNomination,
)
from modules.leave.models.requests import TASK_PENDING
from modules.leave.selectors import queries, scoping

MODULE = "leave"


def _gates(*permission_codes: str) -> list:
    """Authentication, module grant, then the fine-grained permission.

    Ordered coarse to fine, so the failure a caller sees is the outermost thing
    that is actually wrong with their request. With no codes this is the coarse
    pair alone, which is right for a read that needs no specific capability.
    """
    gates = [IsAuthenticatedPrincipal, HasModuleGrant(MODULE)]
    if permission_codes:
        gates.append(HasPermission(*permission_codes))
    return gates


_view_gates = _gates()


class LeaveApiView(APIView):
    """The shared base: `principal` is the actor every service call expects."""
    permission_classes = _view_gates

    @property
    def actor(self):
        return self.request.principal


class MyRequestsView(LeaveApiView):
    """EL-UC-001: strictly the caller's own applications, never anyone else's."""
    @extend_schema(responses=ser.LeaveRequestSerializer(many=True),
                   parameters=[OpenApiParameter("status", str),
                               OpenApiParameter("category", str),
                               OpenApiParameter("year", int)])
    def get(self, request):
        rows = queries.my_requests(request.principal)
        return Response(ser.LeaveRequestSerializer(rows, many=True).data)


class RequestCountsView(LeaveApiView):
    """EL-UC-002: per-status counts, computed in one query rather than one per
    status."""

    @extend_schema(responses={200: dict})
    def get(self, request):
        return Response(queries.request_counts(request.principal))


class LeaveRequestViewSet(viewsets.GenericViewSet):
    """Draft, submit, withdraw, and the owner-only detail screen."""
    serializer_class = ser.LeaveRequestSerializer

    def get_permissions(self):
        """Require the capability appropriate to each request action."""
        permission_by_action = {
            "create": ("leave.request.create",),
            "partial_update": ("leave.request.create",),
            "destroy": ("leave.request.delete",),
            "retrieve": ("leave.request.view_self", "leave.request.view"),
            "overlaps": ("leave.request.view_self", "leave.request.view"),
            "submit": ("leave.request.create",),
            "withdraw": ("leave.request.create", "leave.request.delete"),
            "nominate": ("leave.request.create",),
        }
        return [
            permission()
            for permission in _gates(*permission_by_action.get(
                self.action, ("leave.request.create",)
            ))
        ]

    def get_queryset(self):
        return scoping.requests_for(self.request.principal)

    def _scoped(self, pk: int) -> LeaveRequest:
        row = scoping.requests_for(self.request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such leave request.")
        return row

    def _owned(self, pk: int) -> LeaveRequest:
        row = self._scoped(pk)
        services.authz.require_owner(self.request.principal, row)
        return row

    @extend_schema(responses=ser.LeaveRequestSerializer)
    def retrieve(self, request, pk=None):
        row = self._scoped(pk)
        return Response(self.serializer_class(row).data)

    @extend_schema(request=ser.LeaveRequestWriteSerializer,
                   responses=ser.LeaveRequestSerializer)
    def create(self, request):
        payload = ser.LeaveRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.leave.apply(request.principal, **payload.validated_data)
        return Response(self.serializer_class(row).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(request=ser.LeaveRequestWriteSerializer,
                   responses=ser.LeaveRequestSerializer)
    def partial_update(self, request, pk=None):
        row = self._owned(pk)
        payload = ser.LeaveRequestWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        updated = services.leave.update_draft(request.principal, row,
                                              **payload.validated_data)
        return Response(self.serializer_class(updated).data)

    @extend_schema(responses={204: None})
    def destroy(self, request, pk=None):
        services.leave.delete_draft(request.principal, self._owned(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=ser.SubmitSerializer,
                   responses=ser.LeaveRequestSerializer)
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        row = services.leave.submit(self.request.principal, self._owned(pk))
        return Response(self.serializer_class(row).data)

    @extend_schema(request=None, responses=ser.LeaveRequestSerializer)
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        row = services.leave.withdraw(self.request.principal, self._owned(pk))
        return Response(self.serializer_class(row).data)

    @extend_schema(request=ser.NominateSerializer,
                   responses=ser.SubstituteNominationSerializer)
    @action(detail=True, methods=["post"], url_path="nominate-substitute")
    def nominate(self, request, pk=None):
        payload = ser.NominateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.leave.nominate_substitute(
            request.principal, self._owned(pk), **payload.validated_data)
        return Response(ser.SubstituteNominationSerializer(row).data,
                        status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["get"], url_path="overlaps")
    def overlaps(self, request, pk=None):
        """BR-EL-024: what this request collides with, and what is exempt."""
        groups = services.leave.active_overlap(self._scoped(pk))
        return Response({name: ser.LeaveRequestSerializer(rows, many=True).data
                         for name, rows in groups.items()})


class DraftsView(LeaveApiView):
    @extend_schema(responses=ser.LeaveRequestSerializer(many=True))
    def get(self, request):
        return Response(ser.LeaveRequestSerializer(
            queries.draft_requests(request.principal), many=True).data)


class SubstitutionQueueView(LeaveApiView):
    """EL-UC-003: nominations addressed to me."""
    permission_classes = _gates("leave.substitute.respond")

    @extend_schema(responses=ser.SubstituteNominationSerializer(many=True))
    def get(self, request):
        rows = SubstituteNomination.objects.filter(
            nominee_user_id=request.principal.user_id).order_by("-id")
        return Response(ser.SubstituteNominationSerializer(rows, many=True).data)


class NominationResponseView(LeaveApiView):
    """EL-UC-004: accept or decline, and only as the nominated person."""
    permission_classes = _gates("leave.substitute.respond")

    @extend_schema(request=ser.NominationResponseSerializer,
                   responses=ser.SubstituteNominationSerializer)
    def post(self, request, pk=None):
        payload = ser.NominationResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        nomination = SubstituteNomination.objects.filter(pk=pk).first()
        if nomination is None:
            raise NotFoundError("No such nomination.")
        row = services.leave.respond_to_nomination(
            request.principal, nomination, **payload.validated_data)
        return Response(ser.SubstituteNominationSerializer(row).data)


class ApprovalsView(LeaveApiView):
    """EL-UC-007: the tasks waiting on me, with the requests they refer to."""
    permission_classes = _gates("leave.request.approve")

    @extend_schema(responses=ser.ApprovalTaskSerializer(many=True))
    def get(self, request):
        rows = scoping.tasks_for(request.principal).select_related("leave_request")
        return Response(ser.ApprovalTaskSerializer(rows, many=True).data)


class TaskDecisionView(LeaveApiView):
    """The one deciding endpoint for CW-EL-01, and the reason a task names its
    assignee rather than trusting the permission alone (BR-EL-036)."""
    permission_classes = _gates("leave.request.approve")

    @extend_schema(request=ser.DecisionSerializer,
                   responses=ser.LeaveRequestSerializer)
    def post(self, request, pk=None):
        payload = ser.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        task = ApprovalTask.objects.filter(pk=pk).first()
        if task is None:
            raise NotFoundError("No such task.")

        decision = payload.validated_data
        if task.kind in services.lifecycle.NON_DECISION_KINDS:
            row = _decide_lifecycle(request.principal, task, decision)
            return Response(_lifecycle_payload(task, row))

        leave = services.leave.decide(request.principal, task, **decision)
        return Response(ser.LeaveRequestSerializer(leave).data)


def _decide_lifecycle(actor, task: ApprovalTask, decision: dict):
    approve = decision["approve"]
    note = decision.get("note", "")
    recommendation = decision.get("recommendation", "")
    if task.kind in ("cancellation_unit_head", "cancellation_establishment",
                     "cancellation_final"):
        return services.lifecycle.decide_cancellation(
            actor, task, approve=approve, note=note, recommendation=recommendation)
    if task.kind in ("extension_unit_head", "extension_establishment",
                     "extension_final"):
        return services.lifecycle.decide_extension(
            actor, task, approve=approve, note=note, recommendation=recommendation)
    if task.kind == "resumption_review":
        return services.lifecycle.review_resumption(actor, task, note=note)
    raise NotFoundError("No such task.")


def _lifecycle_payload(task: ApprovalTask, row) -> dict:
    if isinstance(row, CancellationRequest):
        return ser.CancellationRequestSerializer(row).data
    if isinstance(row, ExtensionRequest):
        return ser.ExtensionRequestSerializer(row).data
    return ser.ResumptionRequestSerializer(row).data


class CancellationView(LeaveApiView):
    """EL-UC-016: cancel approved leave before it starts (BR-EL-023)."""
    @extend_schema(request=ser.ReasonSerializer,
                   responses=ser.CancellationRequestSerializer)
    def post(self, request, pk=None):
        payload = ser.ReasonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = scoping.requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such leave request.")
        cancellation = services.lifecycle.request_cancellation(
            request.principal, row, **payload.validated_data)
        return Response(ser.CancellationRequestSerializer(cancellation).data,
                        status=status.HTTP_201_CREATED)


class ExtensionView(LeaveApiView):
    """EL-UC-017: extend leave already approved (BR-EL-025)."""
    @extend_schema(request=ser.ExtensionRequestWriteSerializer,
                   responses=ser.ExtensionRequestSerializer)
    def post(self, request, pk=None):
        payload = ser.ExtensionRequestWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = scoping.requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such leave request.")
        extension = services.lifecycle.request_extension(
            request.principal, row, **payload.validated_data)
        return Response(ser.ExtensionRequestSerializer(extension).data,
                        status=status.HTTP_201_CREATED)


class ResumptionView(LeaveApiView):
    """EL-UC-018: report an actual return (BR-EL-027)."""
    @extend_schema(request=ser.ResumptionWriteSerializer,
                   responses=ser.ResumptionRequestSerializer)
    def post(self, request, pk=None):
        payload = ser.ResumptionWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = scoping.requests_for(request.principal).filter(pk=pk).first()
        if row is None:
            raise NotFoundError("No such leave request.")
        resumption = services.lifecycle.submit_resumption(
            request.principal, row, **payload.validated_data)
        return Response(ser.ResumptionRequestSerializer(resumption).data,
                        status=status.HTTP_201_CREATED)


class LifecycleListView(LeaveApiView):
    """EL-UC-019: cancellations, extensions and resumptions in one place, so the
    employee can see every change to a leave they have."""
    @extend_schema(responses=dict)
    def get(self, request):
        actor = request.principal
        return Response({
            "cancellations": ser.CancellationRequestSerializer(
                scoping.cancellations_for(actor), many=True).data,
            "extensions": ser.ExtensionRequestSerializer(
                scoping.extensions_for(actor), many=True).data,
            "resumptions": ser.ResumptionRequestSerializer(
                scoping.resumptions_for(actor), many=True).data,
        })


class BalancesView(LeaveApiView):
    """EL-UC-012: my balances, or any person's for a record administrator."""
    @extend_schema(responses=ser.LeaveBalanceSerializer(many=True))
    def get(self, request):
        year = request.query_params.get("year")
        rows = queries.balances(request.principal,
                                year=int(year) if year else None)
        return Response(ser.LeaveBalanceSerializer(rows, many=True).data)


class BalanceAdjustmentView(LeaveApiView):
    """EL-UC-013: a correction is a ledger entry with a reason (BR-EL-026)."""
    permission_classes = _gates("leave.balance.update")

    @extend_schema(request=ser.BalanceAdjustmentSerializer, responses={201: dict})
    def post(self, request):
        payload = ser.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.admin.adjust_balance(request.principal, **payload.validated_data)
        return Response({"recorded": True}, status=status.HTTP_201_CREATED)


class LedgerView(LeaveApiView):
    """BR-EL-026: the account behind the balance, readable within scope."""
    @extend_schema(responses=ser.LeaveLedgerEntrySerializer(many=True))
    def get(self, request):
        params = request.query_params
        rows = queries.ledger_entries(
            request.principal,
            user_id=int(params["user_id"]) if params.get("user_id") else None,
            year=int(params["year"]) if params.get("year") else None,
            category=params.get("category", ""))
        return Response(ser.LeaveLedgerEntrySerializer(rows, many=True).data)


class LeaveAdminConfigView(LeaveApiView):
    """EL-UC-014: policy, hierarchy and calendar, in one place."""
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(responses=dict)
    def get(self, request):
        return Response({
            "policy": ser.LeavePolicySerializer(services.admin.read_policy()).data,
            "units": ser.OrganizationalUnitSerializer(
                OrganizationalUnit.objects.all(), many=True).data,
            "routes": ser.HierarchyRouteSerializer(
                HierarchyRoute.objects.prefetch_related("steps"),
                many=True).data,
            "thresholds": ser.SlaThresholdSerializer(
                SlaThreshold.objects.all(), many=True).data,
            "calendar": services.admin.calendar_summary(),
            "unassigned_steps": services.admin.unassigned_steps(),
        })


class PolicyView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.LeavePolicySerializer, responses=ser.LeavePolicySerializer)
    def patch(self, request):
        services.admin.ensure_configured(request.principal)
        return Response(ser.LeavePolicySerializer(
            services.admin.update_policy(request.principal, **request.data)).data)


class HolidayCalendarView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.HolidayWriteSerializer, responses={201: dict})
    def post(self, request):
        payload = ser.HolidayWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.admin.save_holiday(request.principal, **payload.validated_data)
        return Response({"recorded": True}, status=status.HTTP_201_CREATED)


class HolidayCalendarPublishView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(responses=ser.HolidayCalendarSerializer)
    def post(self, request, pk=None):
        calendar = services.admin.publish_calendar(request.principal, year=int(pk))
        return Response(ser.HolidayCalendarSerializer(calendar).data)


class VacationPeriodView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.VacationPeriodSerializer,
                   responses=ser.VacationPeriodSerializer)
    def post(self, request):
        payload = ser.VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        period = services.admin.save_vacation_period(
            request.principal, **payload.validated_data)
        return Response(ser.VacationPeriodSerializer(period).data,
                        status=status.HTTP_201_CREATED)


class RouteView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.RouteWriteSerializer, responses=ser.HierarchyRouteSerializer)
    def post(self, request):
        payload = ser.RouteWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        route = services.admin.save_route(request.principal, **payload.validated_data)
        return Response(ser.HierarchyRouteSerializer(route).data,
                        status=status.HTTP_201_CREATED)


class OrganizationalUnitView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.UnitWriteSerializer,
                   responses=ser.OrganizationalUnitSerializer)
    def post(self, request):
        payload = ser.UnitWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        unit = services.admin.upsert_unit(request.principal, **payload.validated_data)
        return Response(ser.OrganizationalUnitSerializer(unit).data)


class ThresholdView(LeaveApiView):
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.ThresholdWriteSerializer,
                   responses=ser.SlaThresholdSerializer)
    def post(self, request):
        payload = ser.ThresholdWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = services.admin.save_threshold(request.principal, **payload.validated_data)
        return Response(ser.SlaThresholdSerializer(row).data)


class OfflineLeaveView(LeaveApiView):
    """BR-EL-029: leave already sanctioned outside the system."""
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(request=ser.OfflineLeaveSerializer, responses={201: dict})
    def post(self, request):
        payload = ser.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.admin.record_offline_leave(request.principal,
                                            **payload.validated_data)
        return Response({"recorded": True}, status=status.HTTP_201_CREATED)


class ReconciliationView(LeaveApiView):
    permission_classes = _gates("leave.balance.update")

    @extend_schema(request=ser.ReconciliationSerializer,
                   responses=ser.LeaveBalanceSerializer(many=True))
    def post(self, request):
        payload = ser.ReconciliationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rows = services.admin.reconcile_account(request.principal,
                                                **payload.validated_data)
        return Response(ser.LeaveBalanceSerializer(rows, many=True).data)


class ExceptionOverviewView(LeaveApiView):
    """BR-EL-032/033: what is overdue, and where it is stuck."""
    permission_classes = _gates("leave.record.maintain")

    @extend_schema(responses=dict)
    def get(self, request):
        return Response(services.sla.overdue_overview())


class OverdueOutOfOfficeView(LeaveApiView):
    """BR-EL-032: approved leave past its end date and not yet returned."""
    permission_classes = _gates("leave.request.view")

    @extend_schema(responses=ser.LeaveRequestSerializer(many=True))
    def get(self, request):
        rows = queries.overdue_out_of_office(
            request.principal, today=timezone.now().date()).prefetch_related(
                Prefetch("resumptions", queryset=ResumptionRequest.objects.all()))
        return Response(ser.LeaveRequestSerializer(rows, many=True).data)


class YearEndRunView(LeaveApiView):
    """EL-UC-020 / BR-EL-001: run the closing year."""
    permission_classes = _gates("leave.year_end.process")

    @extend_schema(request=ser.YearEndRunSerializer, responses={200: dict})
    def post(self, request):
        payload = ser.YearEndRunSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        report = services.year_end.run(**payload.validated_data)
        return Response({"report": str(report),
                         "year": report.year, "credited": report.credited,
                         "lapsed": report.lapsed, "converted": report.converted,
                         "carried": report.carried, "skipped": report.skipped,
                         "exceptions": report.exceptions})


class YearEndStatusView(LeaveApiView):
    permission_classes = _gates("leave.year_end.process")

    @extend_schema(responses=dict)
    def get(self, request):
        today = timezone.now().date()
        pol = services.admin.read_policy()
        pending = services.year_end.is_due(today=today, policy=pol)
        return Response({"today": today.isoformat(),
                         "year_end_month": pol.year_end_month,
                         "due": pending,
                         "pending_tasks": queries.escalated_task_count(
                             today=today)})
