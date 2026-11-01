from rest_framework import serializers

from .models import (
    AuditEvent,
    EmployeeRecord,
    HRRequest,
    LeaveAccount,
    LeavePolicy,
    Notification,
    WorkflowRoute,
)


class EmployeeRecordSerializer(serializers.ModelSerializer):
    service_history = serializers.JSONField(required=False)

    class Meta:
        model = EmployeeRecord
        fields = (
            "id",
            "user_id",
            "category",
            "department",
            "designation",
            "appointment_date",
            "service_history",
            "retired",
            "created_at",
            "updated_at",
        )

    def validate_user_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("A positive external user ID is required.")
        if self.instance and self.instance.user_id != value:
            raise serializers.ValidationError("User ID cannot be modified.")
        return value

    def validate_category(self, value):
        if value not in ["faculty", "staff"]:
            raise serializers.ValidationError("Category must be either 'faculty' or 'staff'.")
        return value

    def validate_service_history(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Service history must be a list.")
        return value


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "code", "label", "eligible_categories", "active")

    def validate_eligible_categories(self, value):
        if (
            not isinstance(value, list)
            or not value
            or not all(cat in ["faculty", "staff"] for cat in value)
            or len(set(value)) != len(value)
        ):
            raise serializers.ValidationError(
                "Use a non-empty list of unique faculty/staff categories."
            )
        return value


class LeaveAccountSerializer(serializers.ModelSerializer):
    created_at = serializers.ReadOnlyField()
    updated_at = serializers.ReadOnlyField()

    class Meta:
        model = LeaveAccount
        fields = ("id", "employee", "policy", "available", "created_at", "updated_at")

    def validate(self, attrs):
        if self.instance and any(
            key in attrs and attrs[key].pk != getattr(self.instance, key + "_id")
            for key in ("employee", "policy")
        ):
            raise serializers.ValidationError("Account owner and policy cannot be changed.")
        return attrs

    def validate_available(self, value):
        if value < 0:
            raise serializers.ValidationError("Available leave cannot be negative.")
        return value


class WorkflowRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRoute
        fields = ("id", "employee_category", "request_kind", "department", "steps", "active")

    def validate_steps(self, value):
        if (
            not isinstance(value, list)
            or not value
            or not all(type(step) is int and step > 0 for step in value)
            or len(set(value)) != len(value)
        ):
            raise serializers.ValidationError(
                "Steps must be a non-empty list of unique positive integers."
            )
        return value


class HRRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRRequest
        read_only_fields = (
            "id",
            "employee",
            "kind",
            "mode",
            "policy",
            "start_date",
            "end_date",
            "days",
            "purpose",
            "amount",
            "documents",
            "status",
            "route",
            "step",
            "created_at",
            "updated_at",
        )
        fields = read_only_fields


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        read_only_fields = (
            "id",
            "actor_id",
            "action",
            "employee",
            "request",
            "details",
            "created_at",
        )
        fields = read_only_fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        read_only_fields = ("id", "recipient_id", "request", "event", "payload", "created_at")
        fields = read_only_fields


class SubmitSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["LEAVE", "LTC", "CPDA"])
    mode = serializers.ChoiceField(
        choices=["ADVANCE", "REIMBURSEMENT"], allow_blank=True, default=""
    )
    policy = serializers.PrimaryKeyRelatedField(
        queryset=LeavePolicy.objects.all(), required=False, allow_null=True
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    purpose = serializers.CharField(max_length=4000, allow_blank=False)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False, default=0
    )
    documents = serializers.ListField(
        child=serializers.CharField(max_length=500, allow_blank=False), required=False, default=list
    )

    def to_internal_value(self, data):
        for key in data:
            if key not in [
                "kind",
                "mode",
                "policy",
                "start_date",
                "end_date",
                "purpose",
                "amount",
                "documents",
            ]:
                raise serializers.ValidationError({key: "This input field is not allowed."})
        return super().to_internal_value(data)


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["APPROVE", "REJECT", "FORWARD"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class SettlementSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=500, allow_blank=False)
