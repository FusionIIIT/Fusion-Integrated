"""Typed boundary validation. Monetary fields never pass through binary floats."""

from rest_framework import serializers

from modules.iaa.domain.rules import AUTHORITIES, Role
from modules.iaa.models import (
    Anomaly,
    ApprovalRoute,
    AuditEntry,
    Budget,
    Clarification,
    Department,
    FinancialRequest,
    FinancialYear,
    Notification,
    Observation,
    Policy,
    RoleAssignment,
)


class DocumentsField(serializers.ListField):
    # References are never fetched by the server. Only HTTPS links are accepted.
    child = serializers.URLField(max_length=2000)
    max_length = 20

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        if any(not value.startswith("https://") for value in values):
            raise serializers.ValidationError("Evidence links must use HTTPS.")
        return values


class RequestWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["expense", "ta"])
    request_type = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    department = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    description = serializers.CharField(
        max_length=10000, required=False, allow_blank=True, default=""
    )
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True, default=None
    )
    documents = DocumentsField(required=False, default=list)
    trip_start = serializers.DateField(required=False, allow_null=True, default=None)
    trip_end = serializers.DateField(required=False, allow_null=True, default=None)


class RemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=10000)


class FinanceSerializer(RemarksSerializer):
    compliant = serializers.BooleanField(default=True)


class DecisionSerializer(RemarksSerializer):
    approve = serializers.BooleanField()


class RecordSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=255)


class ResponseSerializer(serializers.Serializer):
    response = serializers.CharField(max_length=10000)
    evidence = DocumentsField(required=False, default=list)


class AnomalyWriteSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=80)
    description = serializers.CharField(max_length=10000)


class ResolveSerializer(RemarksSerializer):
    escalate = serializers.BooleanField(default=False)


class ObservationWriteSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=10000)
    respondent_id = serializers.IntegerField(min_value=1, required=False)


class VerifySerializer(serializers.Serializer):
    satisfactory = serializers.BooleanField()
    verification = serializers.CharField(max_length=10000)


class SwitchSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[r.value for r in Role])


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = [
            "id",
            "actor_id",
            "active_role",
            "action",
            "object_type",
            "object_id",
            "from_status",
            "to_status",
            "details",
            "at",
        ]


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialRequest
        fields = [
            "id",
            "creator_id",
            "creator_role",
            "kind",
            "request_type",
            "department",
            "description",
            "amount",
            "documents",
            "trip_start",
            "trip_end",
            "status",
            "finance_user_id",
            "recovery_note",
            "year_id",
            "route_snapshot",
            "route_index",
            "assignee_id",
            "assignee_role",
            "assigned_at",
            "reservation",
            "processing_reference",
            "created_at",
            "submitted_at",
            "recorded_at",
        ]
        read_only_fields = fields


class ClarificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clarification
        fields = ["id", "query", "asked_by", "response", "evidence", "asked_at", "responded_at"]


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = "__all__"


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = "__all__"


class IaaRequestDetailSerializer(RequestSerializer):
    history = AuditSerializer(many=True, read_only=True)
    clarifications = ClarificationSerializer(many=True, read_only=True)
    anomalies = AnomalySerializer(many=True, read_only=True)
    observations = ObservationSerializer(many=True, read_only=True)

    class Meta(RequestSerializer.Meta):
        fields = [
            *RequestSerializer.Meta.fields,
            "history",
            "clarifications",
            "anomalies",
            "observations",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "event", "message", "request_id", "at"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = "__all__"


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class PolicySerializer(serializers.ModelSerializer):
    anomaly_resolver_role = serializers.ChoiceField(
        choices=[r.value for r in Role if r != Role.ADMIN and r != Role.BASIC]
    )
    anomaly_escalation_role = serializers.ChoiceField(
        choices=[r.value for r in Role], allow_blank=True, required=False
    )

    class Meta:
        model = Policy
        fields = "__all__"


class StepSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=sorted(AUTHORITIES))
    timeout_hours = serializers.IntegerField(min_value=1, max_value=8760)


class RouteSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True, allow_empty=False, max_length=10)

    class Meta:
        model = ApprovalRoute
        fields = "__all__"


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = "__all__"


CONFIG_SERIALIZERS = {
    "roles": RoleSerializer,
    "years": YearSerializer,
    "departments": DepartmentSerializer,
    "policies": PolicySerializer,
    "routes": RouteSerializer,
    "budgets": BudgetSerializer,
}
