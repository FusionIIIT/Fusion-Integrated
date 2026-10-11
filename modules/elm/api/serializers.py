"""Serializers for ELM API endpoints."""
from rest_framework import serializers

from modules.elm.domain.constants import LeaveCategory
from modules.elm.models import (
    ApprovalHierarchy,
    HalfDaySessionChoice,
    Holiday,
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
    LeaveAuditLog,
    LeaveBalanceTransaction,
    LeaveExtension,
    LeavePolicyConfig,
    LeaveResumption,
    SlaThresholdConfig,
    VacationPeriod,
    WorkflowTask,
    YearEndRun,
)


class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = [
            "id", "user_id", "year", "category",
            "credited", "carried_forward", "availed", "balance",
            "created_at", "updated_at",
        ]


class LeaveBalanceTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalanceTransaction
        fields = [
            "id", "user_id", "year", "category", "transaction_type",
            "amount", "balance_after", "reference_id", "remarks",
            "performed_by_user_id", "created_at",
        ]


class LeaveBalanceResponseSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField()
    balances = serializers.DictField(child=serializers.CharField())
    transactions = LeaveBalanceTransactionSerializer(many=True)


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[c.value for c in LeaveCategory])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.ChoiceField(
        choices=HalfDaySessionChoice.choices, required=False, allow_blank=True, default=""
    )
    medical_certificate = serializers.CharField(required=False, allow_blank=True, default="")

    # Station Leave
    is_station_leave = serializers.BooleanField(default=False)
    station_leave_departure = serializers.DateTimeField(required=False, allow_null=True)
    station_leave_return = serializers.DateTimeField(required=False, allow_null=True)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="")
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_emergency_contact = serializers.CharField(required=False, allow_blank=True, default="")

    # Substitute
    requires_substitute = serializers.BooleanField(default=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveApplicationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"


class LeaveApplicationExportSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    application_id = serializers.IntegerField()
    generated_at = serializers.CharField()
    applicant = serializers.DictField()
    leave_details = serializers.DictField()
    station_leave = serializers.DictField()
    substitute = serializers.DictField()
    review_trail = serializers.DictField()


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteReplaceSerializer(serializers.Serializer):
    new_substitute_user_id = serializers.IntegerField()


class UnitHeadReviewSerializer(serializers.Serializer):
    # outcome: "approve" | "reject" for CL/RH; "recommended" | "not_recommended" for higher
    outcome = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class EstablishmentRouteSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class CancellationReviewSerializer(serializers.Serializer):
    outcome = serializers.CharField()  # approve/reject or recommended/not_recommended
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ExtensionRequestSerializer(serializers.Serializer):
    extended_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    requires_substitute = serializers.BooleanField(default=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ExtensionReviewSerializer(serializers.Serializer):
    outcome = serializers.CharField()  # recommended / not_recommended or approve / reject
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveExtension
        fields = "__all__"


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    resumption_details = serializers.CharField(max_length=2000)


class ResumptionReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveResumption
        fields = "__all__"


class OfflineLeaveCreateSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[c.value for c in LeaveCategory])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    offline_reference_no = serializers.CharField(max_length=100)
    offline_sanction_date = serializers.DateField()
    offline_sanctioning_authority = serializers.CharField(max_length=150)
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.ChoiceField(
        choices=HalfDaySessionChoice.choices, required=False, allow_blank=True, default=""
    )


class AdminMaintenanceSerializer(serializers.Serializer):
    reason_note = serializers.CharField(max_length=1000)
    new_purpose = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    new_medical_certificate = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class LeavePolicyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicyConfig
        fields = "__all__"


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"


class HolidayCalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = "__all__"


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = "__all__"


class ApprovalHierarchySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalHierarchy
        fields = "__all__"


class SlaThresholdConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaThresholdConfig
        fields = "__all__"


class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = "__all__"


class LeaveAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAuditLog
        fields = "__all__"


class YearEndRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearEndRun
        fields = "__all__"


class AdminYearEndProcessRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)


class AdminProcessSlaResponseSerializer(serializers.Serializer):
    reminders_sent = serializers.IntegerField()
    escalations_processed = serializers.IntegerField()


