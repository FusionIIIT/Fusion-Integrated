from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveBalanceEntry,
    NotificationRecord,
    RequestDecision,
)


class EmployeeServiceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeServiceRecord
        fields = (
            "id",
            "user_id",
            "employee_category",
            "appointment_details",
            "department_code",
            "designation",
            "service_history",
            "retirement_status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EmployeeServiceRecordWriteSerializer(serializers.Serializer):
    employee_category = serializers.ChoiceField(
        choices=[value for value, _ in EmployeeServiceRecord.EMPLOYEE_CATEGORIES], required=False
    )
    appointment_details = serializers.JSONField(required=False)
    department_code = serializers.CharField(max_length=80, required=False)
    designation = serializers.CharField(max_length=120, required=False)
    service_history = serializers.ListField(child=serializers.JSONField(), required=False)
    retirement_status = serializers.CharField(max_length=40, required=False)


class RequestDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestDecision
        fields = (
            "from_state",
            "event",
            "to_state",
            "actor_user_id",
            "actor_role",
            "note",
            "created_at",
        )
        read_only_fields = fields


class HRRequestSerializer(serializers.ModelSerializer):
    decisions = serializers.SerializerMethodField()

    class Meta:
        model = HRRequest
        fields = (
            "id",
            "owner_user_id",
            "request_type",
            "state",
            "cycle_key",
            "data",
            "created_at",
            "updated_at",
            "decisions",
        )
        read_only_fields = fields

    @extend_schema_field(RequestDecisionSerializer(many=True))
    def get_decisions(self, obj):
        return RequestDecisionSerializer(obj.decisions.all(), many=True).data


class CreateRequestSerializer(serializers.Serializer):
    request_type = serializers.ChoiceField(choices=[value for value, _ in HRRequest.REQUEST_TYPES])
    data = serializers.DictField()


class HRRequestTransitionSerializer(serializers.Serializer):
    event = serializers.ChoiceField(
        choices=(
            "assign_reviewers",
            "verify",
            "approve",
            "reject",
            "forward",
            "finalize",
            "process",
        )
    )
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    details = serializers.DictField(required=False)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicyVersion
        fields = (
            "id",
            "policy_name",
            "version",
            "effective_from",
            "effective_to",
            "payload",
            "created_at",
        )
        read_only_fields = fields


class PolicyCreateSerializer(serializers.Serializer):
    policy_name = serializers.CharField(max_length=80)
    version = serializers.IntegerField(min_value=1)
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(required=False, allow_null=True, default=None)
    payload = serializers.DictField()


class BalanceAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    leave_type = serializers.CharField(max_length=32)
    delta_days = serializers.DecimalField(max_digits=8, decimal_places=2)
    reason = serializers.CharField(max_length=300)


class LeaveBalanceEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalanceEntry
        fields = (
            "id",
            "user_id",
            "leave_type",
            "delta_days",
            "request_id",
            "reason",
            "actor_user_id",
            "created_at",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecord
        fields = ("id", "topic", "request_id", "payload", "created_at", "read_at")
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "user_id",
            "actor_user_id",
            "actor_role",
            "action",
            "resource_type",
            "resource_id",
            "details",
            "occurred_at",
        )
        read_only_fields = fields
