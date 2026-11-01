"""HTTP layer: parse, scope, delegate, serialise.

Every view takes its queryset from the selectors, so authorisation is never
re-derived per endpoint and a row outside your scope is simply absent, which is
why the detail views 404 rather than 403 (BR-EL-036).
"""
from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.domain import categories as cat
from modules.leave.models import HolidayCalendar, SlaThreshold
from modules.leave.selectors import accounts as account_selector
from modules.leave.selectors import config as config_selector
from modules.leave.selectors import requests as request_selector
from modules.leave.selectors import scoping
from modules.leave.services import config as config_service
from modules.leave.services import facts, reviews
from modules.leave.services import records as record_service
from modules.leave.services import requests as request_service
from modules.leave.services import substitutes as substitute_service

MODULE = HasModuleGrant("leave")

P_REQUEST_VIEW = "leave.request.view"
P_REQUEST_CREATE = "leave.request.create"
P_REQUEST_DELETE = "leave.request.delete"
P_REQUEST_REVIEW = "leave.request.review"
P_BALANCE_VIEW = "leave.balance.view"
P_EXPORT = "leave.application.export"
P_CALENDAR_VIEW = "leave.calendar.view"
P_CALENDAR_PUBLISH = "leave.calendar.publish"
P_POLICY_UPDATE = "leave.policy.update"
P_THRESHOLD_UPDATE = "leave.threshold.update"
P_RECORD_VIEW = "leave.record.view"
P_RECORD_UPDATE = "leave.record.update"
P_RESUMPTION_CREATE = "leave.resumption.create"
P_RESUMPTION_REVIEW = "leave.resumption.review"
P_SUBSTITUTE = "leave.substitute.review"
P_CANCELLATION = "leave.cancellation.create"
P_EXTENSION = "leave.extension.create"


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    """A non-integer filter is a 400, not a ValueError deep in the ORM."""
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc


def _row_or_404(actor, request_id: int):
    row = scoping.request_for(actor, request_id)
    if row is None:
        from core.api.exceptions import NotFoundError

        raise NotFoundError("No such leave request.")
    return row


class _Base(APIView):
    def get_serializer_context(self):
        return {"request": self.request, "actor": _actor(self.request)}


# -- Balances and history (EL-UC-012, EL-UC-013) ------------------------------
@extend_schema(responses=s.BalanceSerializer(many=True))
class MyBalancesView(_Base):
    permission_classes = [MODULE, HasPermission(P_BALANCE_VIEW)]

    def get(self, request):
        year = _int_param(request.query_params, "year") or timezone.localdate().year
        user_id = _actor(request).user_id
        payload = [{
            "category": category,
            "label": cat.LABELS[category],
            "entitlement": config_selector.entitlement(category),
            "balance": account_selector.balance(user_id=user_id, year=year,
                                                category=category),
            "committed": account_selector.committed(user_id=user_id, year=year,
                                                    category=category),
            "available": account_selector.available(user_id=user_id, year=year,
                                                    category=category),
        } for category in cat.CATEGORIES]
        ledger = [{"id": e.pk, "category": e.account.category,
                   "entry_type": e.entry_type, "days": e.days,
                   "reference": e.reference, "reason": e.reason,
                   "created_at": e.created_at}
                  for e in account_selector.ledger_for(user_id=user_id, year=year)]
        return Response({"year": year, "balances": payload, "ledger": ledger})


# -- Requests (EL-UC-001, EL-UC-007) ------------------------------------------
@extend_schema_view(
    get=extend_schema(operation_id="leave_requests_list",
                      responses=s.LeaveRequestSerializer(many=True)),
    post=extend_schema(operation_id="leave_requests_create",
                       request=s.LeaveRequestCreateSerializer,
                       responses={201: s.LeaveRequestSerializer}),
)
class RequestListCreateView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_VIEW)]

    def get(self, request):
        qs = scoping.requests_for(_actor(request))
        year = _int_param(request.query_params, "year")
        kind = request.query_params.get("kind")
        if year:
            qs = qs.filter(start_date__year=year)
        if kind:
            qs = qs.filter(kind=kind)
        return Response({"results": s.LeaveRequestSerializer(qs[:200], many=True).data})

    def post(self, request):
        payload = s.LeaveRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        row = request_service.apply_for_leave(
            actor=_actor(request),
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            purpose=data["purpose"],
            half=data.get("half", ""),
            evidence_note=data.get("evidence_note", ""),
            substitute_user_id=data.get("substitute_user_id"),
            station_leave={
                "required": data.get("station_leave_required", False),
                "place": data.get("station_leave_place", ""),
                "start": data.get("station_leave_start"),
                "end": data.get("station_leave_end"),
            },
        )
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(operation_id="leave_request_detail",
                      responses=s.LeaveRequestSerializer),
)
class RequestDetailView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_VIEW)]

    def get(self, request, pk: int):
        return Response(s.LeaveRequestSerializer(_row_or_404(_actor(request), pk)).data)


@extend_schema(responses=s.LeaveTransitionSerializer(many=True))
class RequestHistoryView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_VIEW)]

    def get(self, request, pk: int):
        row = _row_or_404(_actor(request), pk)
        rows = row.transitions.order_by("id")
        return Response({"results": s.TransitionSerializer(rows, many=True).data})


@extend_schema(request=s.LeaveWithdrawSerializer,
               responses={200: s.LeaveRequestSerializer})
class WithdrawView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_DELETE)]

    def post(self, request, pk: int):
        row = request_service.withdraw(
            actor=_actor(request), request_id=pk,
            reason=request.data.get("reason", ""),
            scope=scoping.requests_for(_actor(request)))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(request=s.CancellationRequestSerializer,
               responses={200: s.LeaveRequestSerializer})
class CancellationRequestView(_Base):
    permission_classes = [MODULE, HasPermission(P_CANCELLATION)]

    def post(self, request, pk: int):
        payload = s.CancellationRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = request_service.request_cancellation(
            actor=_actor(request), request_id=pk,
            reason=payload.validated_data.get("reason", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(request=s.ExtensionRequestSerializer,
               responses={201: s.LeaveRequestSerializer})
class ExtensionRequestView(_Base):
    permission_classes = [MODULE, HasPermission(P_EXTENSION)]

    def post(self, request, pk: int):
        payload = s.ExtensionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = request_service.request_extension(
            actor=_actor(request), request_id=pk, start_date=data["start_date"],
            end_date=data["end_date"], purpose=data["purpose"],
            substitute_user_id=data.get("substitute_user_id"))
        return Response(s.LeaveRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.ReplacementSerializer,
               responses={200: s.LeaveRequestSerializer})
class NominateReplacementView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_CREATE)]

    def post(self, request, pk: int):
        payload = s.ReplacementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        substitute_service.nominate_replacement(
            actor=_actor(request), request_id=pk,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        row = _row_or_404(_actor(request), pk)
        return Response(s.LeaveRequestSerializer(row).data)


# -- The office queue and decisions (EL-UC-003 to EL-UC-005) ------------------
@extend_schema(responses=s.LeaveRequestSerializer(many=True))
class QueueView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_REVIEW)]

    def get(self, request):
        rows = reviews.my_queue(_actor(request))[:200]
        return Response({"results": s.LeaveRequestSerializer(rows, many=True).data})


@extend_schema(request=s.LeaveStatusChangeSerializer,
               responses={200: s.LeaveRequestSerializer})
class DecisionView(_Base):
    permission_classes = [MODULE, HasPermission(
        P_REQUEST_REVIEW, "leave.request.approve")]

    def post(self, request, pk: int):
        payload = s.LeaveStatusChangeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        event = request.data.get("event", "")
        data = payload.validated_data
        row = reviews.decide(
            actor=_actor(request), request_id=pk, event=event,
            reason=data.get("reason", ""),
            recommendation=data.get("recommendation", ""),
            scope=scoping.requests_for(_actor(request)))
        return Response(s.LeaveRequestSerializer(row).data)


# -- Substitute responses (EL-UC-002, EL-UC-019) ------------------------------
@extend_schema(responses=s.SubstituteAssignmentSerializer(many=True))
class SubstituteRequestListView(_Base):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def get(self, request):
        rows = scoping.substitutes_for(_actor(request))
        state = request.query_params.get("state", "")
        if state:
            rows = rows.filter(state=state)
        return Response({"results": s.SubstituteAssignmentSerializer(rows, many=True).data})


@extend_schema(request=s.SubstituteResponseSerializer,
               responses={200: s.LeaveRequestSerializer})
class SubstituteResponseView(_Base):
    """`request_id` is the leave request the nomination hangs off."""

    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, request_id: int):
        payload = s.SubstituteResponseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = substitute_service.respond(
            actor=_actor(request), request_id=request_id,
            accept=payload.validated_data["accept"],
            reason=payload.validated_data.get("reason", ""))
        return Response(s.LeaveRequestSerializer(row).data)


# -- Resumption (EL-UC-010, EL-UC-011) ----------------------------------------
@extend_schema(request=s.ResumptionSerializer,
               responses={200: s.LeaveRequestSerializer})
class ResumptionSubmitView(_Base):
    permission_classes = [MODULE, HasPermission(P_RESUMPTION_CREATE)]

    def post(self, request, pk: int):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = reviews.submit_resumption(
            actor=_actor(request), request_id=pk,
            actual_date=payload.validated_data["actual_date"],
            notes=payload.validated_data.get("notes", ""))
        return Response(s.LeaveRequestSerializer(row).data)


@extend_schema(request=s.ResumptionSerializer,
               responses={200: s.LeaveRequestSerializer})
class ResumptionReviewView(_Base):
    permission_classes = [MODULE, HasPermission(P_RESUMPTION_REVIEW)]

    def post(self, request, pk: int):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = reviews.review_resumption(
            actor=_actor(request), request_id=pk,
            actual_date=payload.validated_data["actual_date"],
            notes=payload.validated_data.get("notes", ""),
            scope=scoping.requests_for(_actor(request)))
        return Response(s.LeaveRequestSerializer(row).data)


# -- Printable application (EL-UC-013) ----------------------------------------
@extend_schema(responses={200: str})
class ApplicationExportView(_Base):
    """A printable copy of one application (EL-UC-013)."""

    permission_classes = [MODULE, HasPermission(P_EXPORT)]

    def get(self, request, pk: int):
        row = _row_or_404(_actor(request), pk)
        lines = [
            "Fusion ERP - Employee Leave Management",
            f"Application: {row.pk} ({row.kind})",
            f"Leave category: {cat.LABELS[row.category]}",
            f"Period: {row.start_date} to {row.end_date} {row.half}".rstrip(),
            f"Days: {row.days_approved or row.days_requested}",
            f"Status: {row.status}",
            f"Purpose: {row.purpose}",
        ]
        if row.station_leave_required:
            lines.append(f"Station leave: {row.station_leave_place} "
                         f"{row.station_leave_start} to {row.station_leave_end}")
        return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


# -- Calendar (EL-UC-015) -----------------------------------------------------
@extend_schema(responses=s.HolidayCalendarSerializer)
class EffectiveCalendarView(_Base):
    permission_classes = [MODULE, HasPermission(P_CALENDAR_VIEW)]

    def get(self, request):
        year = _int_param(request.query_params, "year") or timezone.localdate().year
        calendar = (config_selector.effective_calendar()
                    or HolidayCalendar.objects.filter(year=year).first())
        if calendar is None:
            return Response({"year": year, "published": False, "days": []})
        return Response(s.HolidayCalendarSerializer(calendar).data)


@extend_schema(request=s.PublishCalendarSerializer,
               responses={201: s.HolidayCalendarSerializer})
class PublishCalendarView(_Base):
    permission_classes = [MODULE, HasPermission(P_CALENDAR_PUBLISH)]

    def post(self, request):
        payload = s.PublishCalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        calendar = config_service.publish_calendar(
            actor=_actor(request), year=data["year"], days=data["days"],
            effective_from=data.get("effective_from"), label=data.get("label", ""))
        return Response(s.HolidayCalendarSerializer(calendar).data,
                        status=status.HTTP_201_CREATED)


# -- Policy, hierarchy and vacation dates (EL-UC-014) -------------------------
@extend_schema(request=s.PolicySerializer, responses=s.PolicySerializer)
class PolicyView(_Base):
    permission_classes = [MODULE, HasPermission(P_POLICY_UPDATE)]

    def get(self, request):
        policy = config_selector.current_policy()
        return Response({
            "entitlements": {c: config_selector.entitlement(c) for c in cat.CATEGORIES},
            "substitute_categories": sorted(config_selector.substitute_categories()),
            "max_backdate_days": policy.max_backdate_days,
            "self_sanction_designation": policy.self_sanction_designation,
            "notes": policy.notes,
        })

    def put(self, request):
        payload = s.PolicySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        policy = config_service.update_policy(
            actor=_actor(request), entitlements=data.get("entitlements"),
            substitute_categories=data.get("substitute_categories"),
            max_backdate_days=data.get("max_backdate_days"),
            self_sanction_designation=data.get("self_sanction_designation"),
            notes=data.get("notes", ""))
        return Response({"entitlements": policy.entitlements,
                         "max_backdate_days": policy.max_backdate_days,
                         "self_sanction_designation": policy.self_sanction_designation})


@extend_schema(request=s.HierarchyStepWriteSerializer(many=True),
               responses=s.HierarchyStepSerializer(many=True))
class HierarchyView(_Base):
    permission_classes = [MODULE, HasPermission(P_POLICY_UPDATE)]

    def get(self, request):
        rows = config_selector.hierarchy_steps()
        return Response({"steps": [
            {"sequence": r.sequence, "kind": r.kind, "designation": r.designation,
             "categories": list(r.categories)} for r in rows]})

    def put(self, request):
        payload = s.HierarchyStepWriteSerializer(data=request.data, many=True)
        payload.is_valid(raise_exception=True)
        rows = config_service.replace_hierarchy(actor=_actor(request),
                                                steps=payload.validated_data)
        return Response({"steps": [
            {"sequence": r.sequence, "kind": r.kind, "designation": r.designation,
             "categories": list(r.categories or [])} for r in rows]})


@extend_schema(request=s.VacationPeriodSerializer,
               responses={201: s.VacationPeriodSerializer})
class VacationPeriodView(_Base):
    permission_classes = [MODULE, HasPermission(P_POLICY_UPDATE)]

    def post(self, request):
        payload = s.VacationPeriodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = config_service.add_vacation_period(
            actor=_actor(request), start_date=data["start_date"],
            end_date=data["end_date"], label=data.get("label", ""))
        return Response({"start_date": row.start_date, "end_date": row.end_date,
                         "label": row.label}, status=status.HTTP_201_CREATED)


# -- SLA thresholds (EL-UC-018) ----------------------------------------------
@extend_schema(responses=s.SlaThresholdSerializer(many=True))
class ThresholdView(_Base):
    permission_classes = [MODULE, HasPermission(P_THRESHOLD_UPDATE)]

    def get(self, request):
        rows = SlaThreshold.objects.order_by("task_class")
        return Response({"results": s.SlaThresholdSerializer(rows, many=True).data})

    @extend_schema(request=s.SlaThresholdWriteSerializer,
                   responses={200: s.SlaThresholdSerializer})
    def put(self, request):
        payload = s.SlaThresholdWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = config_service.set_threshold(
            actor=_actor(request), task_class=data["task_class"],
            reminder_hours=data["reminder_hours"],
            escalation_hours=data["escalation_hours"],
            escalation_designation=data.get("escalation_designation", ""))
        return Response(s.SlaThresholdSerializer(row).data)


# -- Records (EL-UC-016, EL-UC-017) -------------------------------------------
@extend_schema(responses=s.OfflineRecordSerializer(many=True))
class RecordListView(_Base):
    permission_classes = [MODULE, HasPermission(P_RECORD_VIEW)]

    def get(self, request):
        user_id = _int_param(request.query_params, "user_id")
        rows = record_service.offline_records(user_id=user_id)[:200]
        return Response({"results": [
            {"id": r.pk, "user_id": r.user_id, "category": r.category,
             "start_date": r.start_date, "end_date": r.end_date, "days": r.days,
             "sanction_reference": r.sanction_reference,
             "balance_synced": r.balance_synced} for r in rows]})


@extend_schema(request=s.OfflineRecordSerializer,
               responses={201: s.OfflineRecordSerializer})
class OfflineRecordView(_Base):
    permission_classes = [MODULE, HasPermission(P_RECORD_UPDATE)]

    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = record_service.record_offline(
            actor=_actor(request), user_id=data["user_id"], category=data["category"],
            start_date=data["start_date"], end_date=data["end_date"],
            days=data.get("days"), sanction_reference=data["sanction_reference"],
            evidence_note=data.get("evidence_note", ""),
            is_faculty=facts.is_faculty(data["user_id"]))
        return Response({"id": row.pk, "days": row.days,
                         "balance_synced": row.balance_synced},
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.BalanceAdjustmentSerializer,
               responses={201: s.BalanceAdjustmentSerializer})
class BalanceAdjustmentView(_Base):
    permission_classes = [MODULE, HasPermission(P_RECORD_UPDATE)]

    def post(self, request):
        payload = s.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = record_service.adjust_balance(
            actor=_actor(request), user_id=data["user_id"], category=data["category"],
            year=data["year"], days=data["days"], reason=data["reason"],
            reversal=data.get("reversal", False))
        return Response({"id": row.pk, "entry_type": row.entry_type,
                         "days": row.days}, status=status.HTTP_201_CREATED)


# -- Where I am in the queue --------------------------------------------------
@extend_schema(responses=s.QueueCountSerializer)
class MyQueueCountView(_Base):
    permission_classes = [MODULE, HasPermission(P_REQUEST_VIEW)]

    def get(self, request):
        actor = _actor(request)
        waiting = request_selector.designation_queue(scoping.designations(actor))
        return Response({"waiting": waiting.count()})
