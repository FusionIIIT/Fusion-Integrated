from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.models import LeaveBalance, LeaveEvent
from modules.elm.serializers import LeaveBalanceSerializer
from modules.elm.validation import locked_employee
from modules.elm.workflows import renominate, submit, substitute_response, withdraw

from .models import LeavePolicy, LeaveRequest, LeaveType
from .serializers import LeavePolicySerializer, LeaveRequestSerializer, LeaveTypeSerializer


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave requests.
    """

    http_method_names = ["get", "post", "head", "options"]
    queryset = LeaveRequest.objects.all()

    def get_queryset(self):
        from django.db.models import Q

        principal = getattr(self.request, "principal", None)
        if not principal:
            return LeaveRequest.objects.none()
        queryset = (
            LeaveRequest.objects.all().select_related("leave_type").prefetch_related("events")
        )
        if principal.has_permission("elm.leave_records.manage"):
            return queryset.order_by("-created_at")
        scope = Q(employee=principal.user_id) | Q(substitute=principal.user_id)
        if principal.has_permission("elm.leave_requests.approve"):
            scope |= Q(route__contains=principal.user_id)
        return queryset.filter(scope).order_by("-created_at")

    serializer_class = LeaveRequestSerializer

    def get_permissions(self):
        if self.action == "offline_sync":
            permission_classes = [
                IsAuthenticatedPrincipal,
                HasModuleGrant("elm"),
                HasPermission("elm.leave_records.manage"),
            ]
        elif self.action in ["create", "withdraw", "renominate", "amend"]:
            # existing body remains
            permission_classes = [
                IsAuthenticatedPrincipal,
                HasModuleGrant("elm"),
                HasPermission("elm.leave_requests.apply"),
            ]
        elif self.action == "decide":
            permission_classes = [
                IsAuthenticatedPrincipal,
                HasModuleGrant("elm"),
                HasPermission("elm.leave_requests.approve"),
            ]
        else:
            permission_classes = [
                IsAuthenticatedPrincipal,
                HasModuleGrant("elm"),
                HasPermission("elm.leave_requests.view"),
            ]
        return [cls() for cls in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = submit(serializer.validated_data, request.principal)
        return Response(self.get_serializer(req).data, status=201)

    @action(detail=False, methods=["post"], url_path="offline-sync")
    def offline_sync(self, request):
        from modules.elm.offline import OfflineMetadataSerializer, synchronize

        meta = OfflineMetadataSerializer(data=request.data)
        meta.is_valid(raise_exception=True)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(meta.validated_data)
        employee = values.pop("employee")
        req = synchronize(serializer.validated_data, employee, request.principal, **values)
        return Response(self.get_serializer(req).data, status=201)

    def perform_create(self, serializer):
        """
        Set created_at timestamp and associate with employee.
        """
        serializer.save(employee=self.request.principal.user_id)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        obj = self.get_object()
        req = withdraw(obj.pk, request.principal)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        from modules.elm.decisions import decide as decide_leave

        obj = self.get_object()
        req = decide_leave(
            obj.pk,
            request.principal,
            request.data.get("decision", ""),
            request.data.get("notes", ""),
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"], url_path="substitute-response")
    def substitute_response(self, request, pk=None):
        obj = self.get_object()
        req = substitute_response(obj.pk, request.principal, request.data.get("accept"))
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def renominate(self, request, pk=None):
        obj = self.get_object()
        req = renominate(obj.pk, request.principal, request.data.get("substitute"))
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def amend(self, request, pk=None):
        from rest_framework import serializers
        from rest_framework.exceptions import ValidationError

        from modules.elm.amendments import cancel_request, extension_request, resumption_request

        obj = self.get_object()
        operation = request.data.get("operation")

        if operation == "CANCELLATION":
            child = cancel_request(obj.pk, request.principal)
        elif operation == "EXTENSION":
            serializer = self.get_serializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            end = serializers.DateField().run_validation(request.data.get("end_date"))
            child = extension_request(obj.pk, request.principal, end, serializer.validated_data)
        elif operation == "RESUMPTION":
            actual = serializers.DateField().run_validation(request.data.get("actual_return_date"))
            notes = serializers.CharField(allow_blank=False).run_validation(
                request.data.get("notes")
            )
            child = resumption_request(obj.pk, request.principal, actual, notes)
        else:
            raise ValidationError("Unknown amendment operation")

        return Response(self.get_serializer(child).data, status=201)

    def update(self, request, *args, **kwargs):
        """
        Handle leave request updates with validation.
        """
        instance = self.get_object()
        if instance.status in ["APPROVED", "CANCELLED"]:
            return Response(
                {"error": "Cannot modify approved or cancelled requests"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

    def get_permissions(self):
        code = "elm.leave_balances.manage" if self.action == "adjust" else "elm.leave_balances.view"
        return [IsAuthenticatedPrincipal(), HasModuleGrant("elm")(), HasPermission(code)()]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if not principal:
            return LeaveBalance.objects.none()
        if principal.has_permission("elm.leave_balances.manage"):
            return LeaveBalance.objects.all().order_by("employee", "year", "id")
        return LeaveBalance.objects.filter(employee=principal.user_id).order_by(
            "employee", "year", "id"
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def adjust(self, request, pk=None):
        obj = self.get_object()
        reason = request.data.get("reason", "")
        evidence = request.data.get("evidence", "")
        if not reason or not evidence:
            raise ValidationError("Reason and evidence are required")

        locked_employee(obj.employee)
        from modules.elm.validation import ensure_open_year

        ensure_open_year(obj.employee, obj.year)
        row = LeaveBalance.objects.select_for_update().get(pk=obj.pk)

        balance_data = request.data.get("balance")
        if balance_data is None:
            raise ValidationError("Balance is required")

        try:
            new_balance = serializers.DecimalField(
                max_digits=10, decimal_places=2, min_value=0
            ).run_validation(balance_data)
        except serializers.ValidationError as e:
            raise ValidationError(e.detail) from None

        delta = new_balance - row.balance
        row.balance = new_balance
        row.last_updated = timezone.now()
        row.save()

        LeaveEvent.objects.create(
            employee=row.employee,
            actor=request.principal.user_id,
            action="BALANCE_CORRECTED",
            delta=delta,
            details={
                "reason": reason.strip(),
                "evidence": evidence.strip(),
                "year": row.year,
                "leave_type": row.leave_type_id,
            },
        )

        return Response(self.get_serializer(row).data)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave types.
    """

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "metadata"):
            code = (
                "elm.leave_types.view"
                if self.queryset.model is LeaveType
                else "elm.leave_policies.view"
            )
        else:
            code = "elm.leave_policies.manage"
        return [IsAuthenticatedPrincipal(), HasModuleGrant("elm")(), HasPermission(code)()]


class LeavePolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing leave policies.
    """

    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "metadata"):
            code = (
                "elm.leave_types.view"
                if self.queryset.model is LeaveType
                else "elm.leave_policies.view"
            )
        else:
            code = "elm.leave_policies.manage"
        return [IsAuthenticatedPrincipal(), HasModuleGrant("elm")(), HasPermission(code)()]

    def get_queryset(self):
        """
        Filter policies by leave type if specified.
        """
        queryset = super().get_queryset()
        type_filter = self.request.query_params.get("type")
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        return queryset


# Add year-end processing and SLA reminder logic here
