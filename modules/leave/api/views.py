from django.http import HttpResponse
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave import services
from modules.leave.api.serializers import (
    AccountSerializer,
    ApplicationSerializer,
    CalendarSerializer,
    DecisionSerializer,
    ExtensionSerializer,
    HistorySerializer,
    LeaveWriteSerializer,
    NotificationSerializer,
    OfflineLeaveSerializer,
    PolicySerializer,
    ResumptionSerializer,
)
from modules.leave.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
    LeaveNotification,
    LeavePolicy,
    LeaveResumption,
)

MODULE = HasModuleGrant("leave_elm")
P_VIEW = HasPermission("leave_elm.application.view_self")
P_APPLY = HasPermission("leave_elm.application.apply")
P_WORKFLOW = HasPermission("leave_elm.workflow.review")


def actor(request):
    return request.principal


def own(request, pk):
    app = LeaveApplication.objects.filter(pk=pk, user_id=actor(request).user_id).first()
    if not app:
        raise NotFoundError("No accessible leave application.")
    return app


class BalanceView(generics.ListAPIView):
    permission_classes = [MODULE, P_VIEW]
    serializer_class = AccountSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveAccount.objects.none()
        return LeaveAccount.objects.filter(
            user_id=actor(self.request).user_id, year=timezone.now().year
        ).order_by("category")


class ApplicationListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, P_VIEW]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        p = actor(self.request)
        if p.has_permission("leave_elm.workflow.review"):
            return LeaveApplication.objects.all().order_by("-created_at")
        if p.has_permission("leave_elm.workflow.substitute"):
            return LeaveApplication.objects.filter(
                Q(user_id=p.user_id) | Q(substitute_user_id=p.user_id)
            ).order_by("-created_at")
        return LeaveApplication.objects.filter(user_id=p.user_id).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        if not actor(request).has_permission("leave_elm.application.apply"):
            return Response({"detail": "You may not apply for leave."}, status=403)
        payload = LeaveWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            app = services.submit(actor=actor(request), data=payload.validated_data)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="leave_validation") from exc
        return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, P_VIEW]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(user_id=actor(self.request).user_id)


@extend_schema(responses=HistorySerializer)
class ApplicationHistoryView(APIView):
    permission_classes = [MODULE, P_VIEW]

    def get(self, request, pk):
        app = own(request, pk)
        return Response({
            "application_id": app.pk,
            "transitions": [
                {"from_state": row.from_state, "to_state": row.to_state,
                 "actor_user_id": row.actor_user_id, "reason": row.reason,
                 "created_at": row.created_at}
                for row in app.transitions.order_by("created_at")
            ],
        })


@extend_schema(request=None, responses=ApplicationSerializer)
class ActionView(APIView):
    permission_classes = [MODULE, P_VIEW]

    def post(self, request, pk):
        app = own(request, pk)
        try:
            if self.action == "withdraw":
                app = services.withdraw(app=app, actor=actor(request))
            elif self.action == "substitute":
                app = services.respond_substitute(
                    app=app, actor=actor(request), accept=request.data.get("accept", False)
                )
            elif self.action == "replace":
                app = services.replace_substitute(
                    app=app,
                    actor=actor(request),
                    substitute_user_id=int(request.data["substitute_user_id"]),
                )
            else:
                raise BadRequestError("Unsupported leave action.")
        except (ValueError, KeyError) as exc:
            raise BadRequestError(str(exc), code="leave_workflow") from exc
        return Response(ApplicationSerializer(app).data)


class WithdrawView(ActionView):
    action = "withdraw"
    permission_classes = [MODULE, HasPermission("leave_elm.application.withdraw")]


@extend_schema(request=None, responses=ApplicationSerializer)
class CancellationView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.cancel")]

    def post(self, request, pk):
        app = own(request, pk)
        try:
            result = services.cancellation(actor=actor(request), app=app)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="leave_cancellation") from exc
        return Response(ApplicationSerializer(result).data, status=201)


@extend_schema(request=ExtensionSerializer, responses=ApplicationSerializer)
class ExtensionView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.extend")]

    def post(self, request, pk):
        app = own(request, pk)
        payload = ExtensionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            result = services.extension(
                actor=actor(request),
                app=app,
                **payload.validated_data,
            )
        except (ValueError, KeyError) as exc:
            raise BadRequestError(str(exc), code="leave_extension") from exc
        return Response(ApplicationSerializer(result).data, status=201)


class SubstituteResponseView(ActionView):
    action = "substitute"
    permission_classes = [MODULE, HasPermission("leave_elm.workflow.substitute")]

    def post(self, request, pk):
        app = LeaveApplication.objects.filter(pk=pk).first()
        if not app:
            raise NotFoundError("No such leave request.")
        try:
            app = services.respond_substitute(
                app=app, actor=actor(request), accept=bool(request.data.get("accept"))
            )
        except ValueError as exc:
            raise BadRequestError(str(exc), code="leave_workflow") from exc
        return Response(ApplicationSerializer(app).data)


class ReplacementView(ActionView):
    action = "replace"


@extend_schema(request=DecisionSerializer, responses=ApplicationSerializer)
class DecisionView(APIView):
    permission_classes = [MODULE, P_WORKFLOW]

    def post(self, request, pk):
        app = LeaveApplication.objects.filter(pk=pk).first()
        if not app:
            raise NotFoundError("No such leave request.")
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            app = services.review(app=app, actor=actor(request), **payload.validated_data)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="leave_decision") from exc
        return Response(ApplicationSerializer(app).data)


@extend_schema(request=ResumptionSerializer, responses=ResumptionSerializer)
class ResumptionCreateView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.application.resume")]

    def post(self, request, pk):
        app = own(request, pk)
        if app.category not in ("EL", "COL", "VL") or app.state != "approved":
            raise BadRequestError("Resumption applies only to approved EL, COL, or VL.")
        payload = ResumptionSerializer(data={**request.data, "application": app.pk})
        payload.is_valid(raise_exception=True)
        res = payload.save()
        app.state = "resumption_review"
        app.save(update_fields=["state", "updated_at"])
        return Response(ResumptionSerializer(res).data, status=201)


@extend_schema(request=None, responses=ResumptionSerializer)
class ResumptionReviewView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.workflow.sanction")]

    def post(self, request, pk):
        res = LeaveResumption.objects.filter(pk=pk, state="pending").first()
        if not res:
            raise NotFoundError("No pending resumption.")
        try:
            res = services.review_resumption(resumption=res, actor=actor(request))
        except ValueError as exc:
            raise BadRequestError(str(exc), code="leave_resumption") from exc
        return Response(ResumptionSerializer(res).data)


@extend_schema(request=OfflineLeaveSerializer, responses=ApplicationSerializer)
class OfflineLeaveView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.records.manage")]

    def post(self, request):
        payload = OfflineLeaveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            data = dict(payload.validated_data)
            employee_user_id = int(data.pop("employee_user_id"))
            employee_kind = data.pop("employee_kind")
            evidence = data.pop("evidence")
            app = services.record_offline(actor=actor(request), employee_user_id=employee_user_id,
                                          employee_kind=employee_kind, data=data, evidence=evidence)
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestError(str(exc), code="offline_leave") from exc
        return Response(ApplicationSerializer(app).data, status=201)


@extend_schema(responses=NotificationSerializer(many=True))
class NotificationListView(APIView):
    permission_classes = [MODULE, P_VIEW]

    def get(self, request):
        rows = LeaveNotification.objects.filter(
            user_id=actor(request).user_id
        ).order_by("-created_at")
        return Response([{"id": row.pk, "application_id": row.application_id,
                          "kind": row.kind, "read": row.read,
                          "created_at": row.created_at} for row in rows])


class PolicyView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]
    queryset = LeavePolicy.objects.all().order_by("-year")
    serializer_class = PolicySerializer


class CalendarView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]
    queryset = HolidayCalendar.objects.all().order_by("-year", "-version")
    serializer_class = CalendarSerializer


@extend_schema(request=None, responses=CalendarSerializer)
class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.configuration.manage")]

    def post(self, request, pk):
        cal = HolidayCalendar.objects.filter(pk=pk).first()
        if not cal:
            raise NotFoundError("No such calendar.")
        HolidayCalendar.objects.filter(year=cal.year, published=True).update(published=False)
        cal.published = True
        cal.published_at = timezone.now()
        cal.published_by = actor(request).user_id
        cal.save()
        return Response(CalendarSerializer(cal).data)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
class YearEndView(APIView):
    permission_classes = [MODULE, HasPermission("leave_elm.year_end.process")]

    def post(self, request):
        return Response(
            {
                "processed": services.year_end(
                    year=int(request.data.get("year", timezone.now().year))
                )
            }
        )


@extend_schema(responses=OpenApiTypes.BINARY)
class ExportView(APIView):
    permission_classes = [MODULE, P_VIEW]

    def get(self, request, pk):
        app = own(request, pk)
        body = "ELM Leave Application\n\n" + "\n".join(
            f"{field}: {getattr(app, field)}"
            for field in (
                "id",
                "category",
                "start_date",
                "end_date",
                "purpose",
                "state",
                "chargeable_days",
            )
        )
        return HttpResponse(
            body,
            content_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="leave-{app.pk}.txt"'},
        )
