"""
modules/leave/api/serializers.py
DRF serializers for the Leave Management module.
"""
from datetime import date
from decimal import Decimal

from rest_framework import serializers

from modules.leave.models import (
    LeavePolicy,
    HolidayCalendar,
    LeaveBalance,
    LeaveApplication,
    ApprovalStep,
    SubstituteRequest,
    SlaConfig,
    LeaveCategory,
    ApplicationStatus,
)
from modules.leave.domain.rules import (
    count_leave_days,
    can_take_half_day,
)


# ---------------------------------------------------------------------------
# Read-only / lightweight serializers
# ---------------------------------------------------------------------------

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model  = LeavePolicy
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by_user_id"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model  = HolidayCalendar
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "created_by_user_id"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LeaveBalance
        fields = ["id", "category", "balance_days", "year"]


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ApprovalStep
        fields = "__all__"


class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SubstituteRequest
        fields = "__all__"


class SlaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SlaConfig
        fields = "__all__"


# ---------------------------------------------------------------------------
# LeaveApplication serializers
# ---------------------------------------------------------------------------

class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    class Meta:
        model  = LeaveApplication
        fields = [
            "id", "category", "start_date", "end_date",
            "half_day", "status", "submitted_at",
        ]


class LeaveApplicationDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested steps and substitute requests."""
    approval_steps       = ApprovalStepSerializer(many=True, read_only=True)
    substitute_requests  = SubstituteRequestSerializer(many=True, read_only=True)

    class Meta:
        model  = LeaveApplication
        fields = "__all__"


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new leave application.
    Validates date logic, half-day eligibility, and balance availability.
    """
    class Meta:
        model  = LeaveApplication
        fields = [
            "category", "start_date", "end_date",
            "half_day", "half",
            "station_leave", "station_start", "station_end",
            "reason",
            "substitute_user_id",
            "is_extension", "parent_application",
        ]

    def validate(self, attrs):
        start  = attrs.get("start_date")
        end    = attrs.get("end_date")
        half   = attrs.get("half_day", False)
        cat    = attrs.get("category")

        if start and end and end < start:
            raise serializers.ValidationError("end_date must be >= start_date.")

        if half and not can_take_half_day(cat):
            raise serializers.ValidationError(
                f"Half-day leave is not allowed for category '{cat}'."
            )

        if half and start != end:
            raise serializers.ValidationError(
                "Half-day leave must have the same start and end date."
            )

        # BR-EL-014: Substitute eligibility (cannot nominate oneself)
        substitute_user_id = attrs.get("substitute_user_id")
        request = self.context.get("request")
        current_user_id = getattr(request.user, "user_id", None) if request and hasattr(request, "user") else None
        if substitute_user_id and current_user_id and substitute_user_id == current_user_id:
            raise serializers.ValidationError(
                {"substitute_user_id": "An applicant cannot nominate themselves as substitute."}
            )

        # Check balance (best-effort; authoritative check happens in service layer)
        if request and current_user_id:
            from modules.leave.models import LeaveBalance
            import datetime
            year = str(start.year) if start else str(datetime.date.today().year)
            try:
                balance = LeaveBalance.objects.get(
                    user_id=current_user_id,
                    category=cat,
                    year=year,
                )
                required = count_leave_days(start, end, category=cat, half_day=half)
                if balance.balance_days < required:
                    raise serializers.ValidationError(
                        f"Insufficient balance: available {balance.balance_days}d, "
                        f"required {required}d."
                    )
            except LeaveBalance.DoesNotExist:
                raise serializers.ValidationError(
                    f"No leave balance found for category '{cat}' in year {year}."
                )

        return attrs


class LeaveApplicationWithdrawSerializer(serializers.Serializer):
    withdrawal_reason = serializers.CharField(required=False, allow_blank=True)


class LeaveApplicationCancelSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(required=True)


class LeaveApplicationExtendSerializer(serializers.Serializer):
    new_end_date = serializers.DateField(required=True)
    reason       = serializers.CharField(required=True)


class SubstituteRespondSerializer(serializers.Serializer):
    STATUS_CHOICES = [("accepted", "Accepted"), ("declined", "Declined")]
    status  = serializers.ChoiceField(choices=STATUS_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True)


class UnitHeadDecideSerializer(serializers.Serializer):
    DECISION_CHOICES = [
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]
    decision = serializers.ChoiceField(choices=DECISION_CHOICES)
    comment  = serializers.CharField(required=False, allow_blank=True)


class ResumptionSerializer(serializers.Serializer):
    actual_resume_date = serializers.DateField(required=True)


class AdminOfflineRecordSerializer(serializers.ModelSerializer):
    """For admin to manually record an offline-sanctioned leave."""
    class Meta:
        model  = LeaveApplication
        fields = [
            "user_id", "category", "start_date", "end_date",
            "half_day", "half", "reason",
            "substitute_user_id", "decided_by_user_id",
        ]
