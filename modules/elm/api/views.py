"""ELM endpoints. `user_id` is never read from the body on self-service paths;
it comes from the credential.
"""
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
from modules.elm.models import HolidayCalendar, LeaveApplication, VacationCalendar

MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.application.view_self"
P_VIEW = "elm.application.view"
P_CREATE = "elm.application.create"
P_DECIDE = "elm.application.decide"
P_RECOMMEND = "elm.application.recommend"
P_WITHDRAW = "elm.application.withdraw"
P_CANCEL = "elm.application.cancel"
P_RESUME = "elm.application.resume"
P_SUBSTITUTE = "elm.substitute.respond"
P_BALANCE = "elm.balance.view_self"
P_ADMIN = "elm.admin.manage"
P_OFFLINE = "elm.admin.offline"


def _actor(request):
    return getattr(request, "principal", None)


def _get_visible(principal, pk: int) -> LeaveApplication:
    qs = selectors.visible_applications(principal)
    app = qs.filter(pk=pk).first()
    if app is not None:
        return app
    # Check if caller is nominated substitute
    app_sub = LeaveApplication.objects.filter(pk=pk, substitute_user_id=principal.user_id).first()
    if app_sub is not None:
        return app_sub
    raise NotFoundError("No such leave request.")


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
        is_director = bool(p.active_role and p.active_role.lower() == "director")
        app = services.apply(user_id=p.user_id, kind=p.kind,
                             is_director=is_director,
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


class CancelRequestView(APIView):
    """Applicant requests cancellation of approved leave before it begins (BR-EL-023)."""

    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    @extend_schema(request=None, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        app = services.request_cancellation(user_id=_actor(request).user_id, application_id=pk)
        return Response(s.LeaveApplicationSerializer(app).data)


class DecideCancelView(APIView):
    """Sanctioning authority approves or rejects cancellation (BR-EL-023)."""

    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(request=s.DecideSerializer, responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        _get_visible(_actor(request), pk)
        payload = s.DecideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.decide_cancellation(
            actor_user_id=_actor(request).user_id,
            application_id=pk,
            approve=payload.validated_data["approve"],
            note=payload.validated_data.get("note", ""))
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


class RenominateSubstituteView(APIView):
    """Applicant nominates replacement substitute after decline (EL-UC-019, BR-EL-015)."""

    permission_classes = [MODULE, HasPermission(P_CREATE)]

    @extend_schema(request=s.RenominateSubstituteSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.RenominateSubstituteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.renominate_substitute(
            user_id=_actor(request).user_id, application_id=pk,
            substitute_user_id=payload.validated_data["substitute_user_id"])
        return Response(s.LeaveApplicationSerializer(app).data)


class RecommendView(APIView):
    """Unit Head records recommendation for higher-sanction leave (BR-EL-017)."""

    permission_classes = [MODULE, HasPermission(P_RECOMMEND)]

    @extend_schema(request=s.RecommendSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        _get_visible(_actor(request), pk)
        payload = s.RecommendSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.recommend(
            actor_user_id=_actor(request).user_id,
            application_id=pk,
            recommended=payload.validated_data["recommended"],
            note=payload.validated_data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(app).data)


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(request=s.DecideSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        _get_visible(_actor(request), pk)
        payload = s.DecideSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.decide(actor_user_id=_actor(request).user_id,
                              application_id=pk,
                              approve=payload.validated_data["approve"],
                              note=payload.validated_data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(app).data)


class SubmitResumptionView(APIView):
    """Employee reports return to duty for EL, COL, VL (BR-EL-027)."""

    permission_classes = [MODULE, HasPermission(P_RESUME)]

    @extend_schema(request=s.ResumptionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        payload = s.ResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.submit_resumption(
            user_id=_actor(request).user_id,
            application_id=pk,
            actual_resumption_date=payload.validated_data["actual_resumption_date"],
            note=payload.validated_data.get("note", ""))
        return Response(s.LeaveApplicationSerializer(app).data)


class ReviewResumptionView(APIView):
    """Authority reviews duty resumption and synchronizes attendance/balance (BR-EL-028)."""

    permission_classes = [MODULE, HasPermission(P_DECIDE)]

    @extend_schema(request=s.ReviewResumptionSerializer,
                   responses=s.LeaveApplicationSerializer)
    def post(self, request, pk):
        _get_visible(_actor(request), pk)
        payload = s.ReviewResumptionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        app = services.review_resumption(
            actor_user_id=_actor(request).user_id,
            application_id=pk,
            note=payload.validated_data.get("note", ""))
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
    """Requests awaiting recommendation or decision for the caller."""

    permission_classes = [MODULE, HasPermission(P_DECIDE, P_RECOMMEND)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True))
    def get(self, request):
        qs = selectors.inbox_applications(request.principal)
        return Response({"results": s.LeaveApplicationSerializer(qs, many=True).data})


class SubstituteInboxView(APIView):
    """Pending requests where caller is nominated as substitute."""

    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    @extend_schema(responses=s.LeaveApplicationSerializer(many=True))
    def get(self, request):
        qs = selectors.substitute_inbox_applications(request.principal.user_id)
        return Response({"results": s.LeaveApplicationSerializer(qs, many=True).data})


class OfflineLeaveView(APIView):
    """Record authorized offline-sanctioned leave (BR-EL-029, BR-EL-037, EL-UC-016)."""

    permission_classes = [MODULE, HasPermission(P_OFFLINE)]

    @extend_schema(request=s.OfflineLeaveSerializer,
                   responses={201: s.LeaveApplicationSerializer})
    def post(self, request):
        payload = s.OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        # Determine kind for target user if possible
        kind = "faculty"
        app = services.record_offline_leave(
            admin_user_id=_actor(request).user_id,
            kind=kind,
            **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(app).data,
                        status=status.HTTP_201_CREATED)


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


class VacationCalendarView(APIView):
    """Maintain the academic vacation periods for faculty VL (EXT-01, BR-EL-006)."""

    permission_classes = [MODULE, HasPermission(P_ADMIN)]

    @extend_schema(responses=s.VacationCalendarSerializer(many=True))
    def get(self, request):
        qs = VacationCalendar.objects.all()
        return Response({"results": s.VacationCalendarSerializer(qs, many=True).data})

    @extend_schema(request=s.VacationCalendarSerializer,
                   responses={201: s.VacationCalendarSerializer})
    def post(self, request):
        payload = s.VacationCalendarSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        item = payload.save()
        return Response(s.VacationCalendarSerializer(item).data,
                        status=status.HTTP_201_CREATED)


class PrintableView(APIView):
    """Printable slip representation of a leave request (EL-UC-013, CFR-EL-023)."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_VIEW)]

    @extend_schema(responses=s.LeaveApplicationSerializer)
    def get(self, request, pk):
        app = _get_visible(_actor(request), pk)
        return Response({
            "application": s.LeaveApplicationSerializer(app).data,
            "generated_at": timezone.now().isoformat(),
            "institute": "PDPM IIITDM Jabalpur",
            "document_title": "EMPLOYEE LEAVE APPLICATION SLIP",
        })
