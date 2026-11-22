from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.files import drive
from modules.hr.models import (
    CLAIM_REQUEST_TYPES,
    LEAVE_TYPES,
    Appraisal,
    AppraisalWindow,
    AuditEvent,
    Claim,
    ClaimIntegrationStatus,
    EmployeeRecord,
    HRNotification,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    WorkflowRoute,
)


def named_choice_field(name, choices, *, read_only=False):
    field_type = type(f"{name}Field", (serializers.ChoiceField,), {})
    field_type = extend_schema_field(
        {"type": "string", "enum": list(serializers.ChoiceField(choices=choices).choices)},
        component_name=name,
    )(field_type)
    return field_type(choices=choices, read_only=read_only)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("leave_type", "available_days", "is_eligible", "updated_at")
        read_only_fields = fields


class EmployeeRecordSerializer(serializers.ModelSerializer):
    employee_category = named_choice_field(
        "EmployeeRecordCategory", EmployeeRecord.CATEGORY, read_only=True
    )
    leave_balances = LeaveBalanceSerializer(many=True, read_only=True)

    class Meta:
        model = EmployeeRecord
        fields = (
            "user_id",
            "employee_category",
            "employment_status",
            "department",
            "designation",
            "appointment_type",
            "appointment_start_date",
            "appointment_end_date",
            "appointment_details",
            "service_history",
            "retirement_status",
            "leave_balances",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EmployeeRecordWriteSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    employment_status = serializers.ChoiceField(
        choices=EmployeeRecord.EMPLOYMENT_STATUS, required=False, default="active"
    )
    department = serializers.CharField(max_length=100)
    designation = serializers.CharField(max_length=100)
    appointment_type = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    appointment_start_date = serializers.DateField(required=False, allow_null=True)
    appointment_end_date = serializers.DateField(required=False, allow_null=True)
    appointment_details = serializers.DictField(required=False, default=dict)
    service_history = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )
    retirement_status = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        start = attrs.get("appointment_start_date")
        end = attrs.get("appointment_end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"appointment_end_date": "Must not precede the start date."}
            )
        return attrs


class EmployeeRecordPatchSerializer(serializers.Serializer):
    employment_status = serializers.ChoiceField(
        choices=EmployeeRecord.EMPLOYMENT_STATUS, required=False
    )
    department = serializers.CharField(max_length=100, required=False)
    designation = serializers.CharField(max_length=100, required=False)
    appointment_type = serializers.CharField(max_length=100, required=False, allow_blank=True)
    appointment_start_date = serializers.DateField(required=False, allow_null=True)
    appointment_end_date = serializers.DateField(required=False, allow_null=True)
    appointment_details = serializers.DictField(required=False)
    service_history = serializers.ListField(child=serializers.DictField(), required=False)
    retirement_status = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate(self, attrs):
        start = attrs.get("appointment_start_date")
        end = attrs.get("appointment_end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"appointment_end_date": "Must not precede the start date."}
            )
        return attrs


class ClaimIntegrationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimIntegrationStatus
        fields = (
            "id",
            "system",
            "external_status",
            "external_reference",
            "details",
            "received_at",
            "created_at",
        )
        read_only_fields = fields


class ClaimSerializer(serializers.ModelSerializer):
    employee_category = named_choice_field(
        "ClaimEmployeeCategory", EmployeeRecord.CATEGORY, read_only=True
    )
    request_type = named_choice_field("ClaimRequestType", CLAIM_REQUEST_TYPES, read_only=True)
    integration_statuses = ClaimIntegrationStatusSerializer(many=True, read_only=True)
    request_type_display = serializers.CharField(source="get_request_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id",
            "employee_user_id",
            "employee_category",
            "request_type",
            "request_type_display",
            "purpose",
            "amount",
            "form_data",
            "supporting_documents",
            "status",
            "status_display",
            "current_authority_user_id",
            "verification_details",
            "processing_details",
            "processed_at",
            "integration_statuses",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ClaimCreateSerializer(serializers.Serializer):
    request_type = named_choice_field("ClaimCreateRequestType", CLAIM_REQUEST_TYPES)
    purpose = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    form_data = serializers.DictField(required=False, default=dict)
    supporting_document_links = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
        allow_empty=True,
    )

    def validate(self, attrs):
        for raw_link in attrs["supporting_document_links"]:
            try:
                drive.parse(raw_link)
            except drive.InvalidDriveLink as exc:
                raise serializers.ValidationError(
                    {
                        "supporting_document_links": exc.message,
                    }
                ) from exc
        return attrs


class ClaimVerificationSerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ClaimDecisionSerializer(serializers.Serializer):
    action = named_choice_field("ClaimDecisionAction", ("approve", "reject", "forward"))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ClaimProcessingSerializer(serializers.Serializer):
    financially_correct = serializers.BooleanField()
    details = serializers.DictField()


class ClaimIntegrationWriteSerializer(serializers.Serializer):
    system = serializers.ChoiceField(choices=("payroll", "finance"))
    external_status = serializers.CharField(max_length=100)
    external_reference = serializers.CharField(
        max_length=160, required=False, allow_blank=True, default=""
    )
    details = serializers.DictField(required=False, default=dict)


class AppraisalSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Appraisal
        fields = (
            "id",
            "employee_user_id",
            "period",
            "form_data",
            "status",
            "status_display",
            "reviewer_user_ids",
            "current_reviewer_index",
            "current_reviewer_user_id",
            "reviews",
            "finalized_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AppraisalCreateSerializer(serializers.Serializer):
    period = serializers.CharField(max_length=40)
    form_data = serializers.DictField()


class ReviewerAssignmentSerializer(serializers.Serializer):
    reviewer_user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )


class AppraisalReviewSerializer(serializers.Serializer):
    action = named_choice_field("AppraisalReviewAction", ("forward", "finalize"))
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class WorkflowRouteSerializer(serializers.ModelSerializer):
    employee_category = named_choice_field(
        "WorkflowRouteEmployeeCategory", WorkflowRoute.CATEGORIES, read_only=True
    )
    request_type = named_choice_field(
        "WorkflowRouteRequestType", WorkflowRoute.REQUEST_TYPES, read_only=True
    )

    class Meta:
        model = WorkflowRoute
        fields = (
            "id",
            "employee_category",
            "request_type",
            "steps",
            "reminder_after_hours",
            "updated_at",
        )
        read_only_fields = fields


class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "entry_type", "amount_delta", "actor_user_id", "created_at")
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_user_id = serializers.IntegerField(source="employee.user_id", read_only=True)
    leave_type_display = serializers.CharField(source="get_leave_type_display", read_only=True)
    ledger_entries = LeaveLedgerEntrySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "employee_user_id",
            "leave_type",
            "leave_type_display",
            "duration_days",
            "justification",
            "status",
            "current_authority_user_id",
            "authority_step",
            "created_at",
            "updated_at",
            "ledger_entries",
        )
        read_only_fields = fields


class LeaveRequestCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=LEAVE_TYPES)
    duration_days = serializers.DecimalField(
        max_digits=7, decimal_places=2, min_value=Decimal("0.01")
    )
    justification = serializers.CharField(max_length=1000, trim_whitespace=True)


class LeaveDecisionSerializer(serializers.Serializer):
    action = named_choice_field("LeaveDecisionAction", ("approve", "reject", "forward"))
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class LeaveBalanceManageSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField(min_value=1)
    leave_type = serializers.ChoiceField(choices=LEAVE_TYPES)
    available_days = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=Decimal("0.00")
    )
    is_eligible = serializers.BooleanField()


class LeaveBalanceManageReadSerializer(serializers.ModelSerializer):
    employee_user_id = serializers.IntegerField(source="employee.user_id", read_only=True)
    leave_type_display = serializers.CharField(source="get_leave_type_display", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "employee_user_id",
            "leave_type",
            "leave_type_display",
            "available_days",
            "is_eligible",
            "updated_at",
        )
        read_only_fields = fields


class WorkflowRouteWriteSerializer(serializers.Serializer):
    employee_category = named_choice_field(
        "WorkflowRouteWriteEmployeeCategory", EmployeeRecord.CATEGORY
    )
    request_type = named_choice_field("WorkflowRouteWriteRequestType", WorkflowRoute.REQUEST_TYPES)
    steps = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    reminder_after_hours = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class AppraisalWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalWindow
        fields = ("id", "period", "opens_at", "closes_at", "is_active", "updated_at")
        read_only_fields = fields


class AppraisalWindowWriteSerializer(serializers.Serializer):
    period = serializers.CharField(max_length=40)
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs["closes_at"] <= attrs["opens_at"]:
            raise serializers.ValidationError({"closes_at": "Must be later than opens_at."})
        return attrs


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "entity_type",
            "entity_id",
            "actor_user_id",
            "action",
            "details",
            "created_at",
        )
        read_only_fields = fields


class HRNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRNotification
        fields = ("id", "topic", "subject", "body", "payload", "created_at")
        read_only_fields = fields


class NoticeWriteSerializer(serializers.Serializer):
    recipient_user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    subject = serializers.CharField(max_length=160)
    body = serializers.CharField(max_length=2000)


class NoticePublishResponseSerializer(serializers.Serializer):
    published = serializers.IntegerField(min_value=0)
