"""Explicit input allow-lists and read-only ELM response shapes."""
from rest_framework import serializers

from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    LeaveAccount,
    LeaveAuditEvent,
    LeaveCalendarDate,
    LeaveCase,
    LeavePolicy,
    LeaveRequest,
    LeaveTransaction,
    OrganizationUnit,
)


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=("none", "first_half", "second_half"), default="none")
    purpose = serializers.CharField(max_length=2000)
    station_leave = serializers.BooleanField(default=False)
    station_destination = serializers.CharField(
        max_length=200, allow_blank=True, required=False, default="")
    medical_evidence_ref = serializers.CharField(
        max_length=500, allow_blank=True, required=False, default="")
    substitute_user_id = serializers.IntegerField(
        allow_null=True, required=False)


class LeaveCaseCreateSerializer(serializers.Serializer):
    case_type = serializers.ChoiceField(
        choices=("cancellation", "extension", "resumption"))
    requested_start = serializers.DateField(required=False)
    requested_end = serializers.DateField(required=False)
    actual_resumption_date = serializers.DateField(required=False)
    medical_evidence_ref = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(
        allow_null=True, required=False, default=None)
    reason = serializers.CharField(max_length=2000)

    def validate(self, attrs):
        case_type = attrs["case_type"]
        if case_type == "extension" and not {
            "requested_start", "requested_end",
        }.issubset(attrs):
            raise serializers.ValidationError(
                "An extension requires requested_start and requested_end.")
        if case_type == "resumption" and "actual_resumption_date" not in attrs:
            raise serializers.ValidationError(
                "A resumption requires actual_resumption_date.")
        return attrs


class DecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=(
        "accept", "decline", "approve", "reject", "recommend",
        "not_recommended", "forward"))
    note = serializers.CharField(max_length=2000, allow_blank=True, default="")


class SubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=("none", "first_half", "second_half"), default="none")
    purpose = serializers.CharField(max_length=2000)


class AccountAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    description = serializers.CharField(max_length=240)


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id", "applicant_user_id", "category", "start_date", "end_date",
            "half_day", "purpose", "station_leave", "station_destination",
            "medical_evidence_ref", "substitute_user_id", "substitute_response",
            "status", "workflow_stage", "approved_days", "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveCaseSerializer(serializers.ModelSerializer):
    leave_category = serializers.CharField(source="leave_request.category",
                                          read_only=True)
    applicant_user_id = serializers.IntegerField(
        source="leave_request.applicant_user_id", read_only=True)
    workflow_stage = serializers.SerializerMethodField()

    class Meta:
        model = LeaveCase
        fields = (
            "id", "leave_request_id", "leave_category", "applicant_user_id",
            "case_type", "requested_start", "requested_end",
            "actual_resumption_date", "medical_evidence_ref", "reason",
            "substitute_user_id", "substitute_response", "status",
            "workflow_stage",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_workflow_stage(self, obj):
        return "unit_head" if obj.status == "pending_unit_head" else (
            "sanction" if obj.status == "pending_sanction" else "")


class LeaveAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAuditEvent
        fields = ("id", "actor_user_id", "action", "note", "created_at")
        read_only_fields = fields


class LeaveTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransaction
        fields = (
            "id", "category", "amount", "transaction_type", "description",
            "created_at",
        )
        read_only_fields = fields


class LeaveAccountSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveAccount
        fields = (
            "user_id", "category", "year", "opening_balance", "credited",
            "used", "lapsed", "closing_balance", "balance",
        )
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = (
            "category", "annual_entitlement", "faculty_only", "continuous_days",
            "carry_forward", "allow_half_day", "medical_evidence_required",
            "is_active",
        )
        read_only_fields = ("category",)


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendarDate
        fields = ("id", "date", "kind", "label", "is_published", "published_at")
        read_only_fields = ("id", "is_published", "published_at")


class OrganizationUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUnit
        fields = ("id", "code", "name", "unit_head_user_id", "is_active")


class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = ("user_id", "employee_type", "designation",
                  "organization_unit", "is_active")


class ApprovalRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRoute
        fields = (
            "id", "category", "organization_unit", "approver_user_id",
            "approver_role", "permission_code", "establishment_required",
            "is_active",
        )
        read_only_fields = ("id",)

    def validate_permission_code(self, value):
        if value != "elm.leave.sanction":
            raise serializers.ValidationError(
                "A final authority route must use elm.leave.sanction.")
        return value
