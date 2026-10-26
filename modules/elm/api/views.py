from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models import Q
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from fusion_auth.permissions import HasModuleGrant

from .. import services
from ..models import Employee, HolidayCalendar, LeaveApplication, LeavePolicy, LeaveState
from .serializers import (
    ApplicationInputSerializer,
    DecisionInputSerializer,
    EmployeeSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationSerializer,
    LeavePolicySerializer,
    SubstituteInputSerializer,
)

MODULE = HasModuleGrant("elm_leave")


def _employee_for(request):
    if hasattr(request, "_elm_employee"):
        return request._elm_employee
    principal = getattr(request, "principal", None)
    user_id = getattr(principal, "user_id", None)
    employee = (
        Employee.objects.select_related("user", "unit")
        .filter(
            user_id=user_id,
            user__is_active=True,
            user__kind__in=["staff", "faculty"],
        )
        .first()
        if user_id is not None
        else None
    )
    if employee is None:
        raise PermissionDenied("No active ELM employee is linked to the logged-in user.")
    request._elm_employee = employee
    return employee


class EmployeeAccess:
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        _employee_for(request)


class LeavePolicyViewSet(EmployeeAccess, ReadOnlyModelViewSet):
    queryset = LeavePolicy.objects.all().order_by("-id")
    serializer_class = LeavePolicySerializer
    permission_classes = [MODULE]


class HolidayCalendarViewSet(EmployeeAccess, ReadOnlyModelViewSet):
    queryset = HolidayCalendar.objects.filter(is_published=True).order_by("-published_at", "-id")
    serializer_class = HolidayCalendarSerializer
    permission_classes = [MODULE]


class EmployeeViewSet(EmployeeAccess, ReadOnlyModelViewSet):
    queryset = Employee.objects.filter(
        user__is_active=True,
        user__kind__in=["staff", "faculty"],
    ).order_by("name", "id")
    serializer_class = EmployeeSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return self.queryset.exclude(pk=_employee_for(self.request).pk)


class LeaveApplicationViewSet(
    EmployeeAccess,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = LeaveApplication.objects.select_related(
        "applicant",
        "substitute",
        "unit_head",
        "sanctioning_authority",
    )
    serializer_class = LeaveApplicationSerializer
    permission_classes = [MODULE]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["employee"] = _employee_for(self.request)
        return context

    def get_queryset(self):
        employee = _employee_for(self.request)
        principal = getattr(self.request, "principal", None)
        scope = (
            Q(applicant=employee)
            | Q(substitute=employee)
            | Q(unit_head=employee)
            | Q(sanctioning_authority=employee)
        )
        establishment = services.establishment_allowed(principal, services.current_hierarchy())
        if establishment:
            scope |= Q(state=LeaveState.AWAITING_ESTABLISHMENT)
        queryset = self.queryset.filter(scope)
        task = self.request.query_params.get("task")
        if task == "mine":
            queryset = queryset.filter(applicant=employee)
        elif task == "substitute":
            queryset = queryset.filter(substitute=employee, state=LeaveState.AWAITING_SUBSTITUTE)
        elif task == "unit-head":
            queryset = queryset.filter(unit_head=employee, state=LeaveState.AWAITING_UNIT_HEAD)
        elif task == "sanction":
            tasks = Q(sanctioning_authority=employee, state=LeaveState.AWAITING_FINAL) | Q(
                applicant=employee, applicant__is_director=True, state=LeaveState.AWAITING_DIRECTOR
            )
            if establishment:
                tasks |= Q(state=LeaveState.AWAITING_ESTABLISHMENT)
            queryset = queryset.filter(tasks)
        return queryset.order_by("-created_at", "-id")

    def create(self, request, *args, **kwargs):
        payload = ApplicationInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            application = services.apply_leave(
                applicant=_employee_for(request),
                **payload.validated_data,
            )
        except ModelValidationError as exc:
            raise serializers.ValidationError({"detail": "; ".join(exc.messages)}) from exc
        return Response(self.get_serializer(application).data, status=status.HTTP_201_CREATED)

    def _workflow_action(self, request, action_name, service, actor_name=None, payload_class=None):
        application = self.get_object()
        allowed = self.get_serializer(application).data["allowed_actions"]
        if action_name not in allowed:
            raise PermissionDenied("This task is not assigned to you or is no longer actionable.")
        values = {}
        if payload_class:
            payload = payload_class(data=request.data)
            payload.is_valid(raise_exception=True)
            values.update(payload.validated_data)
        if actor_name:
            values[actor_name] = _employee_for(request)
        if action_name == "substitute-response":
            values["accepted"] = values.pop("accept")
        if action_name == "establishment-route":
            values["role"] = services.current_hierarchy().establishment_role
        try:
            result = service(application=application, **values)
        except ModelValidationError as exc:
            raise serializers.ValidationError({"detail": "; ".join(exc.messages)}) from exc
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"], url_path="substitute-response")
    def substitute_response(self, request, pk=None):
        return self._workflow_action(
            request,
            "substitute-response",
            services.respond_to_substitute,
            "substitute",
            SubstituteInputSerializer,
        )

    @action(detail=True, methods=["post"], url_path="unit-head-review")
    def unit_head_review(self, request, pk=None):
        return self._workflow_action(
            request,
            "unit-head-review",
            services.review_leave,
            "unit_head",
            DecisionInputSerializer,
        )

    @action(detail=True, methods=["post"], url_path="establishment-route")
    def establishment_route(self, request, pk=None):
        return self._workflow_action(request, "establishment-route", services.route_establishment)

    @action(detail=True, methods=["post"], url_path="final-decision")
    def final_decision(self, request, pk=None):
        return self._workflow_action(
            request,
            "final-decision",
            services.make_final_decision,
            "actor",
            DecisionInputSerializer,
        )

    @action(detail=True, methods=["post"], url_path="director-decision")
    def director_decision(self, request, pk=None):
        return self._workflow_action(
            request,
            "director-decision",
            services.make_director_decision,
            "actor",
            DecisionInputSerializer,
        )
