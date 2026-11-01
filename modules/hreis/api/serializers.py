from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from modules.hreis.domain.policy import HRPolicy
from modules.hreis.models import (
    Appraisal,
    AppraisalWindow,
    AuditEntry,
    Claim,
    EmployeeRecord,
    LeaveRequest,
    Notification,
    WorkflowRoute,
)


class EmployeeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_service_history(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Service history must be an array.")
        return value

    def validate_leave_balances(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Leave balances must be an object keyed by leave type."
            )
        types = {name for name, _ in LeaveRequest.TYPES}
        normalized = {}
        for key, amount in value.items():
            if key not in types:
                raise serializers.ValidationError(f"Unsupported leave type: {key}")
            try:
                balance = Decimal(str(amount))
            except (TypeError, ValueError, InvalidOperation) as exc:
                raise serializers.ValidationError(f"Invalid balance for {key}.") from exc
            if not balance.is_finite() or balance < 0:
                raise serializers.ValidationError(
                    f"Leave balance for {key} must be finite and nonnegative."
                )
            normalized[key] = str(balance)
        return normalized


class WorkflowRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRoute
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_authorities(self, roles):
        try:
            validated = list(HRPolicy.validate_authorities(roles))
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if any(role not in ("HOD", "Registrar", "Director") for role in validated):
            raise serializers.ValidationError("Authorities must be HOD, Registrar, or Director.")
        return validated


class AppraisalWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalWindow
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, data):
        if data["opens_at"] >= data["closes_at"]:
            raise serializers.ValidationError("Submission window must end after it opens.")
        return data


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "id",
            "record",
            "status",
            "current_step",
            "approval_roles",
            "created_at",
            "updated_at",
        )

    def validate_days(self, days):
        if days <= 0:
            raise serializers.ValidationError("Duration must be positive.")
        return days

    def validate_justification(self, value):
        if not value.strip():
            raise serializers.ValidationError("Justification is required.")
        return value


class AppraisalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appraisal
        fields = "__all__"
        read_only_fields = (
            "id",
            "record",
            "reviewer_roles",
            "current_step",
            "status",
            "submitted_at",
            "closed_at",
        )


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = "__all__"
        read_only_fields = (
            "id",
            "record",
            "status",
            "current_step",
            "approval_roles",
            "payment_status",
            "payment_reference",
            "submitted_at",
            "updated_at",
        )

    def validate_documents(self, value):
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)
        ):
            raise serializers.ValidationError("Supporting document references are required.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value

    def validate_purpose(self, value):
        if not value.strip():
            raise serializers.ValidationError("Purpose must not be blank.")
        return value


class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = "__all__"
        read_only_fields = tuple(
            fields
            for fields in (
                "id",
                "entity_type",
                "entity_id",
                "action",
                "actor_id",
                "detail",
                "occurred_at",
            )
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("id", "user_id", "kind", "message", "created_at", "read_at")
