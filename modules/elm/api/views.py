"""HTTP layer: parse, scope, delegate, serialise."""
from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.domain import categories as c
from modules.elm.domain import permissions as p
from modules.elm.domain import policy as policy_domain
from modules.elm.models import (
    CalendarVersion,
    OfflineLeaveRecord,
    PolicyVersion,
)
from modules.elm.selectors import config as config_sel
from modules.elm.selectors import ledger as ledger_sel
from modules.elm.selectors import scoping
from modules.elm.services import config as config_svc
from modules.elm.services import ledger as ledger_svc
from modules.elm.services import offline as offline_svc
from modules.elm.services import requests as request_svc
from modules.elm.services import resumption as resumption_svc
from modules.elm.services import workflow as workflow_svc

MODULE = HasModuleGrant("elm")


def _actor(request):
    return getattr(request, "principal", None)


def _names(user_ids):
    try:
        return directory.get_users([u for u in user_ids if u is not None])
    except IamUnavailable:
        return {}


def _ctx(rows, **extra):
    ids = set()
    for r in rows:
        ids.add(r.user_id)
        if r.substitute_user_id:
            ids.add(r.substitute_user_id)
    return {"names": _names(ids), **extra}


def _one(request, data, **extra):
    return Response(s.LeaveRequestSerializer(data, context=_ctx([data], **extra)).data)


def _valid(serializer_cls, request):
    ser = serializer_cls(data=request.data)
    ser.is_valid(raise_exception=True)
    return ser.validated_data


def _int_param(params, name):
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.", code="invalid_filter") from exc


class _List(generics.ListAPIView):
    serializer_class = s.LeaveRequestSerializer
    queue = False

    def get_serializer(self, *args, **kwargs):
        rows = args[0] if args else []
        kwargs["context"] = _ctx(rows, queue=self.queue)
        return self.serializer_class(*args, **kwargs)


# -- Employee ------------------------------------------------------------------
@extend_schema(request=s.LeaveInputSerializer, responses=s.LeaveRequestSerializer)
class RequestListView(_List):
    permission_classes = [MODULE, HasPermission(p.P_VIEW)]

    def get_queryset(self):
        qs = scoping.own_requests(_actor(self.request))
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return qs.order_by("-id")

    def post(self, request):
        data = request_svc.LeaveInput(**_valid(s.LeaveInputSerializer, request))
        req = request_svc.apply(_actor(request), data)
        resp = _one(request, req)
        resp.status_code = status.HTTP_201_CREATED
        return resp


@extend_schema(responses=s.LeaveRequestSerializer)
class RequestDetailView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk):
        req = scoping.visible_requests(_actor(request)).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such leave request.")
        data = _one(request, req).data
        data["history"] = s.TransitionSerializer(
            req.transitions.order_by("at", "id"), many=True).data
        return Response(data)


@extend_schema(request=s.LeaveInputSerializer, responses=s.LeaveRequestSerializer)
class ModifyView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    def post(self, request, pk):
        data = request_svc.LeaveInput(**_valid(s.LeaveInputSerializer, request))
        return _one(request, request_svc.modify(_actor(request), pk, data))


@extend_schema(request=s.ReasonSerializer, responses=s.LeaveRequestSerializer)
class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_WITHDRAW)]

    def post(self, request, pk):
        v = _valid(s.ReasonSerializer, request)
        return _one(request, request_svc.withdraw(_actor(request), pk, v["reason"]))


@extend_schema(request=s.ReasonSerializer, responses=s.LeaveRequestSerializer)
class CancelView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    def post(self, request, pk):
        v = _valid(s.ReasonSerializer, request)
        return _one(request, request_svc.request_cancellation(_actor(request), pk,
                                                              v["reason"]))


@extend_schema(request=s.RenominateSerializer, responses=s.LeaveRequestSerializer)
class RenominateView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    def post(self, request, pk):
        v = _valid(s.RenominateSerializer, request)
        return _one(request, request_svc.renominate(
            _actor(request), pk, v["substitute_user_id"], v["responsibility"]))


@extend_schema(request=s.ExtensionSerializer, responses=s.LeaveRequestSerializer)
class ExtendView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_CREATE)]

    def post(self, request, pk):
        v = _valid(s.ExtensionSerializer, request)
        req = request_svc.apply_extension(_actor(request), pk, **v)
        resp = _one(request, req)
        resp.status_code = status.HTTP_201_CREATED
        return resp


@extend_schema(request=s.ResumptionSerializer, responses=s.LeaveRequestSerializer)
class ResumeView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    def post(self, request, pk):
        v = _valid(s.ResumptionSerializer, request)
        return _one(request, resumption_svc.submit(_actor(request), pk, **v))


@extend_schema(responses={(200, "text/plain"): OpenApiTypes.STR})
class PrintView(APIView):
    """EL-UC-013: a printable copy of one's own application."""

    permission_classes = [MODULE, HasPermission(p.P_VIEW)]

    def get(self, request, pk):
        req = scoping.own_requests(_actor(request)).filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such leave request.")
        names = _names([req.user_id, req.substitute_user_id])
        who = names.get(req.user_id)
        sub = names.get(req.substitute_user_id) if req.substitute_user_id else None
        lines = [
            "PDPM IIITDM Jabalpur — Leave Application",
            f"Application no.: {req.pk}",
            f"Applicant: {who.display_name if who else req.user_id} ({req.applicant_kind})",
            f"Unit: {req.applicant_unit or '-'}",
            f"Leave: {c.LABELS.get(req.category, req.category)}"
            + (f" ({req.half} half)" if req.half else ""),
            f"Period: {req.start_date} to {req.end_date} ({req.days} day(s))",
            f"Purpose: {req.purpose}",
            f"Station leave: {'yes' if req.station_leave else 'no'}"
            + (f", {req.station_from} to {req.station_to}, {req.station_address}"
               if req.station_leave else ""),
            f"Substitute: {sub.display_name if sub else '-'} {req.substitute_status}",
            f"Status: {req.status.replace('_', ' ')}",
            f"Route: {' -> '.join(st['role'] for st in req.route) or '-'}",
            f"Printed: {timezone.localtime():%Y-%m-%d %H:%M}",
        ]
        resp = HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
        resp["Content-Disposition"] = f'attachment; filename="leave-{req.pk}.txt"'
        return resp


@extend_schema(responses=s.BalanceSerializer)
class BalanceView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_BALANCE)]

    def get(self, request):
        actor = _actor(request)
        return Response(_balance(actor.user_id, getattr(actor, "kind", "")))


def _balance(user_id: int, kind: str) -> dict:
    pv = config_sel.effective_policy()
    if pv is not None and kind in c.EMPLOYEE_KINDS:
        ledger_svc.ensure_annual_credits(user_id, kind, timezone.localdate().year,
                                         policy_domain.parse(pv.params))
    return s.BalanceSerializer({
        "user_id": user_id,
        "balances": ledger_sel.balances(user_id),
        "pending": ledger_sel.pending_days(user_id),
        "history": list(ledger_sel.history(user_id)[:200]),
    }).data


@extend_schema(parameters=[OpenApiParameter("user_id", int, required=True)],
               responses=s.BalanceSerializer)
class AccountView(APIView):
    """Leave Administrator: any employee's account (EL-UC-016 support)."""

    permission_classes = [MODULE, HasPermission(p.P_ACCOUNT_VIEW)]

    def get(self, request):
        uid = _int_param(request.query_params, "user_id")
        if uid is None:
            raise BadRequestError("user_id is required.", code="invalid_filter")
        emp = _names([uid]).get(uid)
        if emp is None or emp.kind not in c.EMPLOYEE_KINDS:
            raise NotFoundError("No such employee.")
        data = _balance(uid, emp.kind)
        data["display_name"] = emp.display_name
        return Response(data)


# -- Substitute ----------------------------------------------------------------
class SubstitutionListView(_List):
    permission_classes = [MODULE, HasPermission(p.P_SUBSTITUTE)]

    def get_queryset(self):
        return scoping.substitution_requests(_actor(self.request)).order_by("-id")


@extend_schema(request=s.SubstituteResponseSerializer, responses=s.LeaveRequestSerializer)
class SubstitutionRespondView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_SUBSTITUTE)]

    def post(self, request, pk):
        v = _valid(s.SubstituteResponseSerializer, request)
        return _one(request, workflow_svc.respond_substitution(_actor(request), pk, **v))


# -- Approvers -----------------------------------------------------------------
class QueueView(_List):
    permission_classes = [MODULE, HasPermission(p.P_REVIEW, p.P_APPROVE)]
    queue = True

    def get_queryset(self):
        return scoping.decision_queue(_actor(self.request)).order_by("stage_entered_at",
                                                                     "id")


@extend_schema(request=s.DecisionSerializer, responses=s.LeaveRequestSerializer)
class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_REVIEW, p.P_APPROVE)]

    def post(self, request, pk):
        v = _valid(s.DecisionSerializer, request)
        return _one(request, workflow_svc.decide(_actor(request), pk, **v))


class ResumptionQueueView(_List):
    permission_classes = [MODULE, HasPermission(p.P_RESUMPTION)]

    def get_queryset(self):
        return scoping.resumption_queue(_actor(self.request)).order_by("id")


@extend_schema(request=s.VerifySerializer, responses=s.LeaveRequestSerializer)
class VerifyView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_RESUMPTION)]

    def post(self, request, pk):
        v = _valid(s.VerifySerializer, request)
        return _one(request, resumption_svc.verify(_actor(request), pk, **v))


# -- Leave Administrator -------------------------------------------------------
class PolicyListView(generics.ListAPIView):
    serializer_class = s.PolicyVersionSerializer
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]
    queryset = PolicyVersion.objects.order_by("-id")

    @extend_schema(request=s.PolicyVersionSerializer, responses=s.PolicyVersionSerializer)
    def post(self, request):
        v = _valid(s.PolicyVersionSerializer, request)
        pv = config_svc.create_policy(_actor(request), **v)
        return Response(s.PolicyVersionSerializer(pv).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.PolicyVersionSerializer, responses=s.PolicyVersionSerializer)
class PolicyDetailView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]

    def put(self, request, pk):
        v = _valid(s.PolicyVersionSerializer, request)
        return Response(s.PolicyVersionSerializer(
            config_svc.update_policy(_actor(request), pk, **v)).data)


@extend_schema(request=None, responses=s.PolicyVersionSerializer)
class PolicyPublishView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]

    def post(self, request, pk):
        return Response(s.PolicyVersionSerializer(
            config_svc.publish_policy(_actor(request), pk)).data)


class CalendarListView(generics.ListAPIView):
    serializer_class = s.CalendarVersionSerializer
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]
    queryset = CalendarVersion.objects.prefetch_related("entries").order_by("-id")

    @extend_schema(request=s.CalendarVersionSerializer,
                   responses=s.CalendarVersionSerializer)
    def post(self, request):
        v = _valid(s.CalendarVersionSerializer, request)
        cv = config_svc.create_calendar(_actor(request), name=v["name"],
                                        effective_from=v["effective_from"],
                                        entries=v["entries"])
        return Response(s.CalendarVersionSerializer(cv).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.CalendarVersionSerializer, responses=s.CalendarVersionSerializer)
class CalendarDetailView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]

    def put(self, request, pk):
        v = _valid(s.CalendarVersionSerializer, request)
        cv = config_svc.update_calendar(_actor(request), pk, name=v["name"],
                                        effective_from=v["effective_from"],
                                        entries=v["entries"])
        return Response(s.CalendarVersionSerializer(cv).data)


@extend_schema(request=None, responses=s.CalendarVersionSerializer)
class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]

    def post(self, request, pk):
        return Response(s.CalendarVersionSerializer(
            config_svc.publish_calendar(_actor(request), pk)).data)


class OfflineListView(generics.ListAPIView):
    serializer_class = s.OfflineRecordSerializer
    permission_classes = [MODULE, HasPermission(p.P_OFFLINE)]
    queryset = OfflineLeaveRecord.objects.select_related("request").order_by("-id")

    @extend_schema(request=s.OfflineInputSerializer, responses=s.OfflineRecordSerializer)
    def post(self, request):
        v = _valid(s.OfflineInputSerializer, request)
        req = offline_svc.record(_actor(request), **v)
        return Response(s.OfflineRecordSerializer(req.offline_record).data,
                        status=status.HTTP_201_CREATED)


# -- Everyone in the module ----------------------------------------------------
class NotificationListView(generics.ListAPIView):
    serializer_class = s.NotificationSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.notifications_for(_actor(self.request)).order_by("-id")


@extend_schema(parameters=[OpenApiParameter("q", str)], responses=OpenApiTypes.OBJECT)
class EmployeeSearchView(APIView):
    """Substitute picker: faculty and staff only, never students."""

    permission_classes = [MODULE, HasPermission(p.P_CREATE, p.P_OFFLINE, p.P_ACCOUNT_VIEW)]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response({"results": []})
        rows = [u for kind in c.EMPLOYEE_KINDS
                for u in directory.search(q=q, kind=kind, limit=10)]
        return Response({"results": [
            {"user_id": u.user_id, "display_name": u.display_name,
             "username": u.username, "kind": u.kind, "department": u.department}
            for u in rows if u.user_id != _actor(request).user_id]})
