"""HTTP parsing and presentation; scoping and writes live outside this layer."""

import csv
import io

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iaa import selectors, services
from modules.iaa.api import serializers as s
from modules.iaa.domain.rules import OPERATORS, REPORTERS, Role, missing_submission


class Gate(APIView):
    permission_classes = [
        HasModuleGrant("institute_accounts_audits"),
        HasPermission("institute_accounts_audits.workspace.access"),
    ]

    def ctx(self, request, roles=OPERATORS):
        ctx = services.context(request.principal, request.headers.get("X-IAA-Role"))
        selectors.require_role(ctx, roles)
        return ctx


def valid(cls, data, **kwargs):
    serializer = cls(data=data, **kwargs)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


@extend_schema(responses=dict)
class SessionView(Gate):
    def get(self, request):
        return Response(
            {
                "roles": list(
                    selectors.assignments(request.principal.user_id).values("role", "department")
                ),
                "user_id": request.principal.user_id,
            }
        )

    @extend_schema(request=s.SwitchSerializer, responses=dict)
    def post(self, request):
        data = valid(s.SwitchSerializer, request.data)
        ctx = services.switch_role(request.principal, data["role"])
        return Response({"active_role": ctx.role})


class RequestsView(Gate):
    @extend_schema(responses=s.RequestSerializer(many=True))
    def get(self, request):
        ctx = self.ctx(request)
        qs = selectors.requests_for(ctx).order_by("-id")
        for key in ("kind", "status", "department"):
            if request.query_params.get(key):
                qs = qs.filter(**{key: request.query_params[key]})
        return Response({"results": s.RequestSerializer(qs[:200], many=True).data})

    @extend_schema(request=s.RequestWriteSerializer, responses={201: s.RequestSerializer})
    def post(self, request):
        ctx = self.ctx(request, {Role.BASIC})
        req = services.create_request(ctx, valid(s.RequestWriteSerializer, request.data))
        return Response(
            {**s.RequestSerializer(req).data, "missing_fields": missing_submission(req)}, status=201
        )


class RequestDetailView(Gate):
    @extend_schema(responses=s.IaaRequestDetailSerializer)
    def get(self, request, pk):
        ctx = self.ctx(request)
        req = get_object_or_404(
            selectors.requests_for(ctx).prefetch_related(
                "history", "clarifications", "anomalies", "observations"
            ),
            pk=pk,
        )
        return Response(
            {**s.IaaRequestDetailSerializer(req).data, "missing_fields": missing_submission(req)}
        )

    @extend_schema(request=s.RequestWriteSerializer, responses=s.RequestSerializer)
    def patch(self, request, pk):
        ctx = self.ctx(request, {Role.BASIC})
        data = valid(s.RequestWriteSerializer, request.data, partial=True)
        return Response(s.RequestSerializer(services.edit_draft(ctx, pk, data)).data)


ACTION_INPUT = {
    "submit": None,
    "query": s.RemarksSerializer,
    "respond": s.ResponseSerializer,
    "validate": s.FinanceSerializer,
    "decide": s.DecisionSerializer,
    "record": s.RecordSerializer,
    "anomaly": s.AnomalyWriteSerializer,
    "observation": s.ObservationWriteSerializer,
}


class ActionView(Gate):
    @extend_schema(operation_id="iaa_request_action", request=dict, responses=dict)
    def post(self, request, pk, action):
        ctx = self.ctx(request)
        if action not in ACTION_INPUT:
            raise NotFoundError()
        cls = ACTION_INPUT[action]
        data = valid(cls, request.data) if cls else {}
        handlers = {
            "submit": services.submit,
            "query": services.query,
            "respond": services.respond,
            "validate": services.validate_finance,
            "decide": services.decide,
            "record": services.record,
            "anomaly": services.flag_anomaly,
            "observation": services.raise_observation,
        }
        result = handlers[action](ctx, pk, **data)
        serializer = (
            s.AnomalySerializer
            if action == "anomaly"
            else s.ObservationSerializer
            if action == "observation"
            else s.RequestSerializer
        )
        return Response(serializer(result).data)


class AnomaliesView(Gate):
    @extend_schema(responses=s.AnomalySerializer(many=True))
    def get(self, request):
        ctx = self.ctx(request)
        return Response(
            {
                "results": s.AnomalySerializer(
                    selectors.anomalies_for(ctx).order_by("-id")[:200], many=True
                ).data
            }
        )


class ResolveView(Gate):
    @extend_schema(request=s.ResolveSerializer, responses=s.AnomalySerializer)
    def post(self, request, pk):
        return Response(
            s.AnomalySerializer(
                services.resolve_anomaly(
                    self.ctx(request), pk, **valid(s.ResolveSerializer, request.data)
                )
            ).data
        )


class ObservationsView(Gate):
    @extend_schema(responses=s.ObservationSerializer(many=True))
    def get(self, request):
        return Response(
            {
                "results": s.ObservationSerializer(
                    selectors.observations_for(self.ctx(request)).order_by("-id")[:200], many=True
                ).data
            }
        )


class ObservationActionView(Gate):
    @extend_schema(request=dict, responses=s.ObservationSerializer)
    def post(self, request, pk, action):
        ctx = self.ctx(request)
        if action == "respond":
            obj = services.respond_observation(ctx, pk, **valid(s.ResponseSerializer, request.data))
        elif action == "review":
            obj = services.review_observation(ctx, pk, **valid(s.VerifySerializer, request.data))
        else:
            raise NotFoundError()
        return Response(s.ObservationSerializer(obj).data)


class NotificationsView(Gate):
    @extend_schema(responses=s.NotificationSerializer(many=True))
    def get(self, request):
        return Response(
            {
                "results": s.NotificationSerializer(
                    selectors.notifications_for(self.ctx(request))[:100], many=True
                ).data
            }
        )


def csv_safe(value):
    text = str(value if value is not None else "")
    # IAA exports must be safe to open in spreadsheet software.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


class ReportsView(Gate):
    @extend_schema(responses=dict)
    def get(self, request):
        ctx = self.ctx(request, REPORTERS)
        if request.query_params.get("export") == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["ID", "Type", "Department", "Amount", "Status", "Submitted", "Recorded"]
            )
            for row in (
                selectors.requests_for(ctx)
                .order_by("id")
                .values_list(
                    "id", "kind", "department", "amount", "status", "submitted_at", "recorded_at"
                )
            ):
                writer.writerow([csv_safe(v) for v in row])
            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="iaa-report.csv"'
            return response
        return Response(selectors.summary(ctx))


class ConfigView(Gate):
    @extend_schema(responses=dict)
    def get(self, request, resource):
        self.ctx(request, {Role.ADMIN})
        if resource not in services.CONFIG_MODELS:
            raise NotFoundError()
        cls = s.CONFIG_SERIALIZERS[resource]
        return Response(
            {
                "results": cls(
                    services.CONFIG_MODELS[resource].objects.order_by("id"), many=True
                ).data
            }
        )

    @extend_schema(request=dict, responses=dict)
    def post(self, request, resource):
        ctx = self.ctx(request, {Role.ADMIN})
        if resource not in services.CONFIG_MODELS:
            raise NotFoundError()
        pk = request.data.get("id")
        if pk is not None and (not isinstance(pk, int) or isinstance(pk, bool) or pk < 1):
            raise BadRequestError("id must be a positive integer.")
        cls = s.CONFIG_SERIALIZERS[resource]
        model = services.CONFIG_MODELS[resource]
        obj = get_object_or_404(model, pk=pk) if pk else None
        serializer = cls(instance=obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            saved = services.configure(ctx, resource, serializer.validated_data, pk=pk)
        except DjangoValidationError as exc:
            raise BadRequestError(
                "Invalid configuration.", details=[{"message": message} for message in exc.messages]
            ) from exc
        return Response(cls(saved).data, status=200 if pk else 201)


class RecoverView(Gate):
    @extend_schema(request=None, responses=dict)
    def post(self, request, pk):
        services.recover_routing(self.ctx(request, {Role.ADMIN}), pk)
        return Response({"status": "routing_recovered"})
