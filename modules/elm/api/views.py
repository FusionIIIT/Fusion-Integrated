"""ELM endpoints. `user_id` is never read from the body on self-service paths;
it comes from the credential."""
from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm import selectors, services
from modules.elm.api import serializers as s
from modules.elm.models import HolidayCalendar, LeaveApplication

MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.application.view_self"
P_VIEW = "elm.application.view"
P_CREATE = "elm.application.create"
P_DECIDE = "elm.application.decide"
P_WITHDRAW = "elm.application.withdraw"
P_CANCEL = "elm.application.cancel"
P_SUBSTITUTE = "elm.substitute.respond"
P_BALANCE = "elm.balance.view_self"
P_ADMIN = "elm.admin.manage"


def _actor(request):
    return getattr(request, "principal", None)


def _get_visible(principal, pk: int) -> LeaveApplication:
    app = LeaveApplication.objects.filter(pk=pk).first()
    if app is None:
        raise NotFoundError("No such leave request.")
    if principal.has_permission(P_VIEW):
        return app
    if app.user_id != principal.user_id:
        raise NotFoundError("No such leave request.")
    return app


class LeaveListCreateView(APIView):
    """The caller's own leave applications, and the way to file a new one."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True),
                   operation_id="leave_applications_list")
    def get(self, request):
        qs = selectors.visible_applications(request.principal)
        return Response({"results": s.LeaveApplicationSerializer(qs, many=True).data})

    @extend_schema(request=s.LeaveApplySerializer,
                   responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        payload = s.LeaveApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        p = _actor(request)
        app = services.apply(user_id=p.user_id, kind=p.kind,
                             **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data,
                        status=status.HTTP_201_CREATED)


class LeaveDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer)
    def get(self, request, pk):
        app = _get_visible(_actor(request), pk)
        return Response(s.LeaveApplicationSerializer(app).data)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_WITHDRAW)]

    @extend_schema(request=None, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        app = services.withdraw(user_id=_actor(request).user_id, application_id=pk)
        return Response(s.LeaveApplicationSerializer(app).data)


class CancelView(APIView):
    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    @extend_schema(request=None, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        app = services.cancel(user_id=_actor(request).user_id, application_id=pk)
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(request=s.SubstituteRespondSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.SubstituteRespondSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.respond_substitute(
            user_id=_actor(request).user_id, application_id=pk,
            accept=payload.validated_data["accept"])
        return Response(s.LeaveApplicationSerializer(app).data)


class BalancesView(APIView):
    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    @extend_schema(responses=s.LeaveBalanceSerializer(many=True))
    def get(self, request):
        p = _actor(request)
        year = int(request.query_params.get("year",
                                            timezone.localdate().year))
        services.ensure_balances(p.user_id, year, p.kind)
        rows = selectors.balances_for(p.user_id, year)
        return Response({"results": s.LeaveBalanceSerializer(rows, many=True).data})


class InboxView(APIView):
    """Requests awaiting a decision, for a Unit Head / Sanctioning Authority."""

    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True))
    def get(self, request):
        qs = (LeaveApplication.objects
              .filter(status="submitted")
              .order_by("start_date"))
        return Response({"results": s.LeaveApplicationSerializer(qs, many=True).data})


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(request=s.DecideSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.DecideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.decide(actor_user_id=_actor(request).user_id,
                              application_id=pk,
                              approve=payload.validated_data["approve"],
                              note=payload.validated_data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(app).data)


class HolidaysView(APIView):
    """Maintain the published holiday / restricted-holiday calendar."""

    permission_classes = [MODULE, HasPermission(P_ADMIN)]

    @extend_schema(responses=s.HolidaySerializer(many=True))
    def get(self, request):
        qs = HolidayCalendar.objects.all()
        return Response({"results": s.HolidaySerializer(qs, many=True).data})

    @extend_schema(request=s.HolidaySerializer, responses={201: s.HolidaySerializer})
    def post(self, request):
        payload = s.HolidaySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        holiday = payload.save()
        return Response(s.HolidaySerializer(holiday).data,
                        status=status.HTTP_201_CREATED)
