"""HR service records and guarded request transitions; no mutable request CRUD."""

from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal

from . import decisions, submissions
from .models import (
    AuditEvent,
    EmployeeRecord,
    HRRequest,
    LeaveAccount,
    LeavePolicy,
    Notification,
    WorkflowRoute,
)
from .serializers import (
    AuditEventSerializer,
    DecisionSerializer,
    EmployeeRecordSerializer,
    HRRequestSerializer,
    LeaveAccountSerializer,
    LeavePolicySerializer,
    NotificationSerializer,
    SettlementSerializer,
    SubmitSerializer,
    WorkflowRouteSerializer,
)
from .support import emit


class GatedView:
    read_permission = "hreis.records.view"
    write_permission = "hreis.config.manage"
    action_permissions = {}

    def get_permissions(self):
        code = self.action_permissions.get(self.action)
        if code is None:
            code = (
                self.read_permission
                if self.action in ("list", "retrieve", "metadata")
                else self.write_permission
            )
        return [IsAuthenticatedPrincipal(), HasModuleGrant("hreis")(), HasPermission(code)()]


class EmployeeRecordViewSet(
    GatedView,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EmployeeRecord.objects.all()
    serializer_class = EmployeeRecordSerializer
    write_permission = "hreis.records.manage"

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        if p is None:
            return self.queryset.none()
        return (
            self.queryset.all()
            if p.has_permission("hreis.records.manage")
            else self.queryset.filter(user_id=p.user_id)
        )

    @transaction.atomic
    def perform_create(self, serializer):
        employee = serializer.save()
        emit(self.request.principal, "record.created", employee)

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = EmployeeRecord.objects.select_for_update().get(
            pk=serializer.instance.pk
        )
        employee = serializer.save()
        emit(self.request.principal, "record.updated", employee)


class ConfigView(GatedView, viewsets.ModelViewSet):
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def audit(self, obj, action_name):
        AuditEvent.objects.create(
            actor_id=self.request.principal.user_id,
            action=action_name,
            details={"model": obj._meta.label, "id": obj.pk},
        )

    @transaction.atomic
    def perform_create(self, serializer):
        if serializer.Meta.model is LeaveAccount:
            EmployeeRecord.objects.select_for_update().get(
                pk=serializer.validated_data["employee"].pk
            )
        self.audit(serializer.save(), "config.created")

    @transaction.atomic
    def perform_update(self, serializer):
        if isinstance(serializer.instance, LeaveAccount):
            EmployeeRecord.objects.select_for_update().get(pk=serializer.instance.employee_id)
        serializer.instance = serializer.Meta.model.objects.select_for_update().get(
            pk=serializer.instance.pk
        )
        self.audit(serializer.save(), "config.updated")


class LeavePolicyViewSet(ConfigView):
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer


class LeaveAccountViewSet(ConfigView):
    queryset = LeaveAccount.objects.select_related("employee", "policy")
    serializer_class = LeaveAccountSerializer

    def get_permissions(self):
        permissions = super().get_permissions()
        if self.action not in ("list", "retrieve", "metadata"):
            permissions.append(HasPermission("hreis.records.manage")())
        return permissions

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        if p is None:
            return self.queryset.none()
        if p.has_any_permission("hreis.records.manage", "hreis.config.manage"):
            return self.queryset.all()
        return self.queryset.filter(employee__user_id=p.user_id)


class WorkflowRouteViewSet(ConfigView):
    queryset = WorkflowRoute.objects.all()
    serializer_class = WorkflowRouteSerializer
    read_permission = "hreis.config.manage"


class HRRequestViewSet(
    GatedView, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = HRRequest.objects.select_related("employee", "policy")
    serializer_class = HRRequestSerializer
    http_method_names = ["get", "post", "head", "options"]
    read_permission = "hreis.requests.view"
    action_permissions = {
        "create": "hreis.requests.submit",
        "verify": "hreis.claims.verify",
        "decide": "hreis.requests.decide",
        "settle": "hreis.claims.settle",
    }

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        if p is None:
            return self.queryset.none()
        if p.has_permission("hreis.claims.verify"):
            return self.queryset.all()
        scope = Q(employee__user_id=p.user_id)
        if p.has_permission("hreis.claims.settle"):
            scope |= Q(kind__in=["LTC", "CPDA"], status__in=["APPROVED", "SETTLED"])
        if p.has_permission("hreis.requests.decide"):
            scope |= Q(status="PENDING", route__contains=[p.user_id])
        return self.queryset.filter(scope)

    def create(self, request):
        serializer = SubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = submissions.submit(request.principal, serializer.validated_data)
        return Response(HRRequestSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        obj = decisions.verify(request.principal, self.get_object().pk)
        return Response(HRRequestSerializer(obj).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = decisions.decide(request.principal, self.get_object().pk, **serializer.validated_data)
        return Response(HRRequestSerializer(obj).data)

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        serializer = SettlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = decisions.settle(request.principal, self.get_object().pk, **serializer.validated_data)
        return Response(HRRequestSerializer(obj).data)


class AuditEventViewSet(GatedView, viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    read_permission = "hreis.audit.view"
    write_permission = "hreis.audit.view"


class NotificationViewSet(GatedView, viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    read_permission = "hreis.notifications.view"
    write_permission = "hreis.notifications.view"

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        return self.queryset.none() if p is None else self.queryset.filter(recipient_id=p.user_id)
