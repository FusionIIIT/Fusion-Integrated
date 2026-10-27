from rest_framework import serializers

from modules.leave.models import (
    HalfDay,
    LeaveAction,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    ReportingLine,
)


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = ["id", "actor_id", "action", "remark", "created_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "kind",
            "parent",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "days",
            "purpose",
            "station_leave",
            "station_address",
            "substitute_id",
            "substitute_status",
            "unit_head_id",
            "establishment_id",
            "sanctioning_authority_id",
            "unit_head_recommendation",
            "stage",
            "status",
            "assignee_id",
            "decided_at",
            "created_at",
            "actions",
        ]
        read_only_fields = (
            "user_id",
            "kind",
            "parent",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "days",
            "purpose",
            "station_leave",
            "station_address",
            "substitute_id",
            "substitute_status",
            "unit_head_id",
            "establishment_id",
            "sanctioning_authority_id",
            "unit_head_recommendation",
            "stage",
            "status",
            "assignee_id",
            "decided_at",
            "created_at",
            "actions",
        )


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=LeaveCategory.choices,
        required=True,
    )
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    half_day = serializers.ChoiceField(
        choices=HalfDay.choices,
        default=HalfDay.NONE,
    )
    purpose = serializers.CharField()
    station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(allow_blank=True, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError("End date must be after start date.")
        return attrs


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
            ("verify", "Verify"),
        ],
        required=True,
    )
    remark = serializers.CharField(allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class ReplaceSubstituteSerializer(serializers.Serializer):
    substitute_id = serializers.IntegerField(required=True)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        read_only=True,
    )

    class Meta:
        model = LeaveBalance
        fields = ["id", "category", "year", "entitled", "used", "available"]


class ReportingLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportingLine
        fields = ["user_id", "unit_head_id", "establishment_id", "sanctioning_authority_id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user_id"].read_only = True
