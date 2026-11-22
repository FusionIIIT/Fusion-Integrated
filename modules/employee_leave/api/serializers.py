from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.employee_leave.models import (
    LeaveBalance,
    LeaveDecision,
    LeaveHoliday,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRequest,
    LeaveTaskNotice,
    LeaveYearEndRun,
)


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = (
            "id",
            "leave_type",
            "leave_year",
            "enabled",
            "annual_entitlement",
            "carry_forward_limit",
            "year_end_treatment",
            "conversion_ratio",
            "max_continuous_days",
            "requires_substitute",
            "requires_higher_sanction",
            "faculty_only",
            "hierarchy",
            "unit_head_sla_hours",
            "final_sanction_sla_hours",
            "escalation_role",
        )

    def validate(self, attrs):
        current = self.instance

        def value(name, default=None):
            if name in attrs:
                return attrs[name]
            if current is not None:
                return getattr(current, name)
            field = LeavePolicy._meta.get_field(name)
            return field.get_default() if field.has_default() else default

        if value("annual_entitlement") < 0 or value("carry_forward_limit") < 0:
            raise serializers.ValidationError(
                "Annual entitlement and carry-forward limit cannot be negative."
            )
        ratio = value("conversion_ratio")
        if ratio <= 0:
            raise serializers.ValidationError("Conversion ratio must be greater than zero.")
        if value("year_end_treatment") == "convert_to_el" and value("leave_type") != "VL":
            raise serializers.ValidationError(
                "Only Vacation Leave may be converted to Earned Leave."
            )
        hierarchy = value("hierarchy", {})
        if not isinstance(hierarchy, dict):
            raise serializers.ValidationError("Hierarchy configuration must be an object.")
        final_role = hierarchy.get("final_role", "sanctioning_authority")
        if not isinstance(final_role, str) or not final_role.strip() or len(final_role) > 64:
            raise serializers.ValidationError("A valid final authority role is required.")
        establishment_required = hierarchy.get("establishment_required", False)
        if not isinstance(establishment_required, bool):
            raise serializers.ValidationError("establishment_required must be a boolean value.")
        if value("unit_head_sla_hours") <= 0 or value("final_sanction_sla_hours") <= 0:
            raise serializers.ValidationError("SLA thresholds must be greater than zero.")
        return attrs


class LeaveDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveDecision
        fields = (
            "actor_user_id",
            "actor_role",
            "action",
            "from_status",
            "to_status",
            "comment",
            "created_at",
        )
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    decisions = serializers.SerializerMethodField()
    requires_higher_sanction = serializers.BooleanField(
        source="policy.requires_higher_sanction", read_only=True
    )
    establishment_required = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "employee_id",
            "employee_name",
            "policy",
            "parent",
            "request_kind",
            "leave_type",
            "start_date",
            "end_date",
            "charged_days",
            "reason",
            "station_leave_details",
            "substitute_id",
            "half_day",
            "status",
            "assigned_role",
            "actual_resume_date",
            "actual_resume_details",
            "final_decision",
            "final_decision_at",
            "requires_higher_sanction",
            "establishment_required",
            "decisions",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_employee_name(self, obj) -> str:
        return self.context.get("employee_names", {}).get(obj.employee_id, str(obj.employee_id))

    @extend_schema_field(LeaveDecisionSerializer(many=True))
    def get_decisions(self, obj):
        return LeaveDecisionSerializer(obj.decisions.all(), many=True).data

    @extend_schema_field(serializers.BooleanField())
    def get_establishment_required(self, obj) -> bool:
        return bool(obj.policy.hierarchy.get("establishment_required", False))


class LeaveRequestCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "VL", "COL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    leave_year = serializers.IntegerField(required=False, min_value=2000, max_value=2200)
    half_day = serializers.BooleanField(required=False, default=False)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave_details = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )


class LeaveExtensionCreateSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=(
            "accept_substitute",
            "decline_substitute",
            "recommend",
            "route_establishment",
            "approve",
            "reject",
            "route_final",
            "return_to_unit_head",
            "withdraw",
            "request_cancellation",
            "nominate_substitute",
            "request_resumption",
            "review",
            "approve_cancellation",
            "reject_cancellation",
            "recommend_cancellation",
            "route_cancellation_establishment",
            "route_cancellation_final",
            "return_cancellation_to_unit_head",
        )
    )
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    replacement_substitute_id = serializers.IntegerField(required=False)
    actual_resume_date = serializers.DateField(required=False)
    actual_resume_details = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = serializers.CharField(source="policy.leave_type", read_only=True)
    leave_year = serializers.IntegerField(source="policy.leave_year", read_only=True)
    available = serializers.DecimalField(max_digits=9, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "user_id",
            "policy",
            "leave_type",
            "leave_year",
            "opening_balance",
            "credited",
            "used",
            "available",
        )
        read_only_fields = fields


class LeaveLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "request_id", "entry_type", "days", "description", "created_at")
        read_only_fields = fields


class LeaveBalanceSummarySerializer(serializers.Serializer):
    balances = LeaveBalanceSerializer(many=True)
    history = LeaveLedgerSerializer(many=True)


class LeaveHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHoliday
        fields = ("id", "leave_year", "day", "name", "restricted", "published")


class BalanceAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    policy_id = serializers.IntegerField(min_value=1)
    entry_type = serializers.ChoiceField(choices=("credit", "opening"))
    days = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    description = serializers.CharField(max_length=300)


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    leave_type = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "VL", "COL"))
    leave_year = serializers.IntegerField(min_value=2000, max_value=2200)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    half_day = serializers.BooleanField(required=False, default=False)


class YearEndProcessSerializer(serializers.Serializer):
    from_year = serializers.IntegerField(min_value=2000, max_value=2199)


class LeaveYearEndRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveYearEndRun
        fields = (
            "id",
            "from_year",
            "to_year",
            "balances_processed",
            "annual_credits",
            "carried_forward",
            "converted_to_el",
            "lapsed",
            "created_at",
        )
        read_only_fields = fields


class LeaveTaskNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTaskNotice
        fields = ("id", "request_id", "event", "message", "created_at", "read_at")
        read_only_fields = fields
