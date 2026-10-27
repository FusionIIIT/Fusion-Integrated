"""Leave API serializers."""
from rest_framework import serializers

from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)


# -- Categories -----------------------------------------------------------------
class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = ("code", "name", "description", "is_carry_forwardable")
        read_only_fields = fields


# -- Balances ------------------------------------------------------------------
class LeaveBalanceSerializer(serializers.ModelSerializer):
    category = LeaveCategorySerializer(read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "category", "category_code", "year",
                  "balance_days", "is_converted")
        read_only_fields = fields


# -- Transitions -----------------------------------------------------------------
class LeaveApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplicationTransition
        fields = ("id", "from_status", "to_status", "actor_user_id",
                  "actor_label", "reason", "at")
        read_only_fields = fields


# -- Applications --------------------------------------------------------------
class LeaveApplicationSerializer(serializers.ModelSerializer):
    category = LeaveCategorySerializer(read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id", "user_id", "category", "category_code", "status",
            "start_date", "end_date", "half_day", "days_charged",
            "balance_deducted", "reason", "is_station_leave",
            "station_details", "substitute_user_id",
            "substitute_response", "recommendation", "applicant_is_director",
            "withdrawn_reason", "actual_resumption_date",
            "resumption_status", "allowed_transitions", "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_allowed_transitions(self, obj) -> list[str]:
        from modules.leave.domain import state_machine as sm
        from modules.leave.services.applications import actor_kind
        actor = self.context.get("actor")
        return sm.allowed_targets(obj.status, actor_kind(actor, obj) if actor else None)


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category_code = serializers.CharField(max_length=3)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.CharField(max_length=6, required=False,
                                     allow_blank=True, default="")
    reason = serializers.CharField()
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_details = serializers.DictField(required=False, default=dict)
    substitute_user_id = serializers.IntegerField(required=False,
                                                  allow_null=True, default=None)
    applicant_is_director = serializers.BooleanField(required=False,
                                                     default=False)
    medical_evidence_ref = serializers.CharField(max_length=300,
                                                 required=False,
                                                 allow_blank=True, default="")


class LeaveApplicationTransitionInputSerializer(serializers.Serializer):
    to_status = serializers.CharField(max_length=40)
    reason = serializers.CharField(required=False, allow_blank=True,
                                     default="")
    recommendation = serializers.CharField(required=False,
                                           allow_blank=True, default="")
    replacement_substitute_id = serializers.IntegerField(required=False,
                                                        allow_null=True, default=None)
