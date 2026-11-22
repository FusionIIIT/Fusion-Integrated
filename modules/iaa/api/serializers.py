from rest_framework import serializers

from modules.iaa.models import (
    Anomaly, ApprovalRoute, ApprovalStep, AuditObservation, BudgetAllocation,
    ExpenseRequest, IaaNotificationOutbox, IaaPolicy, IaaSupportingDocument,
    ObservationResponse, TravelClaim,
)


class ExpenseReadSerializer(serializers.ModelSerializer):
    supporting_documents = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseRequest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "creator_user_id", "status",
                            "assigned_finance_user_id", "assigned_route", "clarification",
                            "finance_notes", "decision_remarks", "recorded_at",
                            "recorded_by_user_id", "lock_version")

    def get_supporting_documents(self, obj):
        return document_references(obj.supporting_documents)


class ExpenseDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseRequest
        fields = ("request_type", "amount", "department", "description", "supporting_documents")

    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class TravelClaimReadSerializer(serializers.ModelSerializer):
    supporting_documents = serializers.SerializerMethodField()

    class Meta:
        model = TravelClaim
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "claimant_user_id", "status",
                            "assigned_finance_user_id", "assigned_route", "clarification",
                            "finance_notes", "decision_remarks", "recorded_at",
                            "recorded_by_user_id")

    def get_supporting_documents(self, obj):
        return document_references(obj.supporting_documents)


def document_references(refs):
    ids = [item.get("document_id") for item in refs if isinstance(item, dict)]
    docs = IaaSupportingDocument.objects.filter(pk__in=ids, is_active=True)
    return SupportingDocumentSerializer(docs, many=True).data


class TravelClaimWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelClaim
        fields = ("department", "trip_start", "trip_end", "purpose", "amount",
                  "supporting_documents")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Claimed amount must be greater than zero.")
        return value


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "record_type", "record_id",
                            "route", "level", "authority_role", "assignee_user_id",
                            "status", "due_at", "decided_at", "remarks")


class AnomalySerializer(serializers.ModelSerializer):
    class Meta:
        model = Anomaly
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "record_type", "record_id",
                            "category", "description", "is_automatic", "status",
                            "resolver_role", "resolver_user_id", "resolution_remarks")


class ObservationSerializer(serializers.ModelSerializer):
    responses = serializers.SerializerMethodField()

    class Meta:
        model = AuditObservation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "record_type", "record_id",
                            "auditor_user_id", "owner_user_id", "department", "finding", "status")

    def get_responses(self, obj):
        result = []
        for response in ObservationResponse.objects.filter(observation=obj):
            result.append({
                "id": response.pk,
                "responder_user_id": response.responder_user_id,
                "corrective_action": response.corrective_action,
                "supporting_documents": document_references(response.supporting_documents),
                "auditor_user_id": response.auditor_user_id,
                "satisfactory": response.satisfactory,
                "verification_remarks": response.verification_remarks,
                "created_at": response.created_at,
            })
        return result


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IaaNotificationOutbox
        fields = "__all__"
        read_only_fields = ("id", "recipient_user_id", "record_type", "record_id", "event",
                            "payload", "created_at", "delivered_at")


class ActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("query", "validate", "verify", "approve", "reject"))
    notes = serializers.CharField(required=False, allow_blank=True)
    clarification = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)


class ClarificationSerializer(serializers.Serializer):
    response = serializers.CharField()
    supporting_documents = serializers.ListField(child=serializers.DictField(), required=False)


class ObservationResponseSerializer(serializers.Serializer):
    corrective_action = serializers.CharField()
    supporting_documents = serializers.ListField(child=serializers.DictField(), required=False)


class ObservationReviewSerializer(serializers.Serializer):
    satisfactory = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class AnomalyCreateSerializer(serializers.Serializer):
    record_type = serializers.ChoiceField(choices=("expense", "ta"))
    record_id = serializers.IntegerField(min_value=1)
    category = serializers.CharField(max_length=80)
    description = serializers.CharField()
    resolver_role = serializers.CharField(max_length=20)
    resolver_user_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    def validate_resolver_role(self, value):
        role = value.strip().lower()
        if role not in {"finance_staff", "auditor", "hod", "dean", "director"}:
            raise serializers.ValidationError("Use a supported designated resolver role.")
        return role


class AnomalyResolutionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("resolve", "escalate"))
    remarks = serializers.CharField()
    next_resolver_user_id = serializers.IntegerField(min_value=1, required=False)
    next_resolver_role = serializers.ChoiceField(
        choices=("finance_staff", "auditor", "hod", "dean", "director"), required=False)


class ObservationCreateSerializer(serializers.Serializer):
    record_type = serializers.ChoiceField(choices=("expense", "ta"))
    record_id = serializers.IntegerField(min_value=1)
    finding = serializers.CharField()


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = IaaPolicy
        fields = ("id", "name", "financial_year_start_month", "ta_high_value_threshold",
                  "approval_timeout_hours", "parameters", "is_active", "updated_at")
        read_only_fields = ("id", "updated_at")

    def validate_financial_year_start_month(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Month must be between 1 and 12.")
        return value


class ApprovalRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRoute
        fields = ("id", "request_type", "department", "amount_from", "amount_through",
                  "level", "authority_role", "assignee_user_id", "timeout_hours",
                  "next_route", "is_active")


class BudgetAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetAllocation
        fields = ("id", "department", "financial_year", "budget_code", "allocated_amount",
                  "committed_amount", "available_amount", "configured_by_user_id",
                  "created_at", "updated_at")
        read_only_fields = ("id", "configured_by_user_id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = self.instance
        allocated = attrs.get("allocated_amount", getattr(instance, "allocated_amount", None))
        committed = attrs.get("committed_amount", getattr(instance, "committed_amount", 0))
        available = attrs.get("available_amount", getattr(instance, "available_amount", None))
        if allocated is not None and (allocated < 0 or committed < 0 or available < 0):
            raise serializers.ValidationError("Budget amounts cannot be negative.")
        if allocated is not None and committed > allocated:
            raise serializers.ValidationError({"committed_amount": "Cannot exceed the allocated amount."})
        if allocated is not None and available > allocated:
            raise serializers.ValidationError({"available_amount": "Cannot exceed the allocated amount."})
        if allocated is not None and committed + available > allocated:
            raise serializers.ValidationError(
                "Committed and available amounts cannot exceed the allocated amount."
            )
        return attrs


class SupportingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IaaSupportingDocument
        fields = ("id", "kind", "title", "drive_url", "created_at")
        read_only_fields = fields


class SupportingDocumentWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("expense", "ta", "observation"))
    drive_url = serializers.URLField(max_length=500)
    title = serializers.CharField(max_length=160, required=False, allow_blank=True)
