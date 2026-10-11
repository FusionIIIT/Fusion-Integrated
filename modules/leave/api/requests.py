"""The employee's own leave: apply, inspect, withdraw, cancel, extend, resume.

`user_id` is never read from the body on these paths; it comes from the
credential, or one employee could act on another's leave. Where a colleague's
data is legitimately in view (an approver reading a request), that arrives
through `records.py` behind `leave.request.view`.
"""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csv as csv_export
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveSubstituteAssignment
from modules.leave.selectors import leave as sel
from modules.leave.services import applications as app_service
from modules.leave.services import resumption as resumption_service

MODULE = HasModuleGrant("leave")
P_SELF = "leave.request.view_self"
P_APPLY = "leave.request.create"
P_WITHDRAW = "leave.request.delete"
P_VIEW = "leave.request.view"


def _actor(request):
    return getattr(request, "principal", None)


def _request_payload(request) -> dict:
    data = s.LeaveRequestSerializer(request).data
    data["history"] = s.LeaveTransitionSerializer(
        request.transitions.all()[:50], many=True).data
    return data


@extend_schema(request=s.ValidateLeaveSerializer, responses={200: dict})
class LeaveValidateView(APIView):
    """EL-UC-001 M4 — validate a would-be application before submitting it."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request):
        payload = s.ValidateLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        check = app_service.assess(actor=_actor(request), **payload.validated_data)
        return Response({
            "is_valid": check["is_valid"],
            "chargeable_days": str(check["chargeable_days"]),
            "available_days": str(check["available_days"]),
            "leave_year": check["leave_year"],
            "employee_kind": check["employee_kind"],
            "charged": check["charged"],
            "skipped": check["skipped"],
            "failures": [{"code": f.code, "message": f.message, "details": f.details}
                         for f in check["failures"]],
        })


@extend_schema(request=s.ApplyLeaveSerializer,
               responses={201: s.LeaveRequestSerializer})
class LeaveApplyView(APIView):
    """EL-UC-001 — create and submit one leave application."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request):
        payload = s.ApplyLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = app_service.submit_new(actor=_actor(request),
                                       **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LeaveRequestSerializer(many=True))
class MyLeaveRequestsView(APIView):
    """EL-UC-012 — the caller's own requests, newest first."""

    permission_classes = [MODULE, HasPermission(P_SELF, P_VIEW)]

    def get(self, request):
        rows = (sel.requests_for(_actor(request))
                .filter(user_id=_actor(request).user_id)
                .order_by("-created_at")[:200])
        return Response({"results": s.LeaveRequestSerializer(rows, many=True).data})


@extend_schema(responses=s.LeaveRequestSerializer)
class LeaveRequestDetailView(APIView):
    """One request with its history, if the caller may see it."""

    permission_classes = [MODULE, HasPermission(P_SELF, P_VIEW)]

    def get(self, request, pk: int):
        leave = sel.request_for(_actor(request), pk)
        from core.api.exceptions import NotFoundError

        if leave is None:
            raise NotFoundError("No such leave request.")
        return Response(_request_payload(leave))


@extend_schema(request=s.WithdrawSerializer, responses=s.LeaveRequestSerializer)
class LeaveWithdrawView(APIView):
    """EL-UC-007 — withdraw a pending request, effective immediately."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        payload = s.WithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = app_service.withdraw(actor=_actor(request), request_id=pk,
                                     reason=payload.validated_data.get("reason", ""))
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(request=s.CancellationSerializer,
               responses={201: s.LeaveRequestSerializer})
class LeaveCancellationView(APIView):
    """EL-UC-008 — request pre-start cancellation of an approved leave."""

    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    def post(self, request, pk: int):
        payload = s.CancellationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = app_service.request_cancellation(
            actor=_actor(request), request_id=pk,
            note=payload.validated_data.get("note", ""))
        return Response(s.LeaveRequestSerializer(leave).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.ExtensionSerializer,
               responses={201: s.LeaveRequestSerializer})
class LeaveExtensionView(APIView):
    """EL-UC-009 — ask for additional time on ongoing EL/COL/VL."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request, pk: int):
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = app_service.request_extension(actor=_actor(request), request_id=pk,
                                              **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.ResumptionSubmitSerializer,
               responses={201: s.LeaveResumptionSerializer})
class LeaveResumptionView(APIView):
    """EL-UC-010 — declare the actual return to duty for review."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request, pk: int):
        payload = s.ResumptionSubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = resumption_service.submit(actor=_actor(request), request_id=pk,
                                        **payload.validated_data)
        return Response(s.LeaveResumptionSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class MyLeaveBalancesView(APIView):
    """EL-UC-012 — current balances for the caller's own account."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def get(self, request):
        year = request.query_params.get("leave_year")
        rows = sel.balances_of(_actor(request).user_id,
                               int(year) if year else None)
        return Response({"results": s.LeaveBalanceSerializer(rows, many=True).data})


@extend_schema(responses=s.LedgerEntrySerializer(many=True))
class MyLeaveLedgerView(APIView):
    """Why the balance is what it is: the account's own transactions."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def get(self, request):
        rows = sel.ledger_for(_actor(request).user_id)[:200]
        return Response({"results": s.LedgerEntrySerializer(rows, many=True).data})


class LeaveApplicationPrintView(APIView):
    """EL-UC-013 — a printable/exportable representation of the application."""

    permission_classes = [MODULE, HasPermission(P_SELF, P_VIEW)]

    @extend_schema(responses={200: str},
                   description="CSV representation of one leave application.")
    def get(self, request, pk: int):
        from core.api.exceptions import NotFoundError

        leave = sel.request_for(_actor(request), pk)
        if leave is None:
            raise NotFoundError("No such leave request.")
        header = ["Field", "Value"]
        rows = [
            ("Reference", leave.reference),
            ("Kind", leave.get_kind_display()),
            ("Category", leave.get_category_display()),
            ("Applicant user id", leave.user_id),
            ("Period from", leave.period_from),
            ("Period to", leave.period_to),
            ("Half", leave.get_half_display()),
            ("Chargeable days", leave.days_counted),
            ("Purpose", leave.purpose),
            ("Station leave", leave.station_leave),
            ("Status", leave.get_status_display()),
            ("Recommendation", leave.recommendation),
            ("Source", leave.get_source_display()),
            ("Decision note", leave.decision_note),
            ("Evidence reference", leave.evidence_reference),
            ("Submitted at", leave.submitted_at),
            ("Decided at", leave.decided_at),
        ]
        history = [
            (f"History {t.at}",
             f"{t.from_status} -> {t.to_status} ({t.action}) by u{t.actor_user_id}")
            for t in leave.transitions.all()[:50]
        ]
        return csv_export.stream(filename=f"{leave.reference or leave.pk}.csv",
                                 header=header, rows=[*rows, *history])


@extend_schema(responses=s.SubstituteAssignmentSerializer(many=True))
class MySubstitutionsView(APIView):
    """EL-UC-002 — responsibility requests nominated to the caller.

    No permission beyond module access: the nomination is the authority, and a
    substitute is any employee (BR-EL-014).
    """

    permission_classes = [MODULE]

    def get(self, request):
        rows = sel.substitute_assignments_for(_actor(request))
        return Response({"results": s.SubstituteAssignmentSerializer(rows, many=True).data})


@extend_schema(request=s.SubstituteRespondSerializer,
               responses=s.SubstituteAssignmentSerializer)
class SubstituteRespondView(APIView):
    """EL-UC-002 M3 — accept or decline; a decline closes the consent gate."""

    permission_classes = [MODULE]

    def post(self, request, pk: int):
        payload = s.SubstituteRespondSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = app_service.respond_to_substitute(
            actor=_actor(request), assignment_id=pk,
            accept=payload.validated_data["accept"],
            note=payload.validated_data.get("note", ""))
        return Response(s.SubstituteAssignmentSerializer(assignment).data)


@extend_schema(request=s.NominateReplacementSerializer,
               responses=s.SubstituteAssignmentSerializer)
class NominateReplacementView(APIView):
    """EL-UC-019 — recover from a decline with one replacement nominee."""

    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request, pk: int):
        payload = s.NominateReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        assignment = app_service.nominate_replacement(
            actor=_actor(request), request_id=pk,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        return Response(s.SubstituteAssignmentSerializer(assignment).data)


@extend_schema(responses={200: dict})
class MyLeaveSummaryView(APIView):
    """What the employee's own landing screen needs, in one call."""

    permission_classes = [MODULE, HasPermission(P_SELF)]

    def get(self, request):
        actor = _actor(request)
        rows = sel.requests_for(actor).filter(user_id=actor.user_id)
        pending = rows.filter(status__in=list(sm.PENDING)).count()
        return Response({
            "balances": s.LeaveBalanceSerializer(
                sel.balances_of(actor.user_id), many=True).data,
            "pending_requests": pending,
            "substitutions_awaiting_response": LeaveSubstituteAssignment.objects
            .filter(nominee_user_id=actor.user_id, status="nominated").count(),
            "resumptions_pending": sel.resumptions_for(actor)
            .filter(outcome="pending").count(),
            "recent_requests": s.LeaveRequestSerializer(
                rows.order_by("-created_at")[:10], many=True).data,
        })


__all__ = [
    "LeaveApplicationPrintView", "LeaveApplyView", "LeaveCancellationView",
    "LeaveExtensionView", "LeaveRequestDetailView", "LeaveResumptionView",
    "LeaveValidateView", "LeaveWithdrawView", "MyLeaveBalancesView",
    "MyLeaveLedgerView", "MyLeaveRequestsView", "MyLeaveSummaryView",
    "MySubstitutionsView", "NominateReplacementView", "SubstituteRespondView",
]
