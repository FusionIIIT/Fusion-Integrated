from rest_framework import serializers
from modules.iaa.models import IAAExpenseRequest, IAAApproval, IAAAnomaly, IAAAuditObservation, IATravelClaim, IAAPolicy

class ExpenseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAExpenseRequest
        fields = ("department_id", "request_type", "title", "description", "amount", "currency", "financial_year", "budget_code", "attachments")

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAExpenseRequest
        fields = "__all__"
        read_only_fields = fields

class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approved", "rejected", "escalated"))
    remarks = serializers.CharField()
    level = serializers.IntegerField(min_value=1, default=1)
    role = serializers.CharField(max_length=80, required=False, allow_blank=True)

class AnomalyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAAnomaly
        fields = ("request", "reference", "category", "description")

class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAAnomaly
        fields = "__all__"
        read_only_fields = fields

class ObservationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAAuditObservation
        fields = ("reference", "title", "finding", "owner_user_id")

class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAAuditObservation
        fields = "__all__"
        read_only_fields = fields

class TravelWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IATravelClaim
        fields = ("trip_purpose", "start_date", "end_date", "amount", "currency", "details")

class TravelSerializer(serializers.ModelSerializer):
    class Meta:
        model = IATravelClaim
        fields = "__all__"
        read_only_fields = fields

class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = IAAPolicy
        fields = ("id", "financial_year", "parameters", "approval_rules", "is_active", "updated_at")
        read_only_fields = ("id", "updated_at")
