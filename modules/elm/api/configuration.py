"""Authorized configuration APIs with validation and audit records."""

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers
from rest_framework.response import Response

from core.api.exceptions import DomainError
from modules.directory.contracts import get_users
from modules.elm.domain.state_machine import CREDITS
from modules.elm.models import ConfigurationAudit, EmployeeRecord, HolidayCalendar, LeavePolicy

from .serializers import CalendarRecordSerializer, CalendarResultSerializer
from .views import ElmView


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"fields": f"Unsupported fields: {', '.join(sorted(unknown))}"}
            )
        return super().to_internal_value(data)


class RouteStepSerializer(StrictSerializer):
    user_id = serializers.RegexField(r"^[1-9][0-9]*$", max_length=64)
    role = serializers.ChoiceField(
        choices=["unit_head", "establishment", "deputy_registrar", "dean", "registrar", "director"]
    )


class EmployeeSerializer(StrictSerializer):
    user_id = serializers.RegexField(r"^[1-9][0-9]*$", max_length=64)
    kind = serializers.ChoiceField(choices=["faculty", "staff"])
    unit = serializers.CharField(max_length=128)
    designation = serializers.CharField(max_length=128)
    is_director = serializers.BooleanField(default=False)
    coverage_required = serializers.BooleanField(default=False)
    col_eligible = serializers.BooleanField(default=True)
    routes = serializers.DictField(child=RouteStepSerializer(many=True), default=dict)
    escalation_user_id = serializers.RegexField(
        r"^[1-9][0-9]*$", required=False, allow_blank=True, default="", max_length=64
    )
    is_active = serializers.BooleanField(default=True)

    def validate(self, data):
        if set(data["routes"]) - set(CREDITS):
            raise serializers.ValidationError("Routes contain an unsupported leave category.")
        for category, route in data["routes"].items():
            if not route or route[0]["role"] != "unit_head":
                raise serializers.ValidationError(
                    "Each route starts with the applicant's Unit Head."
                )
            if category in {"CL", "RH"} and len(route) != 1:
                raise serializers.ValidationError("CL and RH end at the Unit Head.")
            if category not in {"CL", "RH"} and (
                len(route) < 2 or route[-1]["role"] in {"unit_head", "establishment"}
            ):
                raise serializers.ValidationError(
                    "Higher leave requires a final sanctioning authority after Unit Head review."
                )
            if any(step["user_id"] == data["user_id"] for step in route):
                raise serializers.ValidationError("Normal routes cannot include the applicant.")
        return data


class PolicySerializer(StrictSerializer):
    annual_credits = serializers.DictField(
        child=serializers.DecimalField(max_digits=7, decimal_places=2, min_value=0), required=False
    )
    weekend_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False, max_length=6
    )
    medical_evidence_required = serializers.BooleanField(required=False)
    reminder_hours = serializers.IntegerField(min_value=1, required=False)
    escalation_hours = serializers.IntegerField(min_value=2, required=False)

    def validate(self, data):
        if set(data.get("annual_credits", {})) - set(CREDITS):
            raise serializers.ValidationError("Unsupported leave category.")
        p = self.context["policy"]
        if data.get("reminder_hours", p.reminder_hours) >= data.get(
            "escalation_hours", p.escalation_hours
        ):
            raise serializers.ValidationError("Escalation must occur after the reminder threshold.")
        if "annual_credits" in data:
            data["annual_credits"] = {k: str(v) for k, v in data["annual_credits"].items()}
        return data


class CalendarSerializer(StrictSerializer):
    year = serializers.IntegerField(min_value=1900, max_value=2200)
    closed_dates = serializers.ListField(child=serializers.DateField(), default=list)
    restricted_dates = serializers.ListField(child=serializers.DateField(), default=list)
    publish = serializers.BooleanField(default=False)

    def validate(self, data):
        for field in ["closed_dates", "restricted_dates"]:
            if any(d.year != data["year"] for d in data[field]):
                raise serializers.ValidationError("All dates must belong to the calendar year.")
            data[field] = sorted({d.isoformat() for d in data[field]})
        return data


def audit(actor, resource, payload):
    ConfigurationAudit.objects.create(
        actor_user_id=str(actor.user_id), resource=resource, payload=payload
    )


@extend_schema_view(
    get=extend_schema(
        responses=EmployeeSerializer(many=True), operation_id="elm_employee_profiles"
    ),
    post=extend_schema(
        request=EmployeeSerializer,
        responses=EmployeeSerializer,
        operation_id="elm_configure_employee",
    ),
)
class EmployeeConfigView(ElmView):
    permission_code = "elm.leave.admin"

    def get(self, request):
        return Response(list(EmployeeRecord.objects.order_by("user_id").values()))

    @transaction.atomic
    def post(self, request):
        s = EmployeeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        ids = {data["user_id"], data["escalation_user_id"]} - {""}
        ids.update(step["user_id"] for route in data["routes"].values() for step in route)
        known = get_users([int(i) for i in ids])
        if any(int(i) not in known or known[int(i)].kind not in {"faculty", "staff"} for i in ids):
            raise DomainError(
                "Every employee and assigned authority must be a known "
                "Fusion faculty/staff identity."
            )
        if known[int(data["user_id"])].kind != data["kind"]:
            raise DomainError("Employee category must match the Fusion directory.")
        user_id = data.pop("user_id")
        EmployeeRecord.objects.update_or_create(user_id=user_id, defaults=data)
        audit(request.principal, f"employee:{user_id}", s.data)
        return Response({"user_id": user_id, **data})


@extend_schema_view(
    get=extend_schema(responses=PolicySerializer, operation_id="elm_policy"),
    post=extend_schema(
        request=PolicySerializer, responses=PolicySerializer, operation_id="elm_configure_policy"
    ),
)
class PolicyView(ElmView):
    permission_code = "elm.leave.admin"

    def get(self, request):
        p = LeavePolicy.objects.filter(pk=1).first() or LeavePolicy()
        return Response(
            {
                "annual_credits": {**CREDITS, **p.annual_credits},
                "weekend_days": p.weekend_days or [5, 6],
                "medical_evidence_required": p.medical_evidence_required,
                "reminder_hours": p.reminder_hours,
                "escalation_hours": p.escalation_hours,
            }
        )

    @transaction.atomic
    def post(self, request):
        p, _ = LeavePolicy.objects.get_or_create(pk=1)
        p = LeavePolicy.objects.select_for_update().get(pk=1)
        s = PolicySerializer(data=request.data, context={"policy": p})
        s.is_valid(raise_exception=True)
        for field, value in s.validated_data.items():
            setattr(p, field, value)
        p.save()
        audit(request.principal, "policy", dict(s.validated_data))
        return self.get(request)


@extend_schema_view(
    get=extend_schema(responses=CalendarRecordSerializer(many=True), operation_id="elm_calendars"),
    post=extend_schema(
        request=CalendarSerializer,
        responses={201: CalendarResultSerializer},
        operation_id="elm_create_calendar",
    ),
)
class CalendarView(ElmView):
    permission_code = "elm.leave.admin"

    def get(self, request):
        return Response(list(HolidayCalendar.objects.order_by("-created_at").values()))

    @transaction.atomic
    def post(self, request):
        s = CalendarSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = dict(s.validated_data)
        publish = data.pop("publish")
        cal = HolidayCalendar.objects.create(
            **data, published_at=timezone.now() if publish else None
        )
        audit(request.principal, f"calendar:{cal.pk}", s.data)
        return Response({"id": cal.pk, "published_at": cal.published_at}, status=201)
