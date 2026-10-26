"""HTTP layer: parse, scope, delegate, serialise.

Every view takes its queryset from a selector, so authorisation is never
re-derived per endpoint — and a request that is not in scope is simply absent,
which is why a detail view answers 404 rather than 403.

Nothing here decides anything. A service raises a domain error and
`core/api/exceptions.py` renders it.
"""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import LeaveCalendar, LeavePolicy, LeaveRequest
from modules.leave.selectors import balances as balance_selectors
from modules.leave.selectors import leave as leave_selectors
from modules.leave.services import (
    accounts,
    applications,
    decisions,
    offline,
    sla,
    year_end,
)
from modules.leave.services import (
    calendar as calendar_service,
)

MODULE = HasModuleGrant("leave")

P_VIEW_SELF = "leave.application.view_self"
P_VIEW_ALL = "leave.application.view"
P_APPLY = "leave.application.create"
P_WITHDRAW = "leave.application.withdraw"
P_CANCEL = "leave.application.cancel"
P_EXTEND = "leave.application.extend"
P_RESPOND = "leave.substitute.respond"
P_NOMINATE = "leave.substitute.nominate"
P_REVIEW = "leave.request.review"
P_ROUTE = "leave.request.route"
P_APPROVE = "leave.request.approve"
P_RESUMPTION_SUBMIT = "leave.resumption.submit"
P_RESUMPTION_REVIEW = "leave.resumption.review"
P_BALANCES = "leave.balance.view"
P_CALENDAR = "leave.calendar.manage"
P_POLICY = "leave.policy.manage"
P_RECORDS = "leave.record.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _page(serializer, rows):
    return {"results": serializer(rows, many=True).data}


# -- the employee's own leave -------------------------------------------------
@extend_schema(tags=["leave"])
class MyRequestsView(APIView):
    """GET /leave/requests   my requests, newest first
       POST /leave/requests  apply for leave
    """

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_APPLY)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True),
                   summary="My leave requests")
    def get(self, request):
        kind = request.query_params.get("kind")
        rows = leave_selectors.my_requests(_actor(request), kind=kind)
        return Response(_page(s.LeaveRequestSerializer, rows))

    @extend_schema(request=s.LeaveApplySerializer,
                   responses={201: s.LeaveRequestSerializer},
                   summary="Apply for leave")
    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = applications.apply(
            principal=_actor(request),
            category_code=data["category"], start=data["from_date"],
            end=data["to_date"], half=data.get("half"),
            purpose=data["purpose"],
            station_leave_required=data.get("station_leave_required", False),
            station_leave_details=data.get("station_leave_details", ""),
            substitute_user_id=data.get("substitute_user_id"),
            substitute_required=data.get("substitute_required", False))
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["leave"])
class MyBalancesView(APIView):
    """GET /leave/balances   my current balances (EL-UC-012)"""

    permission_classes = [MODULE, HasPermission(P_BALANCES)]

    @extend_schema(responses=s.BalanceSerializer(many=True),
                   summary="My leave balances")
    def get(self, request):
        actor = _actor(request)
        policy = LeavePolicy.current()
        year = request.query_params.get("year") or (
            policy.year_label if policy else str(timezone.now().year))
        if policy is not None and actor.user_id:
            accounts.credit_annual(user_id=actor.user_id, year_label=year,
                                   employee_kind=accounts._employee_kind_of(
                                       actor.user_id)
                                   if hasattr(accounts, "_employee_kind_of")
                                   else "staff", policy=policy)
        rows = balance_selectors.balances(actor.user_id, year)
        return Response({"year": year,
                         "results": s.BalanceSerializer(rows, many=True).data})


@extend_schema(tags=["leave"])
class RequestDetailView(APIView):
    """GET /leave/requests/<pk>   one request, with its decision history"""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW_ALL)]

    @extend_schema(responses=s.LeaveRequestSerializer,
                   summary="A leave request and its history")
    def get(self, request, pk):
        row = leave_selectors.request_by_id(_actor(request), pk)
        if row is None:
            raise NotFoundError("No such leave request.", code="not_found")
        return Response({
            **s.LeaveRequestSerializer(row).data,
            "history": s.ApprovalSerializer(row.approvals.all(), many=True).data,
        })


@extend_schema(tags=["leave"])
class WithdrawView(APIView):
    """POST /leave/requests/<pk>/withdraw   EL-UC-007"""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=s.LeaveWithdrawSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Withdraw a pending request")
    def post(self, request, pk):
        payload = s.LeaveWithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = applications.withdraw(
            principal=_actor(request), request_id=pk,
            reason=payload.validated_data.get("reason", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class ReplacementSubstituteView(APIView):
    """POST /leave/requests/<pk>/replacement   EL-UC-019"""

    permission_classes = [MODULE, HasPermission(P_NOMINATE)]

    @extend_schema(request=s.ReplacementSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Nominate a replacement substitute after a decline")
    def post(self, request, pk):
        payload = s.ReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = applications.nominate_replacement(
            principal=_actor(request), request_id=pk,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class SubstitutionInboxView(APIView):
    """GET  /leave/substitutions   what I have been nominated for
       POST /leave/substitutions/<pk>   accept or decline
    """

    permission_classes = [MODULE, HasPermission(P_RESPOND)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True),
                   summary="Requests I am the nominated substitute on")
    def get(self, request):
        rows = leave_selectors.substitution_requests(_actor(request))
        return Response(_page(s.LeaveRequestSerializer, rows))

    @extend_schema(request=s.SubstituteResponseSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Accept or decline a substitution")
    def post(self, request, pk):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = decisions.respond_as_substitute(
            principal=_actor(request), request_id=pk,
            accept=payload.validated_data["accept"])
        return Response(s.LeaveRequestSerializer(row).data)


# -- the processing lanes -----------------------------------------------------
@extend_schema(tags=["leave"])
class TaskInboxView(APIView):
    """GET /leave/inbox   the actionable work assigned to me"""

    permission_classes = [MODULE,
                          HasPermission(P_REVIEW, P_ROUTE, P_APPROVE,
                                        P_RESUMPTION_REVIEW)]

    @extend_schema(summary="My leave work queue")
    def get(self, request):
        rows = leave_selectors.task_inbox(_actor(request))
        return Response({"results": [{
            "task_id": t.pk,
            "stage": t.stage,
            "assigned_at": t.assigned_at,
            "reminder_due_at": t.reminder_due_at,
            "escalation_due_at": t.escalation_due_at,
            "request": s.LeaveRequestSerializer(t.request).data,
        } for t in rows]})


@extend_schema(tags=["leave"])
class UnitHeadReviewView(APIView):
    """POST /leave/requests/<pk>/review   EL-UC-003"""

    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Review at Unit Head")
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = decisions.review_at_unit_head(
            principal=_actor(request), request_id=pk,
            decision=payload.validated_data["decision"],
            remarks=payload.validated_data.get("remarks", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class EstablishmentRouteView(APIView):
    """POST /leave/requests/<pk>/route   EL-UC-004"""

    permission_classes = [MODULE, HasPermission(P_ROUTE)]

    @extend_schema(request=s.RouteSerializer, responses=s.LeaveRequestSerializer,
                   summary="Verify and route a higher-sanction request")
    def post(self, request, pk):
        payload = s.RouteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = decisions.route_at_establishment(
            principal=_actor(request), request_id=pk,
            remarks=payload.validated_data.get("remarks", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class FinalDecisionView(APIView):
    """POST /leave/requests/<pk>/decide   EL-UC-005"""

    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(request=s.DecisionSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Take the final sanctioning decision")
    def post(self, request, pk):
        payload = s.DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = decisions.decide_final(
            principal=_actor(request), request_id=pk,
            decision=payload.validated_data["decision"],
            remarks=payload.validated_data.get("remarks", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class ResumptionView(APIView):
    """POST /leave/leaves/<pk>/resumption   EL-UC-010"""

    permission_classes = [MODULE, HasPermission(P_RESUMPTION_SUBMIT)]

    @extend_schema(request=s.ResumptionSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Submit a resumption of duty")
    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = applications.submit_resumption(
            principal=_actor(request), leave_id=pk,
            actual_date=payload.validated_data["actual_date"],
            remarks=payload.validated_data.get("remarks", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(tags=["leave"])
class ResumptionReviewView(APIView):
    """POST /leave/requests/<pk>/resumption-review   EL-UC-011"""

    permission_classes = [MODULE, HasPermission(P_RESUMPTION_REVIEW)]

    @extend_schema(request=s.ResumptionReviewSerializer,
                   responses=s.LeaveRequestSerializer,
                   summary="Review a submitted resumption")
    def post(self, request, pk):
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = decisions.review_resumption(
            principal=_actor(request), request_id=pk,
            outcome=payload.validated_data["outcome"],
            remarks=payload.validated_data.get("remarks", ""))
        return Response(s.LeaveRequestSerializer(row).data)


# -- approved leave: cancellation and extension -------------------------------
@extend_schema(tags=["leave"])
class CancellationView(APIView):
    """POST /leave/leaves/<pk>/cancellation   EL-UC-008"""

    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    @extend_schema(request=s.CancellationSerializer,
                   responses={201: s.LeaveRequestSerializer},
                   summary="Request cancellation of approved leave")
    def post(self, request, pk):
        payload = s.CancellationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = applications.request_cancellation(
            principal=_actor(request), leave_id=pk,
            reason=payload.validated_data["reason"])
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["leave"])
class ExtensionView(APIView):
    """POST /leave/leaves/<pk>/extension   EL-UC-009"""

    permission_classes = [MODULE, HasPermission(P_EXTEND)]

    @extend_schema(request=s.ExtensionSerializer,
                   responses={201: s.LeaveRequestSerializer},
                   summary="Request an extension of ongoing leave")
    def post(self, request, pk):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = applications.request_extension(
            principal=_actor(request), leave_id=pk,
            end_date=payload.validated_data["end_date"],
            substitute_user_id=payload.validated_data.get("substitute_user_id"),
            substitute_required=payload.validated_data.get(
                "substitute_required", False))
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["leave"])
class ApprovedLeaveView(APIView):
    """GET /leave/leaves   my approved leave, with its amendments"""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True),
                   summary="My approved leave")
    def get(self, request):
        actor = _actor(request)
        rows = (LeaveRequest.objects
                .filter(user_id=actor.user_id, kind="new", status="approved")
                .order_by("-from_date"))
        return Response({"results": [
            {**s.LeaveRequestSerializer(r).data,
             "amendments": s.LeaveRequestSerializer(
                 r.amendments.all(), many=True).data}
            for r in rows]})


# -- staff views --------------------------------------------------------------
@extend_schema(tags=["leave"])
class AllRequestsView(APIView):
    """GET /leave/all   every request, filtered"""

    permission_classes = [MODULE, HasPermission(P_VIEW_ALL)]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True),
                   summary="All leave requests")
    def get(self, request):
        rows = leave_selectors.visible_requests(_actor(request))
        for name in ("status", "category", "kind", "user_id"):
            value = request.query_params.get(name)
            if value:
                rows = rows.filter(**{name: value})
        return Response(_page(s.LeaveRequestSerializer, rows[:200]))


@extend_schema(tags=["leave"])
class OfflineLeaveView(APIView):
    """POST /leave/offline   EL-UC-016: record already-sanctioned leave"""

    permission_classes = [MODULE, HasPermission(P_RECORDS)]

    @extend_schema(request=s.OfflineLeaveSerializer,
                   responses={201: s.LeaveRequestSerializer},
                   summary="Record leave sanctioned offline")
    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = offline.record(principal=_actor(request),
                             **payload.validated_data)
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


# -- configuration ------------------------------------------------------------
@extend_schema(tags=["leave"])
class PolicyView(APIView):
    """GET /leave/policy    the current configured policy
       POST /leave/policy   revise it (EL-UC-014)
    """

    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(responses=s.PolicySerializer, summary="Current policy")
    def get(self, request):
        policy = LeavePolicy.current()
        if policy is None:
            raise NotFoundError("Leave has not been configured yet.",
                                code="policy_missing")
        return Response(s.PolicySerializer(policy).data)

    @extend_schema(request=s.PolicySerializer, responses=s.PolicySerializer,
                   summary="Save the current policy configuration")
    def post(self, request):
        payload = s.PolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        existing = LeavePolicy.current()
        if existing is not None:
            for field, value in payload.validated_data.items():
                setattr(existing, field, value)
            existing.save()
            return Response(s.PolicySerializer(existing).data)
        policy = LeavePolicy.objects.create(**payload.validated_data)
        return Response(s.PolicySerializer(policy).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["leave"])
class CalendarListView(APIView):
    """GET  /leave/calendars        calendars for a year
       POST /leave/calendars       draft a revision (EL-UC-015)
    """

    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(responses=s.CalendarSerializer(many=True),
                   summary="Calendars, published and draft")
    def get(self, request):
        year = request.query_params.get("year")
        rows = LeaveCalendar.objects.all()
        if year:
            rows = rows.filter(year_label=year)
        return Response(_page(s.CalendarSerializer, rows))

    @extend_schema(request=s.CalendarWriteSerializer,
                   responses={201: s.CalendarSerializer},
                   summary="Draft a calendar revision")
    def post(self, request):
        payload = s.CalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = calendar_service.create_draft(
            principal=_actor(request), year_label=data["year_label"],
            label=data.get("label", ""), entries=data["entries"])
        return Response(s.CalendarSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(tags=["leave"])
class CalendarPublishView(APIView):
    """POST /leave/calendars/<pk>/publish   make a revision effective"""

    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(responses=s.CalendarSerializer,
                   summary="Publish a calendar revision")
    def post(self, request, pk):
        row = calendar_service.publish(principal=_actor(request), calendar_id=pk)
        return Response(s.CalendarSerializer(row).data)


@extend_schema(tags=["leave"])
class VacationPeriodsView(APIView):
    """POST /leave/vacations   project the Academic Calendar's vacation
    periods (EXT-01). Idempotent."""

    permission_classes = [MODULE, HasPermission(P_CALENDAR)]

    @extend_schema(request=s.ExtensionSerializer, responses={"count": "int"},
                   summary="Ingest vacation periods for a leave year")
    def post(self, request):
        year = request.data.get("year")
        periods = [(p["date"], p["ends_on"], p.get("label", ""))
                   for p in request.data.get("periods", [])]
        if not year:
            raise NotFoundError("A leave year is required.", code="year_missing")
        count = calendar_service.ingest_vacation_periods(year_label=year,
                                                         periods=periods)
        return Response({"count": count})


@extend_schema(tags=["leave"])
class SlaSweepView(APIView):
    """POST /leave/sla/sweep   EVT-02, runnable by hand for a check."""

    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(summary="Run the SLA reminder and escalation sweep")
    def post(self, request):
        return Response({"report": str(sla.sweep())})


@extend_schema(tags=["leave"])
class YearEndView(APIView):
    """POST /leave/year-end   EVT-01, runnable by hand for a check."""

    permission_classes = [MODULE, HasPermission(P_POLICY)]

    @extend_schema(summary="Run year-end leave processing")
    def post(self, request):
        policy = LeavePolicy.current()
        if policy is None:
            raise NotFoundError("Leave has not been configured yet.",
                                code="policy_missing")
        report = year_end.run(policy=policy, dry_run=False)
        return Response({"report": str(report),
                         "lapsed": report.lapsed, "converted": report.converted,
                         "carried": report.carried,
                         "exceptions": report.exceptions})


@extend_schema(tags=["leave"])
class CalendarForYearView(APIView):
    """GET /leave/calendar/<year>   the calendar in force, for the client."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    @extend_schema(responses=s.CalendarSerializer,
                   summary="The published calendar in force")
    def get(self, request, year):
        cal = balance_selectors.published_calendar(year)
        if cal is None:
            raise NotFoundError(f"No published calendar for {year}.",
                                code="calendar_missing")
        return Response(s.CalendarSerializer(cal).data)
