"""HTTP layer: parse, scope, delegate, serialise; module grant first, then the permission."""
from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.domain import categories as cat
from modules.leave.selectors import balances as balance_reads
from modules.leave.selectors import configuration as config_reads
from modules.leave.selectors import scoping
from modules.leave.services import (
    applications,
    calendar,
    configuration,
    documents,
    readiness,
    records,
    resumptions,
    substitutes,
    workflow,
)

MODULE = HasModuleGrant("leave")


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(request, name, default=None):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a whole number.", code="invalid_filter") from exc


def _year(request) -> int:
    year = _int_param(request, "year", timezone.localdate().year)
    if not 2000 <= year <= 2100:
        raise BadRequestError("year must be between 2000 and 2100.", code="invalid_filter")
    return year


def _people(user_ids) -> dict:
    return directory.get_users(sorted(set(user_ids)))


def _valid(serializer_class, data):
    ser = serializer_class(data=data)
    ser.is_valid(raise_exception=True)
    return ser.validated_data


def _detail(req) -> Response:
    return Response(s.LeaveRequestDetailSerializer(req).data)


# -- employee ---------------------------------------------------------------------
class OverviewView(APIView):
    """EL-UC-012: balances for the year, and what this employee may apply for."""

    permission_classes = [MODULE, HasPermission("leave.balance.view")]

    @extend_schema(responses=s.OverviewSerializer,
                   parameters=[OpenApiParameter("year", int, required=False)])
    def get(self, request):
        actor, year = _actor(request), _year(request)
        policy = configuration.current_policy(required=False)
        person = directory.get_users([actor.user_id]).get(actor.user_id)
        options = [] if policy is None else [
            {"category": c, "label": cat.LABELS[c], "substitute": policy.rule(c).substitute,
             "evidence_min_days": policy.rule(c).evidence_min_days,
             "half_day": cat.get(c).half_day, "extendable": cat.get(c).extendable}
            for c in cat.ALL if cat.applicable(c, actor.kind)]
        return Response(s.OverviewSerializer({
            "year": year, "kind": actor.kind,
            "department": getattr(person, "department", "") or "",
            "balances": balance_reads.overview(actor.user_id, actor.kind, year),
            "categories": options, "configured": policy is not None}).data)


class LedgerView(generics.ListAPIView):
    serializer_class = s.LedgerSerializer
    permission_classes = [MODULE, HasPermission("leave.balance.view")]

    @extend_schema(parameters=[OpenApiParameter("year", int, required=False)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return balance_reads.ledger(0).none()
        return balance_reads.ledger(_actor(self.request).user_id,
                                    _int_param(self.request, "year"))


class EffectiveCalendarView(APIView):
    """The published holidays and RH dates, and the vacation periods, that validation will use."""

    permission_classes = [MODULE, HasPermission("leave.request.create", "leave.calendar.update")]

    @extend_schema(responses=s.EffectiveCalendarSerializer,
                   parameters=[OpenApiParameter("year", int, required=False)])
    def get(self, request):
        year = _year(request)
        cal = config_reads.published_calendar(year)
        vacations = config_reads.vacations(year)
        return Response(s.EffectiveCalendarSerializer({
            "year": year, "published": cal is not None,
            "holidays": list(cal.holidays.all()) if cal else [],
            "vacations": list(vacations)}).data)


class EmployeeSearchView(APIView):
    """Colleagues to nominate as a substitute; names only, never their leave."""

    permission_classes = [MODULE, HasPermission("leave.request.create", "leave.record.view")]
    throttle_scope = "directory_search"

    @extend_schema(responses=s.PersonSerializer(many=True),
                   parameters=[OpenApiParameter("q", str, required=False)])
    def get(self, request):
        q = (request.query_params.get("q") or "").strip()[:60]
        me = _actor(request).user_id
        rows = [p for p in directory.search_employees(q, limit=20) if p.user_id != me]
        return Response(s.PersonSerializer(rows, many=True).data)


class RequestListView(APIView):
    """EL-UC-001 (POST) and the employee's own history (GET)."""

    permission_classes = [MODULE, HasPermission("leave.request.view", "leave.request.create")]

    @extend_schema(responses=s.LeaveRequestSerializer(many=True),
                   parameters=[OpenApiParameter("year", int, required=False),
                               OpenApiParameter("status", str, required=False)])
    def get(self, request):
        qs = scoping.own_requests(_actor(request))
        year = _int_param(request, "year")
        if year:
            qs = qs.filter(leave_year=year)
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return Response(s.LeaveRequestSerializer(qs.order_by("-created_at", "-id")[:200],
                                                 many=True).data)

    @extend_schema(request=s.LeaveApplySerializer, responses={201: s.LeaveRequestDetailSerializer})
    def post(self, request):
        req = applications.submit(actor=_actor(request), data=_valid(s.LeaveApplySerializer,
                                                                     request.data))
        return Response(s.LeaveRequestDetailSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class RequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission(
        "leave.request.view", "leave.request.review", "leave.resumption.review",
        "leave.record.view", "leave.substitution.review")]

    @extend_schema(responses=s.LeaveRequestDetailSerializer)
    def get(self, request, pk: int):
        req = scoping.visible_requests(_actor(request)).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such leave request.")
        return _detail(req)


class RequestDocumentView(APIView):
    """EL-UC-013: a self-contained HTML document, to print or keep."""

    permission_classes = [MODULE, HasPermission("leave.request.export")]

    @extend_schema(responses={(200, "text/html"): str})
    def get(self, request, pk: int):
        req = scoping.visible_requests(_actor(request)).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such leave request.")
        response = HttpResponse(documents.render(req), content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="leave-{req.pk}.html"'
        response["Cache-Control"] = "private, no-store"
        return response


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.revoke")]

    @extend_schema(request=s.ReasonSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk: int):
        data = _valid(s.ReasonSerializer, request.data)
        return _detail(workflow.withdraw(request_id=pk, actor=_actor(request),
                                         reason=data["reason"]))


class CancellationView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.ReasonSerializer, responses={201: s.LeaveRequestDetailSerializer})
    def post(self, request, pk: int):
        data = _valid(s.ReasonSerializer, request.data)
        req = applications.request_cancellation(actor=_actor(request), leave_id=pk,
                                                reason=data["reason"])
        return Response(s.LeaveRequestDetailSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.ExtensionSerializer, responses={201: s.LeaveRequestDetailSerializer})
    def post(self, request, pk: int):
        req = applications.request_extension(actor=_actor(request), leave_id=pk,
                                             data=_valid(s.ExtensionSerializer, request.data))
        return Response(s.LeaveRequestDetailSerializer(req).data,
                        status=status.HTTP_201_CREATED)


class RenominateView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.NomineeSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk: int):
        data = _valid(s.NomineeSerializer, request.data)
        return _detail(substitutes.renominate(request_id=pk, actor=_actor(request),
                                              nominee_id=data["substitute_user_id"]))


class ResumptionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.request.create")]

    @extend_schema(request=s.ResumeSerializer, responses={201: s.ResumptionSerializer})
    def post(self, request, pk: int):
        data = _valid(s.ResumeSerializer, request.data)
        res = resumptions.submit(actor=_actor(request), leave_id=pk,
                                 resumption_date=data["resumption_date"], details=data["details"])
        return Response(s.ResumptionSerializer(res).data, status=status.HTTP_201_CREATED)


# -- substitute -------------------------------------------------------------------
class SubstitutionListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitution.review")]

    @extend_schema(responses=s.SubstitutionRequestSerializer(many=True))
    def get(self, request):
        rows = list(scoping.substitution_requests(_actor(request))[:100])
        return Response(s.SubstitutionRequestSerializer(
            rows, many=True, context={"people": _people(r.request.user_id for r in rows)}).data)


class SubstitutionRespondView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitution.review")]

    @extend_schema(request=s.RespondSerializer, responses=s.LeaveRequestSerializer)
    def post(self, request, pk: int):
        data = _valid(s.RespondSerializer, request.data)
        req = substitutes.respond(substitution_id=pk, accept=data["accept"],
                                  actor=_actor(request), remarks=data["remarks"])
        return Response(s.LeaveRequestSerializer(req).data)


# -- approvers --------------------------------------------------------------------
class QueueView(APIView):
    """The open tasks of the role being acted as; switching role switches the queue."""

    permission_classes = [MODULE, HasPermission("leave.request.review",
                                                "leave.resumption.review")]

    @extend_schema(responses=s.TaskSerializer(many=True))
    def get(self, request):
        rows = list(scoping.queue(_actor(request))[:200])
        return Response(s.TaskSerializer(
            rows, many=True, context={"people": _people(t.request.user_id for t in rows)}).data)


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(
        "leave.request.review", "leave.request.assign", "leave.request.approve",
        "leave.resumption.review")]

    @extend_schema(request=s.DecideSerializer, responses=s.LeaveRequestDetailSerializer)
    def post(self, request, pk: int):
        data = _valid(s.DecideSerializer, request.data)
        actor = _actor(request)
        if data["action"] == "review":
            res = resumptions.review(task_id=pk, actor=actor, remarks=data["remarks"])
            return _detail(res.leave)
        return _detail(workflow.decide(task_id=pk, action=data["action"], actor=actor,
                                       remarks=data["remarks"]))


# -- administration ---------------------------------------------------------------
class PolicyView(APIView):
    """EL-UC-014: saving writes a new revision that governs from that moment (BR-EL-030)."""

    permission_classes = [MODULE, HasPermission("leave.policy.update")]

    def _current(self):
        p = configuration.current_policy(required=False)
        if p is None:
            return {"revision_id": None, "rules": [], "weekend_days": [5, 6],
                    "max_backdate_days": 0}
        return {"revision_id": p.revision_id,
                "rules": [vars(r) for r in (p.rules[c] for c in cat.ALL if c in p.rules)],
                "weekend_days": sorted(p.weekend_days), "max_backdate_days": p.max_backdate_days}

    @extend_schema(responses=s.PolicySerializer)
    def get(self, request):
        return Response(s.PolicySerializer(self._current()).data)

    @extend_schema(request=s.PolicySerializer, responses=s.PolicySerializer)
    def post(self, request):
        data = _valid(s.PolicySerializer, request.data)
        configuration.save_policy(actor=_actor(request), rules=data["rules"],
                                  weekend_days=data["weekend_days"],
                                  max_backdate_days=data["max_backdate_days"], note=data["note"])
        return Response(s.PolicySerializer(self._current()).data, status=status.HTTP_201_CREATED)


class HierarchyView(APIView):
    """EL-UC-014: Unit Heads, higher-sanction routes, and the designations each may name."""

    permission_classes = [MODULE, HasPermission("leave.hierarchy.update")]

    def _current(self):
        from modules.leave.domain.authority import STEP_PERMISSIONS

        h = configuration.current_hierarchy(required=False)
        choices = {step: sorted(configuration.designations_with(STEP_PERMISSIONS[step]))
                   for step in ("unit_head", "establishment", "authority")}
        return {"revision_id": h.revision_id if h else None,
                "units": [vars(u) for u in h.units.values()] if h else [],
                "routes": [vars(r) for r in h.routes] if h else [],
                "choices": choices, "warnings": readiness.warnings()}

    @extend_schema(responses=s.HierarchySerializer)
    def get(self, request):
        return Response(s.HierarchySerializer(self._current()).data)

    @extend_schema(request=s.HierarchySerializer, responses=s.HierarchySerializer)
    def post(self, request):
        data = _valid(s.HierarchySerializer, request.data)
        configuration.save_hierarchy(actor=_actor(request), units=data["units"],
                                     routes=data["routes"], note=data["note"])
        return Response(s.HierarchySerializer(self._current()).data,
                        status=status.HTTP_201_CREATED)


class SlaView(APIView):
    """EL-UC-018."""

    permission_classes = [MODULE, HasPermission("leave.sla.update")]

    def _current(self):
        return {"rules": [vars(r) for r in configuration.current_sla().values()]}

    @extend_schema(responses=s.SlaSerializer)
    def get(self, request):
        return Response(s.SlaSerializer(self._current()).data)

    @extend_schema(request=s.SlaSerializer, responses=s.SlaSerializer)
    def post(self, request):
        data = _valid(s.SlaSerializer, request.data)
        configuration.save_sla(actor=_actor(request), rules=data["rules"], note=data["note"])
        return Response(s.SlaSerializer(self._current()).data, status=status.HTTP_201_CREATED)


class CalendarListView(APIView):
    """EL-UC-015: every version of a year's calendar, and a new draft."""

    permission_classes = [MODULE, HasPermission("leave.calendar.update")]

    @extend_schema(responses=s.CalendarSerializer(many=True),
                   parameters=[OpenApiParameter("year", int, required=False)])
    def get(self, request):
        rows = config_reads.calendars(_year(request))
        return Response(s.CalendarSerializer(rows, many=True).data)

    @extend_schema(request=s.CalendarCreateSerializer, responses={201: s.CalendarSerializer})
    def post(self, request):
        data = _valid(s.CalendarCreateSerializer, request.data)
        cal = calendar.start_draft(actor=_actor(request), year=data["year"])
        return Response(s.CalendarSerializer(cal).data, status=status.HTTP_201_CREATED)


class CalendarDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.update")]

    @extend_schema(request=s.CalendarEntriesSerializer, responses=s.CalendarSerializer)
    def put(self, request, pk: int):
        data = _valid(s.CalendarEntriesSerializer, request.data)
        cal = calendar.replace_entries(actor=_actor(request), calendar_id=pk,
                                       entries=data["holidays"])
        return Response(s.CalendarSerializer(cal).data)


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.publish")]

    @extend_schema(request=None, responses=s.CalendarSerializer)
    def post(self, request, pk: int):
        return Response(s.CalendarSerializer(
            calendar.publish(actor=_actor(request), calendar_id=pk)).data)


class VacationListView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.update")]

    @extend_schema(responses=s.VacationSerializer(many=True))
    def get(self, request):
        return Response(s.VacationSerializer(config_reads.vacations()[:200], many=True).data)

    @extend_schema(request=s.VacationSerializer, responses={201: s.VacationSerializer})
    def post(self, request):
        data = _valid(s.VacationSerializer, request.data)
        row = calendar.add_vacation(actor=_actor(request), **data)
        return Response(s.VacationSerializer(row).data, status=status.HTTP_201_CREATED)


class VacationDetailView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.update")]

    @extend_schema(responses={204: None})
    def delete(self, request, pk: int):
        calendar.remove_vacation(actor=_actor(request), vacation_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecordView(APIView):
    """EL-UC-017: one employee's year — balances, requests and every ledger entry."""

    permission_classes = [MODULE, HasPermission("leave.record.view")]

    @extend_schema(responses=s.RecordSerializer,
                   parameters=[OpenApiParameter("user_id", int, required=True),
                               OpenApiParameter("year", int, required=False)])
    def get(self, request):
        uid = _int_param(request, "user_id")
        if uid is None:
            raise BadRequestError("Choose an employee (user_id).", code="invalid_filter")
        year = _year(request)
        person = directory.get_users([uid]).get(uid)
        kind = getattr(person, "kind", "") or ""
        qs = scoping.records_for(_actor(request)).filter(user_id=uid, leave_year=year)
        return Response(s.RecordSerializer({
            "user_id": uid, "year": year, "person": person,
            "balances": balance_reads.overview(uid, kind, year),
            "requests": list(qs.order_by("-created_at")[:200]),
            "ledger": list(balance_reads.ledger(uid, year)[:500])}).data)


class OfflineRecordView(APIView):
    permission_classes = [MODULE, HasPermission("leave.record.import")]

    @extend_schema(request=s.OfflineRecordSerializer, responses={201: s.LeaveRequestSerializer})
    def post(self, request):
        req = records.record_offline(actor=_actor(request),
                                     data=_valid(s.OfflineRecordSerializer, request.data))
        return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AdjustmentView(APIView):
    permission_classes = [MODULE, HasPermission("leave.record.update")]

    @extend_schema(request=s.AdjustmentSerializer, responses={201: s.LedgerSerializer})
    def post(self, request):
        data = _valid(s.AdjustmentSerializer, request.data)
        entry = records.adjust(actor=_actor(request), **data)
        return Response(s.LedgerSerializer(entry).data, status=status.HTTP_201_CREATED)


class YearEndView(APIView):
    permission_classes = [MODULE, HasPermission("leave.record.view")]

    @extend_schema(responses=s.YearEndRunSerializer(many=True))
    def get(self, request):
        return Response(s.YearEndRunSerializer(config_reads.year_end_runs()[:20], many=True).data)


class ReadinessView(APIView):
    permission_classes = [MODULE, HasPermission("leave.policy.update", "leave.record.view")]

    @extend_schema(responses=s.ReadinessSerializer)
    def get(self, request):
        unmet = readiness.unmet()
        return Response(s.ReadinessSerializer({"ready": not unmet, "unmet": unmet,
                                               "warnings": readiness.warnings()}).data)

