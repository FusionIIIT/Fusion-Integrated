from rest_framework import serializers

from modules.iaa.models import (
    ActionHistory, Anomaly, ApprovalRouteRule, AuditObservation, DepartmentBudget,
    Evidence, ExpenseVoucherRequest, FinancialYear, IaaNotification,
    IaaRoleAssignment, PolicyParameter, TravelAllowanceClaim,
)


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseVoucherRequest
        fields = ("id", "created_by_id", "department", "request_type", "amount",
                  "description", "supporting_information", "status", "submitted_at",
                  "recorded_at", "created_at", "updated_at")
        read_only_fields = ("id", "created_by_id", "status", "submitted_at",
                            "recorded_at", "created_at", "updated_at")


class ClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelAllowanceClaim
        fields = ("id", "claimant_user_id", "department", "trip_start", "trip_end",
                  "purpose", "claimed_amount", "trip_details", "status",
                  "submitted_at", "recorded_at", "created_at", "updated_at")
        read_only_fields = ("id", "claimant_user_id", "status", "submitted_at",
                            "recorded_at", "created_at", "updated_at")


class EvidenceSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = Evidence
        fields = ("id", "record_type", "record_id", "purpose", "file",
                  "original_filename", "uploaded_by_id", "uploaded_at")
        read_only_fields = ("id", "original_filename", "uploaded_by_id", "uploaded_at")


class ActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionHistory
        fields = ("id", "record_type", "record_id", "source_status",
                  "destination_status", "action", "actor_user_id", "actor_role",
                  "remarks", "details", "happened_at")


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = ("id", "record_type", "record_id", "category", "description",
                  "status", "resolver_role", "assigned_user_id", "created_by_id",
                  "created_by_role", "created_at", "resolved_at")
        read_only_fields = ("id", "status", "created_by_id", "created_by_role",
                            "created_at", "resolved_at")


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditObservation
        fields = ("id", "record_type", "record_id", "auditor_user_id", "department",
                  "title", "description", "status", "created_at", "closed_at")
        read_only_fields = ("id", "auditor_user_id", "status", "created_at", "closed_at")


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IaaRoleAssignment
        fields = ("id", "user_id", "role", "department", "assigned_by_id",
                  "assigned_at", "is_active")
        read_only_fields = ("id", "assigned_by_id", "assigned_at")


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = ("id", "code", "starts_on", "ends_on", "is_active", "created_by_id")
        read_only_fields = ("id", "created_by_id")


class BudgetSerializer(serializers.ModelSerializer):
    financial_year_id = serializers.IntegerField()

    class Meta:
        model = DepartmentBudget
        fields = ("id", "financial_year_id", "department", "available_amount",
                  "updated_by_id", "updated_at")
        read_only_fields = ("id", "updated_by_id", "updated_at")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRouteRule
        fields = ("id", "request_type", "department", "minimum_amount",
                  "maximum_amount", "levels", "escalation_roles", "timeout_seconds",
                  "priority", "is_active", "updated_by_id", "updated_at")
        read_only_fields = ("id", "updated_by_id", "updated_at")


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyParameter
        fields = ("id", "code", "value", "effective_from", "effective_until",
                  "is_active", "updated_by_id", "updated_at")
        read_only_fields = ("id", "updated_by_id", "updated_at")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IaaNotification
        fields = ("id", "user_id", "actor_role", "event", "title", "message",
                  "record_type", "record_id", "created_at", "read_at")
        read_only_fields = ("id", "user_id", "actor_role", "event", "title",
                            "message", "record_type", "record_id", "created_at")


class RequestUpdateSerializer(serializers.Serializer):
    department = serializers.CharField(required=False, allow_blank=True, max_length=120)
    request_type = serializers.CharField(required=False, allow_blank=True, max_length=80)
    amount = serializers.DecimalField(required=False, max_digits=14, decimal_places=2,
                                       min_value=0, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    supporting_information = serializers.JSONField(required=False)


class RequestReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("validate", "clarification"))
    remarks = serializers.CharField(required=False, allow_blank=True)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("Approved", "Rejected"))
    remarks = serializers.CharField(allow_blank=False)


class ClarificationResponseSerializer(serializers.Serializer):
    response = serializers.CharField(allow_blank=False)


class ClaimCreateSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=120)
    trip_start = serializers.DateField()
    trip_end = serializers.DateField()
    purpose = serializers.CharField()
    claimed_amount = serializers.DecimalField(max_digits=14, decimal_places=2,
                                              min_value=0)
    trip_details = serializers.JSONField(required=False, default=dict)
    evidence = serializers.ListField(child=serializers.FileField(), allow_empty=False)

    def validate(self, attrs):
        if attrs["trip_end"] < attrs["trip_start"]:
            raise serializers.ValidationError({"trip_end": "Trip end precedes trip start."})
        return attrs


class TaReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("verify", "clarification"))
    policy_passed = serializers.BooleanField(required=False, default=True)
    remarks = serializers.CharField(required=False, allow_blank=True)


class AnomalyCreateSerializer(serializers.Serializer):
    record_type = serializers.ChoiceField(choices=("request", "ta_claim"))
    record_id = serializers.IntegerField(min_value=1)
    category = serializers.CharField(max_length=80)
    description = serializers.CharField()
    resolver_role = serializers.CharField(max_length=32)
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)


class AnomalyOutcomeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("Resolved", "Escalated"))
    remarks = serializers.CharField(allow_blank=False)


class ObservationCreateSerializer(serializers.Serializer):
    record_type = serializers.ChoiceField(choices=("request", "ta_claim"))
    record_id = serializers.IntegerField(min_value=1)
    department = serializers.CharField(max_length=120, allow_blank=True, required=False)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()


class ObservationResponseSerializer(serializers.Serializer):
    response = serializers.CharField(allow_blank=False)


class ObservationVerifySerializer(serializers.Serializer):
    satisfactory = serializers.BooleanField()
    remarks = serializers.CharField(allow_blank=False)


class ActiveRoleSerializer(serializers.Serializer):
    active_role = serializers.CharField(max_length=32)


class AssignmentCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role = serializers.ChoiceField(choices=("Basic User", "Finance Staff", "HoD",
                                            "Dean", "Director", "Auditor", "System Admin"))
    department = serializers.CharField(max_length=120, allow_blank=True, required=False)


class FinancialYearWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    is_active = serializers.BooleanField(default=False)


class BudgetWriteSerializer(serializers.Serializer):
    financial_year_id = serializers.IntegerField(min_value=1)
    department = serializers.CharField(max_length=120)
    available_amount = serializers.DecimalField(max_digits=14, decimal_places=2,
                                                min_value=0)


class RouteWriteSerializer(serializers.Serializer):
    request_type = serializers.CharField(max_length=80, allow_blank=True, required=False)
    department = serializers.CharField(max_length=120, allow_blank=True, required=False)
    minimum_amount = serializers.DecimalField(max_digits=14, decimal_places=2,
                                              required=False, allow_null=True)
    maximum_amount = serializers.DecimalField(max_digits=14, decimal_places=2,
                                              required=False, allow_null=True)
    levels = serializers.ListField(child=serializers.CharField(max_length=32), allow_empty=False)
    escalation_roles = serializers.ListField(child=serializers.CharField(max_length=32),
                                              required=False, default=list)
    timeout_seconds = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    priority = serializers.IntegerField(min_value=0, max_value=255, required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)


class PolicyWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=80)
    value = serializers.JSONField()
    effective_from = serializers.DateField()
    effective_until = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)


class AutoAnomalyRuleSerializer(serializers.Serializer):
    condition = serializers.ChoiceField(choices=("budget_insufficient",))
    category = serializers.CharField(max_length=80)
    description = serializers.CharField(required=False, allow_blank=True)
    resolver_role = serializers.ChoiceField(choices=("Finance Staff", "HoD", "Dean",
                                                      "Director", "Auditor"))
    assigned_user_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)
