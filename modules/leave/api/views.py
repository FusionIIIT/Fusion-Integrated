"""HTTP layer: parse, scope, delegate, serialise."""
from __future__ import annotations

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import HolidayCalendar, LeavePolicy
from modules.leave.selectors import scoping
from modules.leave.services import accounts, admin, applications as app_svc
from modules.leave.services import policy as policy_svc

MODULE = HasModuleGrant("leave")


def _actor(request):
    return getattr(request, "principal", None)


class ApplicationListView(generics.ListCreateAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission("leave.application.view",
                                                "leave.application.create")]

    def get_queryset(self):
        return scoping.applications_for(_actor(self.request)).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        payload = s.LeaveWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = app_svc.submit(_actor(request), **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [MODULE, HasPermission("leave.application.view")]

    def get_object(self):
        return scoping.get_visible_application(_actor(self.request), self.kwargs["pk"])


class ApplicationHistoryView(generics.ListAPIView):
    serializer_class = s.TransitionSerializer
    permission_classes = [MODULE, HasPermission("leave.application.view")]

    def get_queryset(self):
        app = scoping.get_visible_application(_actor(self.request), self.kwargs["pk"])
        return app.history.order_by("created_at")


class ApplicationExportView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.export")]

    def get(self, request, pk):
        app = scoping.get_visible_application(_actor(request), pk)
        body = (
            f"Leave application #{app.pk}\n"
            f"Employee user_id: {app.user_id}\n"
            f"Category: {app.category}\n"
            f"Period: {app.start_on} to {app.end_on} ({app.half or 'full day'})\n"
            f"Chargeable days: {app.chargeable_days}\n"
            f"Status: {app.status}\n"
            f"Purpose: {app.purpose}\n"
            f"Station leave: {app.station_leave}\n"
            f"Substitute: {app.substitute_user_id or 'n/a'}\n"
        )
        resp = HttpResponse(body, content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="leave-{app.pk}.txt"'
        return resp


class ModifyView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.update")]

    def post(self, request, pk):
        payload = s.LeaveWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        row = app_svc.modify(_actor(request), pk, **payload.validated_data)
        return Response(s.LeaveApplicationSerializer(row).data)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.delete")]

    def post(self, request, pk):
        row = app_svc.withdraw(_actor(request), pk)
        return Response(s.LeaveApplicationSerializer(row).data)


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission("leave.substitute.review")]

    def post(self, request, pk):
        accept = bool(request.data.get("accept"))
        row = app_svc.respond_substitute(_actor(request), pk, accept=accept)
        return Response(s.LeaveApplicationSerializer(row).data)


class SubstituteNominateView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.update")]

    def post(self, request, pk):
        nominee = int(request.data.get("substitute_user_id"))
        row = app_svc.nominate_substitute(_actor(request), pk, nominee)
        return Response(s.LeaveApplicationSerializer(row).data)


class UnitHeadView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.review",
                                                "leave.application.approve")]

    def post(self, request, pk):
        action = request.data.get("action")
        note = request.data.get("note") or ""
        row = app_svc.unit_head_decide(_actor(request), pk, action=action, note=note)
        return Response(s.LeaveApplicationSerializer(row).data)


class EstablishmentView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.review")]

    def post(self, request, pk):
        row = app_svc.establishment_route(
            _actor(request), pk, note=request.data.get("note") or "")
        return Response(s.LeaveApplicationSerializer(row).data)


class SanctionView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.approve")]

    def post(self, request, pk):
        approve = bool(request.data.get("approve"))
        row = app_svc.final_decide(
            _actor(request), pk, approve=approve, note=request.data.get("note") or "")
        return Response(s.LeaveApplicationSerializer(row).data)


class CancelView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.create")]

    def post(self, request, pk):
        row = app_svc.request_cancellation(
            _actor(request), pk, reason=request.data.get("reason") or "")
        return Response(s.LeaveApplicationSerializer(row).data)


class CancelDecideView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.approve")]

    def post(self, request, pk):
        row = app_svc.decide_cancellation(
            _actor(request), pk, approve=bool(request.data.get("approve")),
            note=request.data.get("note") or "")
        return Response(s.LeaveApplicationSerializer(row).data)


class ExtendView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.create")]

    def post(self, request, pk):
        extra = request.data.get("extra_end_on")
        from datetime import date as date_cls
        extra_end = date_cls.fromisoformat(extra)
        row = app_svc.submit_extension(
            _actor(request), pk, extra_end_on=extra_end,
            purpose=request.data.get("purpose") or "",
            substitute_user_id=request.data.get("substitute_user_id"),
            station_leave=bool(request.data.get("station_leave")),
            station_details=request.data.get("station_details") or "",
        )
        return Response(s.LeaveApplicationSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ResumeView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.create")]

    def post(self, request, pk):
        from datetime import date as date_cls
        row = app_svc.submit_resumption(
            _actor(request), pk,
            resumption_on=date_cls.fromisoformat(request.data.get("resumption_on")),
            details=request.data.get("details") or "",
        )
        return Response(s.LeaveApplicationSerializer(row).data)


class VerifyResumeView(APIView):
    permission_classes = [MODULE, HasPermission("leave.application.review")]

    def post(self, request, pk):
        row = app_svc.verify_resumption(
            _actor(request), pk, verified=bool(request.data.get("verified")),
            note=request.data.get("note") or "")
        return Response(s.LeaveApplicationSerializer(row).data)


class BalanceView(APIView):
    permission_classes = [MODULE, HasPermission("leave.balance.view")]

    def get(self, request):
        from datetime import date as date_cls
        actor = _actor(request)
        year = int(request.query_params.get("year") or date_cls.today().year)
        _, snap = policy_svc.effective_policy()
        accounts.ensure_year_credits(actor.user_id, year, snap)
        bals = accounts.balances(actor.user_id, year)
        hist = s.LedgerSerializer(accounts.history(actor.user_id)[:100], many=True).data
        return Response({
            "year": year,
            "balances": {k: str(v) for k, v in bals.items()},
            "history": hist,
        })


class TaskListView(generics.ListAPIView):
    serializer_class = s.TaskSerializer
    permission_classes = [MODULE, HasPermission("leave.application.view")]

    def get_queryset(self):
        return scoping.tasks_for(_actor(self.request)).order_by("created_at")


class PolicyView(APIView):
    permission_classes = [MODULE, HasPermission("leave.policy.publish",
                                                "leave.application.view")]

    def get(self, request):
        row = LeavePolicy.objects.filter(is_effective=True).first()
        return Response(s.PolicySerializer(row).data if row else {})

    def post(self, request):
        payload = s.PolicyWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = admin.publish_policy(_actor(request), fields=payload.validated_data)
        return Response(s.PolicySerializer(row).data, status=status.HTTP_201_CREATED)


class CalendarView(APIView):
    permission_classes = [MODULE, HasPermission("leave.calendar.publish",
                                                "leave.application.view")]

    def get(self, request):
        row = HolidayCalendar.objects.filter(is_effective=True).prefetch_related("entries").first()
        return Response(s.CalendarSerializer(row).data if row else {})

    def post(self, request):
        payload = s.CalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = admin.publish_calendar(
            _actor(request), year=data["year"], label=data.get("label") or "",
            entries=data["entries"])
        return Response(s.CalendarSerializer(row).data, status=status.HTTP_201_CREATED)


class OfflineView(APIView):
    permission_classes = [MODULE, HasPermission("leave.offline.create")]

    def post(self, request):
        from datetime import date as date_cls
        row = admin.record_offline(
            _actor(request),
            user_id=int(request.data["user_id"]),
            category=request.data["category"],
            start_on=date_cls.fromisoformat(request.data["start_on"]),
            end_on=date_cls.fromisoformat(request.data["end_on"]),
            purpose=request.data.get("purpose") or "Offline-sanctioned leave",
            reference=request.data.get("reference") or "",
            half=request.data.get("half") or "",
            station_leave=bool(request.data.get("station_leave")),
            medical_evidence=bool(request.data.get("medical_evidence")),
        )
        return Response(s.LeaveApplicationSerializer(row).data,
                        status=status.HTTP_201_CREATED)
