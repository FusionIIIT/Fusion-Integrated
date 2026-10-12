"""HTTP layer: parse, scope, delegate, serialise.

Reads take their queryset from `selectors.scoping`, so authorisation is
never re-derived per endpoint: a row you may not see is a 404, not a 403.
Writes go straight to the services, which own permission, identity and the
state machine — the view only parses and translates.
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.leave.api import serializers as s
from modules.leave.models import LeaveYearRun
from modules.leave.selectors import scoping
from modules.leave.services import (
    applications,
    authz,
    balances,
    calendar as calendar_service,
    decisions,
    hierarchy,
    notifications,
    policy as policy_service,
    records,
)
from modules.leave.services.policy import EDITABLE

MODULE = HasModuleGrant("leave")()


def _perm(*codes, require_all: bool = False):
    """An instance, because `get_permissions` must hand DRF instances —
    placement gets that for free via `permission_classes`."""
    return HasPermission(*codes, require_all=require_all)()

P_VIEW_SELF = "leave.request.view_self"
P_VIEW = "leave.request.view"
P_CREATE = "leave.request.create"
P_BALANCE_VIEW = "leave.balance.view"
P_TYPE_MANAGE = "leave.type.manage"
P_CALENDAR_MANAGE = "leave.calendar.manage"
P_RECORD_MANAGE = "leave.record.manage"
P_SLA_MANAGE = "leave.sla.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc


def _people_for(*requests_rows) -> dict:
    ids: set[int] = set()
    for row in requests_rows:
        if row is None:
            continue
        ids.add(row.user_id)
        if row.substitute_user_id:
            ids.add(row.substitute_user_id)
    return directory.get_users(sorted(ids))


def _detail(obj, request, code=status.HTTP_200_OK) -> Response:
    data = s.LeaveRequestSerializer(
        obj, context={"actor": _actor(request),
                      "people": _people_for(obj)}).data
    return Response(data, status=code)


def _list_payload(qs, request) -> Response:
    rows = list(qs[:200])
    ids: set[int] = set()
    for row in rows:
        ids.add(row.user_id)
        if row.substitute_user_id:
            ids.add(row.substitute_user_id)
    data = s.LeaveRequestSerializer(
        rows, many=True,
        context={"actor": _actor(request),
                 "people": directory.get_users(sorted(ids))}).data
    return Response({"count": qs.count(), "results": data})


# -- requests ---------------------------------------------------------------
class RequestListView(generics.GenericAPIView):
    """GET: scoped list. POST: a new application (EL-UC-001)."""

    serializer_class = s.LeaveRequestSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE, _perm(P_CREATE)]
        return [MODULE, _perm(P_VIEW_SELF, P_VIEW)]

    def get_queryset(self):
        actor = _actor(self.request)
        qs = scoping.requests_for(actor)
        params = self.request.query_params
        if params.get("mine"):
            qs = qs.filter(user_id=getattr(actor, "user_id", None))
        for field in ("category", "status"):
            if params.get(field):
                qs = qs.filter(**{field: params[field]})
        year = _int_param(params, "year")
        if year is not None:
            qs = qs.filter(year=year)
        user_id = _int_param(params, "user_id")
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        return qs.order_by("-created_at")

    def get(self, request, *args, **kwargs):
        return _list_payload(self.get_queryset(), request)

    def post(self, request, *args, **kwargs):
        payload = s.SubmitSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = applications.submit(actor=_actor(request),
                                  **dict(payload.validated_data))
        return _detail(obj, request, status.HTTP_201_CREATED)


class RequestDetailView(APIView):
    def get(self, request, pk):
        obj = scoping.request_or_404(_actor(request), pk)
        return _detail(obj, request)


class RequestHistoryView(APIView):
    def get(self, request, pk):
        obj = scoping.request_or_404(_actor(request), pk)
        rows = obj.events.all()
        return Response(s.LeaveEventSerializer(rows, many=True).data)


class RequestWithdrawView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        return _detail(applications.withdraw(_actor(request), obj), request)


class RequestCancellationView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.ReasonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        derived = applications.request_cancellation(
            _actor(request), obj, **dict(payload.validated_data))
        return _detail(derived, request, status.HTTP_201_CREATED)


class RequestExtensionView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        derived = applications.request_extension(
            _actor(request), obj, **dict(payload.validated_data))
        return _detail(derived, request, status.HTTP_201_CREATED)


class RequestResumptionView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.ResumptionFileSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        resumption = applications.submit_resumption(
            _actor(request), obj, **dict(payload.validated_data))
        return Response(s.LeaveResumptionSerializer(resumption).data,
                        status=status.HTTP_201_CREATED)


class RequestSubstituteNominateView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.NominateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = applications.nominate_substitute(
            _actor(request), obj,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        return _detail(out, request)


class SubstituteRespondView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.SubstituteRespondSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = decisions.substitute_respond(
            _actor(request), obj, **dict(payload.validated_data))
        return _detail(out, request)


class RequestReviewView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.ReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = decisions.unit_head_review(_actor(request), obj,
                                         **dict(payload.validated_data))
        return _detail(out, request)


class RequestRouteView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.NoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = decisions.establishment_route(_actor(request), obj,
                                            **dict(payload.validated_data))
        return _detail(out, request)


class RequestSanctionView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.SanctionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = decisions.sanction(_actor(request), obj,
                                 **dict(payload.validated_data))
        return _detail(out, request)


class RequestAnnotateView(APIView):
    def post(self, request, pk):
        obj = scoping.request_for_action(pk)
        payload = s.AnnotateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = records.annotate(_actor(request), obj,
                               note=payload.validated_data["note"])
        return _detail(out, request)


class ResumptionReviewView(APIView):
    def post(self, request, pk):
        from modules.leave.models import LeaveResumption

        actor = _actor(request)
        resumption = LeaveResumption.objects.filter(pk=pk).first()
        if resumption is None:
            from core.api.exceptions import NotFoundError
            raise NotFoundError("Resumption not found.", code="not_found")
        # Scope through the request the resumption belongs to, so a foreign
        # id is a 404 before any permission question arises.
        scoping.request_or_404(actor, resumption.request_id)
        payload = s.ResumptionReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        out = decisions.review_resumption(actor, resumption,
                                          **dict(payload.validated_data))
        return Response(s.LeaveResumptionSerializer(out).data)


# -- tasks, balances, notifications ----------------------------------------
class TaskListView(APIView):
    def get(self, request):
        return _list_payload(scoping.tasks_for(_actor(request)), request)


class BalanceListView(APIView):
    def get(self, request):
        actor = _actor(request)
        target = _int_param(request.query_params, "user_id")
        if target is not None and target != getattr(actor, "user_id", None):
            authz.require(actor, P_BALANCE_VIEW)
        year = _int_param(request.query_params, "year")
        year = year if year is not None else policy_service.current_leave_year()
        person_id = target if target is not None else getattr(actor, "user_id",
                                                              None)
        if person_id is None:
            return Response({"count": 0, "results": []})
        balances.ensure_year(person_id, year)
        rows = scoping.balances_rows_for(actor, target).filter(year=year)
        return Response({"count": rows.count(),
                         "results": s.BalanceSerializer(rows, many=True).data,
                         "year": year})


class BalanceLedgerView(APIView):
    def get(self, request):
        actor = _actor(request)
        target = _int_param(request.query_params, "user_id")
        if target is not None and target != getattr(actor, "user_id", None):
            authz.require(actor, P_BALANCE_VIEW)
        person_id = target if target is not None else getattr(actor, "user_id",
                                                              None)
        if person_id is None:
            return Response({"count": 0, "results": []})
        from modules.leave.models import LeaveAccountTransaction
        rows = (LeaveAccountTransaction.objects
                .filter(user_id=person_id).order_by("-at")[:200])
        data = [{"id": r.id, "category": r.category, "year": r.year,
                 "kind": r.kind, "days": r.days, "request": r.request_id,
                 "note": r.note, "at": r.at} for r in rows]
        return Response({"count": len(data), "results": data})


class NotificationListView(APIView):
    def get(self, request):
        rows = scoping.notifications_for(_actor(request))[:50]
        return Response(s.NotificationSerializer(rows, many=True).data)


class NotificationReadView(APIView):
    def post(self, request):
        payload = s.MarkReadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        updated = notifications.mark_read(
            _actor(request), payload.validated_data.get("ids") or None)
        return Response({"marked": updated})


# -- calendars, policy, administration -------------------------------------
class CalendarView(APIView):
    def get(self, request):
        authz.require(request.principal, P_VIEW_SELF)
        return Response(calendar_service.calendar_payload())


class CalendarListView(generics.GenericAPIView):
    serializer_class = s.CalendarWriteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE, _perm(P_CALENDAR_MANAGE)]
        return [MODULE, _perm(P_CALENDAR_MANAGE)]

    def get(self, request):
        from modules.leave.models import HolidayCalendar
        rows = HolidayCalendar.objects.all()[:50]
        data = [{"id": c.id, "title": c.title, "academic_year": c.academic_year,
                 "status": c.status, "published_at": c.published_at,
                 "holidays": c.holidays.count()} for c in rows]
        return Response(data)

    def post(self, request):
        payload = s.CalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        calendar = calendar_service.create_calendar(
            _actor(request), **dict(payload.validated_data))
        return Response({"id": calendar.id, "status": calendar.status},
                        status=status.HTTP_201_CREATED)


class CalendarPublishView(APIView):
    def post(self, request, pk):
        calendar = calendar_service.publish_calendar(_actor(request), pk)
        return Response({"id": calendar.id, "status": calendar.status})


class VacationListView(generics.GenericAPIView):
    serializer_class = s.VacationWriteSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE, _perm(P_CALENDAR_MANAGE)]
        return [MODULE, _perm(P_VIEW_SELF)]

    def get(self, request):
        from modules.leave.models import VacationPeriod
        rows = VacationPeriod.objects.all()
        data = [{"id": v.id, "name": v.name, "academic_year": v.academic_year,
                 "start_date": v.start_date, "end_date": v.end_date,
                 "source_ref": v.source_ref} for v in rows]
        return Response(data)

    def post(self, request):
        payload = s.VacationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = calendar_service.upsert_vacation(_actor(request),
                                               dict(payload.validated_data))
        return Response({"id": row.id}, status=status.HTTP_201_CREATED)


class PolicyView(APIView):
    def get(self, request):
        authz.require(request.principal, P_VIEW_SELF)
        return Response(s.PolicySerializer(policy_service.current_policy()).data)

    def put(self, request):
        payload = s.PolicySerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        data = {k: v for k, v in payload.validated_data.items()
                if k in EDITABLE}
        policy = policy_service.update_policy(_actor(request), data)
        return Response(s.PolicySerializer(policy).data)


class OrgUnitListView(generics.GenericAPIView):
    serializer_class = s.OrgUnitSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE, _perm(P_TYPE_MANAGE)]
        return [MODULE, _perm(P_VIEW_SELF)]

    def get(self, request):
        from modules.leave.models import OrganizationalUnit
        rows = OrganizationalUnit.objects.all()
        return Response(s.OrgUnitSerializer(rows, many=True).data)

    def post(self, request):
        payload = s.OrgUnitWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        unit = hierarchy.configure_unit(_actor(request),
                                        dict(payload.validated_data))
        return Response(s.OrgUnitSerializer(unit).data,
                        status=status.HTTP_201_CREATED)


class OrgUnitDetailView(APIView):
    def put(self, request, pk):
        payload = s.OrgUnitWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        data["id"] = pk
        unit = hierarchy.configure_unit(_actor(request), data)
        return Response(s.OrgUnitSerializer(unit).data)


class AuthorityListView(generics.GenericAPIView):
    serializer_class = s.AuthoritySerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE, _perm(P_TYPE_MANAGE)]
        return [MODULE, _perm(P_VIEW_SELF)]

    def get(self, request):
        from modules.leave.models import AuthorityAssignment
        rows = AuthorityAssignment.objects.all()
        return Response(s.AuthoritySerializer(rows, many=True).data)

    def post(self, request):
        payload = s.AuthorityWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = hierarchy.configure_authority(_actor(request),
                                            dict(payload.validated_data))
        return Response(s.AuthoritySerializer(row).data,
                        status=status.HTTP_201_CREATED)


class AuthorityDetailView(APIView):
    def delete(self, request, pk):
        hierarchy.remove_authority(_actor(request), pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SlaView(APIView):
    def get(self, request):
        from modules.leave.models import SlaThreshold
        rows = SlaThreshold.objects.all().order_by("task_class")
        return Response(s.SlaThresholdSerializer(rows, many=True).data)

    def put(self, request):
        authz.require(request.principal, P_SLA_MANAGE)
        payload = s.SlaWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        from modules.leave.models import SlaThreshold
        out = []
        for item in payload.validated_data["thresholds"]:
            row, _ = SlaThreshold.objects.update_or_create(
                task_class=item["task_class"],
                defaults={"reminder_hours": item["reminder_hours"],
                          "escalation_hours": item["escalation_hours"],
                          "escalation_user_id": item["escalation_user_id"]})
            out.append(row)
        return Response(s.SlaThresholdSerializer(out, many=True).data)


class EmployeeSearchView(APIView):
    """Picker for substitutes and assignments — directory search behind this
    module's own gates, never a raw cross-module call from the client."""

    def get_permissions(self):
        return [MODULE, _perm(P_CREATE, P_RECORD_MANAGE)]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        kind = request.query_params.get("kind") or None
        rows = directory.search(q=q, kind=kind, limit=25)
        return Response([
            {"user_id": p.user_id, "username": p.username,
             "display_name": p.display_name, "kind": p.kind,
             "department": p.department}
            for p in rows
        ])


class OfflineLeaveView(APIView):
    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = applications.record_offline(_actor(request),
                                          **dict(payload.validated_data))
        return _detail(obj, request, status.HTTP_201_CREATED)


class AdjustBalanceView(APIView):
    def post(self, request):
        payload = s.AdjustBalanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        txn = records.adjust_balance(_actor(request),
                                     **dict(payload.validated_data))
        return Response({"id": txn.id, "category": txn.category,
                         "year": txn.year, "days": txn.days,
                         "kind": txn.kind},
                        status=status.HTTP_201_CREATED)


class YearEndStatusView(APIView):
    def get(self, request):
        rows = LeaveYearRun.objects.all()[:5]
        return Response([{"year": r.year, "processed_at": r.processed_at,
                          "report": r.report} for r in rows])
