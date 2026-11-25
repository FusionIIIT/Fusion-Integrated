from rest_framework import serializers
from modules.elm.models import LeaveAction, LeaveBalance, LeaveRequest


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.DecimalField(max_digits=7, decimal_places=2,
                                              read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "year", "category", "entitled_days",
                  "carried_forward_days", "consumed_days", "available_days")
        read_only_fields = fields


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = ("id", "actor_user_id", "action", "note", "from_status",
                  "to_status", "created_at")
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ("id", "applicant_user_id", "category", "start_date", "end_date",
                  "half_day", "reason", "station_leave_required",
                  "station_leave_details", "substitute_user_id",
                  "substitute_response", "status", "current_reviewer_user_id",
                  "final_decision_by_user_id", "final_decision_at",
                  "decision_note", "actions", "created_at", "updated_at")
        read_only_fields = ("id", "applicant_user_id", "substitute_response",
                            "status", "current_reviewer_user_id",
                            "final_decision_by_user_id", "final_decision_at",
                            "decision_note", "actions", "created_at", "updated_at")


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=("full", "first", "second"),
                                        default="full")
    reason = serializers.CharField(max_length=4000)
    station_leave_required = serializers.BooleanField(default=False)
    station_leave_details = serializers.CharField(required=False, allow_blank=True,
                                                  default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({
                "end_date": "End date must not precede start date."
            })

        if (
            attrs["station_leave_required"]
            and not attrs["station_leave_details"].strip()
        ):
            raise serializers.ValidationError({
                "station_leave_details":
                    "Details are required when Station Leave applies."
            })

        substitute_user_id = attrs.get("substitute_user_id")
        if substitute_user_id is not None and substitute_user_id <= 0:
            raise serializers.ValidationError({
                "substitute_user_id": "Invalid employee id."
            })

        if (
            attrs["half_day"] in ("first", "second")
            and attrs["start_date"] != attrs["end_date"]
        ):
            raise serializers.ValidationError({
                "half_day":
                    "Half-day leave must have the same start and end date."
            })

        return attrs

class LeaveDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("recommend", "not_recommend",
                                              "approve", "reject", "withdraw",
                                              "substitute_accept", "substitute_decline"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=4000,
                                  default="")
