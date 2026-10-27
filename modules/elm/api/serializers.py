"""Explicit ELM request input and safe own-request output serializers."""

from rest_framework import serializers

from modules.elm.models import LeaveRequest, LeaveWorkflowAction


class ELMMetadataSerializer(serializers.Serializer):
    label = serializers.CharField()
    description = serializers.CharField()
    version = serializers.CharField()


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"non_field_errors": [f"Unsupported field(s): {', '.join(sorted(unknown))}."]}
            )
        return super().to_internal_value(data)


class LeaveRequestSubmissionSerializer(StrictSerializer):
    leave_type = serializers.ChoiceField(choices=LeaveRequest.LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(trim_whitespace=True)
    half_day = serializers.ChoiceField(
        choices=LeaveRequest.HalfDay.choices,
        required=False,
        allow_null=True,
        default=None,
    )
    substitute_user_id = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        if not attrs["purpose"]:
            raise serializers.ValidationError({"purpose": "Purpose or reason is required."})
        half_day = attrs.get("half_day")
        if half_day is not None:
            if attrs["leave_type"] != "CL":
                raise serializers.ValidationError(
                    {"half_day": "Half-day requests are supported only for CL."}
                )
            if attrs["start_date"] != attrs["end_date"]:
                raise serializers.ValidationError(
                    {"half_day": "A CL half-day must cover one date."}
                )
        return attrs


class LeaveDecisionSerializer(StrictSerializer):
    decision = serializers.ChoiceField(
        choices=(
            "RECOMMENDED",
            "NOT_RECOMMENDED",
            "PROCESSED",
            "APPROVED",
            "REJECTED",
        )
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveWithdrawalSerializer(StrictSerializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(StrictSerializer):
    decision = serializers.ChoiceField(choices=("ACCEPTED", "DECLINED"))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteNominationSerializer(StrictSerializer):
    substitute_user_id = serializers.IntegerField(min_value=1)


class LeaveWorkflowActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveWorkflowAction
        fields = ("from_status", "to_status", "action", "actor_role", "reason", "at")
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    workflow_actions = LeaveWorkflowActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "leave_type",
            "start_date",
            "end_date",
            "purpose",
            "half_day",
            "chargeable_days",
            "status",
            "created_at",
            "submitted_at",
            "workflow_actions",
        )
        read_only_fields = fields
