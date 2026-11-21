"""Explicit transport schemas: callers cannot edit IDs, owner or ledger."""

from decimal import Decimal

from django.db.models import Sum
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.hreis.models import (
    AppraisalDetail,
    AuditEvent,
    ClaimDetail,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
)


class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"non_field_errors": ["Expected an object."]})
        unexpected = set(data) - set(self.fields)
        if unexpected:
            raise serializers.ValidationError(
                {
                    "unknown_fields": sorted(unexpected),
                }
            )
        return super().to_internal_value(data)


def _leave_balances_by_user_ids(user_ids):
    balances = {}
    entries = (
        LeaveLedgerEntry.objects.filter(user_id__in=user_ids)
        .values("user_id", "leave_type")
        .annotate(total=Sum("quantity"))
    )
    for row in entries:
        balances.setdefault(row["user_id"], {})[row["leave_type"]] = str(row["total"])
    return balances


class RecordListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        records = list(data)
        self.context["leave_balances_by_user_id"] = _leave_balances_by_user_ids(
            [record.user_id for record in records]
        )
        return super().to_representation(records)


class RecordReadSerializer(serializers.ModelSerializer):
    leave_balances = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
    def get_leave_balances(self, record):
        mapping = self.context.get("leave_balances_by_user_id")
        if mapping is None:
            mapping = _leave_balances_by_user_ids([record.user_id])
        return mapping.get(record.user_id, {})

    class Meta:
        model = EmployeeServiceRecord
        fields = (
            "id",
            "user_id",
            "appointment_details",
            "department",
            "designation_snapshot",
            "service_history",
            "leave_balances",
            "retirement_status",
            "revision",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
        list_serializer_class = RecordListSerializer


class MyLeaveBalancesSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    leave_balances = serializers.DictField(
        child=serializers.CharField(), read_only=True
    )


class RecordCreateSerializer(StrictInputSerializer):
    user_id = serializers.IntegerField(min_value=1)
    appointment_details = serializers.JSONField()
    department = serializers.CharField(max_length=120, allow_blank=False)
    designation_snapshot = serializers.CharField(max_length=150, allow_blank=False)
    service_history = serializers.ListField()
    retirement_status = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )


class RecordUpdateSerializer(StrictInputSerializer):
    expected_revision = serializers.IntegerField(min_value=0)
    appointment_details = serializers.JSONField(required=False)
    department = serializers.CharField(max_length=120, required=False, allow_blank=False)
    designation_snapshot = serializers.CharField(max_length=150, required=False, allow_blank=False)
    service_history = serializers.ListField(required=False)
    retirement_status = serializers.CharField(max_length=100, required=False, allow_blank=True)


class PolicyReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRPolicyVersion
        fields = (
            "id",
            "family",
            "version",
            "effective_from",
            "effective_until",
            "parameters",
            "approved_by_user_id",
            "approved_designation",
            "recorded_at",
        )
        read_only_fields = fields


class PolicyCreateSerializer(StrictInputSerializer):
    family = serializers.ChoiceField(choices=("leave", "appraisal", "ltc", "cpda"))
    version = serializers.IntegerField(min_value=1)
    effective_from = serializers.DateTimeField()
    effective_until = serializers.DateTimeField(required=False, allow_null=True, default=None)
    parameters = serializers.JSONField()


class VerifiedLeaveCreditSerializer(StrictInputSerializer):
    user_id = serializers.IntegerField(min_value=1)
    leave_type = serializers.ChoiceField(
        choices=("Casual", "Restricted", "Medical", "Earned", "Vacation", "Sabbatical")
    )
    quantity = serializers.DecimalField(
        max_digits=18, decimal_places=4, min_value=Decimal("0.0001")
    )
    evidence_reference = serializers.CharField(max_length=250, allow_blank=False)


class VerifiedLeaveCreditReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "user_id", "leave_type", "quantity", "recorded_at")
        read_only_fields = fields


class LeaveSubmitSerializer(StrictInputSerializer):
    leave_type = serializers.ChoiceField(
        choices=("Casual", "Restricted", "Medical", "Earned", "Vacation", "Sabbatical")
    )
    duration = serializers.DecimalField(
        max_digits=18, decimal_places=4, min_value=Decimal("0.0001")
    )
    justification = serializers.CharField(allow_blank=False, trim_whitespace=True)


class ClaimSubmitSerializer(StrictInputSerializer):
    family = serializers.ChoiceField(choices=("ltc", "cpda"))
    subtype = serializers.ChoiceField(choices=("advance", "reimbursement"))
    prescribed_form_reference = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(
        max_digits=20, decimal_places=6, required=False, min_value=Decimal("0.000001")
    )
    document_references = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
    )


class AppraisalSubmitSerializer(StrictInputSerializer):
    period_key = serializers.CharField(max_length=80, allow_blank=False)
    submitted_form = serializers.JSONField()


class ReviewerAssignmentSerializer(StrictInputSerializer):
    reviewer_user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class AppraisalDecisionSerializer(StrictInputSerializer):
    event = serializers.ChoiceField(choices=("forward", "finalize"))


class ClaimReviewSerializer(StrictInputSerializer):
    document_review_reference = serializers.CharField(allow_blank=False)
    eligibility_basis = serializers.CharField(allow_blank=False)


class DecisionSerializer(StrictInputSerializer):
    event = serializers.ChoiceField(choices=("approve", "reject", "forward"))
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class FinancialReviewSerializer(StrictInputSerializer):
    financial_review_reference = serializers.CharField(allow_blank=False)


class FinancialReviewReadSerializer(serializers.Serializer):
    request_id = serializers.IntegerField()
    financial_review_reference = serializers.CharField()
    reviewed_by_user_id = serializers.IntegerField()


class FinancialProcessingSerializer(StrictInputSerializer):
    financial_review_reference = serializers.CharField(allow_blank=False)
    source_system = serializers.ChoiceField(choices=("payroll", "finance"))
    external_status_reference = serializers.CharField(allow_blank=False)
    payment_status = serializers.ChoiceField(
        choices=("processing", "payment_pending", "paid", "failed")
    )


class FinancialStatusReadSerializer(serializers.Serializer):
    source_system = serializers.CharField()
    external_status_reference = serializers.CharField()
    payment_status = serializers.CharField()
    recorded_at = serializers.DateTimeField()


class ClaimSummarySerializer(serializers.Serializer):
    purpose = serializers.CharField()
    amount = serializers.CharField(allow_null=True)
    prescribed_form_reference = serializers.CharField()
    hr_verified = serializers.BooleanField()
    financial_verified = serializers.BooleanField()
    payment_status = serializers.CharField(allow_null=True)
    status_history = FinancialStatusReadSerializer(many=True)


class AppraisalSummarySerializer(serializers.Serializer):
    period_key = serializers.CharField()
    submitted_form = serializers.DictField(child=serializers.JSONField())
    reviewer_user_ids = serializers.ListField(child=serializers.IntegerField())


class ComplianceRequestSerializer(serializers.ModelSerializer):
    """Restricted status-only response: no medical reasons, forms or claim evidence."""

    family = serializers.CharField(read_only=True)

    class Meta:
        model = HRRequest
        fields = (
            "id", "user_id", "family", "state", "created_at", "submitted_at",
        )
        read_only_fields = fields


class RequestReadSerializer(serializers.ModelSerializer):
    claim_summary = serializers.SerializerMethodField()
    appraisal_summary = serializers.SerializerMethodField()
    route_total_steps = serializers.SerializerMethodField()

    @extend_schema_field(serializers.IntegerField())
    def get_route_total_steps(self, row):
        return len(row.authority_steps.all())

    @extend_schema_field(AppraisalSummarySerializer(allow_null=True))
    def get_appraisal_summary(self, row):
        if row.family != "appraisal":
            return None
        try:
            appraisal = row.appraisal
        except AppraisalDetail.DoesNotExist:
            return None
        return {
            "period_key": appraisal.period_key,
            "submitted_form": appraisal.submitted_form,
            "reviewer_user_ids": appraisal.reviewer_user_ids,
        }

    @extend_schema_field(ClaimSummarySerializer(allow_null=True))
    def get_claim_summary(self, row):
        if row.family not in ("ltc", "cpda"):
            return None
        try:
            claim = row.claim
        except ClaimDetail.DoesNotExist:
            return None
        return {
            "purpose": claim.purpose,
            "amount": (str(claim.amount) if claim.amount is not None else None),
            "prescribed_form_reference": claim.prescribed_form_reference,
            "hr_verified": claim.hr_verified_by_user_id is not None,
            "financial_verified": claim.financial_verified_by_user_id is not None,
            "payment_status": claim.financial_processing_details.get("payment_status"),
            "status_history": FinancialStatusReadSerializer(
                sorted(
                    claim.status_history.all(),
                    key=lambda item: (item.recorded_at, item.pk),
                ),
                many=True,
            ).data,
        }

    class Meta:
        model = HRRequest
        fields = (
            "id",
            "user_id",
            "family",
            "subtype",
            "state",
            "payload",
            "claim_summary",
            "appraisal_summary",
            "route_step",
            "route_total_steps",
            "submitted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RequestTransitionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRRequestTransition
        fields = ("source", "event", "target", "acting_designation", "reason", "recorded_at")
        read_only_fields = fields


class RequestDetailReadSerializer(RequestReadSerializer):
    family = serializers.CharField(read_only=True)
    history = serializers.SerializerMethodField()

    @extend_schema_field(RequestTransitionReadSerializer(many=True))
    def get_history(self, row):
        return RequestTransitionReadSerializer(
            row.transitions.order_by("recorded_at", "pk"), many=True,
        ).data

    class Meta(RequestReadSerializer.Meta):
        fields = (*RequestReadSerializer.Meta.fields, "history")
        read_only_fields = fields


class AuditReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor_user_id",
            "acting_designation",
            "subject_user_id",
            "action",
            "resource_kind",
            "resource_id",
            "data",
            "recorded_at",
        )
        read_only_fields = fields


class NotificationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "request_id", "created_at", "read_at")
        read_only_fields = fields
