from rest_framework import serializers
from ..models import LeaveBalance, LeaveApplication, LeaveAction, LeaveCategory
from ..domain.rules import calculate_leave_days, validate_substitute


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "leave_type",
            "allocated",
            "used",
            "balance",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "updated_at"]


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = [
            "id",
            "application",
            "actor_id",
            "action",
            "comments",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)
    calculated_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "substitute_id",
            "substitute_status",
            "is_station_leave",
            "station_address",
            "half_day",
            "half_day_type",
            "unit_head_id",
            "unit_head_recommendation",
            "sanctioning_authority_id",
            "rejection_reason",
            "created_at",
            "updated_at",
            "actions",
            "calculated_days",
        ]
        read_only_fields = [
            "id",
            "applicant_id",
            "status",
            "substitute_status",
            "unit_head_recommendation",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def get_calculated_days(self, obj) -> float:
        try:
            return calculate_leave_days(obj.leave_type, obj.start_date, obj.end_date, obj.half_day)
        except Exception:
            return 0.0


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "substitute_id",
            "is_station_leave",
            "station_address",
            "half_day",
            "half_day_type",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        leave_type = attrs.get("leave_type")
        half_day = attrs.get("half_day", False)
        substitute_id = attrs.get("substitute_id")

        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})

        if half_day and leave_type != LeaveCategory.CL:
            raise serializers.ValidationError({"half_day": "Half-day option is only available for CL."})

        request = self.context.get("request")
        user_id = getattr(getattr(request, "user", None), "id", None) or getattr(getattr(request, "principal", None), "erp_user_id", None) or 1
        if substitute_id:
            try:
                validate_substitute(user_id, substitute_id)
            except ValueError as e:
                raise serializers.ValidationError({"substitute_id": str(e)})

        return attrs


class SubstituteActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class ApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")
