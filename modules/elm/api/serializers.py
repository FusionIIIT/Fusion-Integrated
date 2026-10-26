"""Serializers for ELM API."""
from decimal import Decimal

from rest_framework import serializers

from ..domain.rules import calculate_leave_days, is_date_overlap, validate_substitute
from ..models import (
    LeaveAction,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    LeaveStatus,
)
from .utils import get_caller_id

ACTIVE_STATUSES = [
    LeaveStatus.SUBMITTED,
    LeaveStatus.PENDING_SUBSTITUTE,
    LeaveStatus.PENDING_UNIT_HEAD,
    LeaveStatus.PENDING_SANCTION,
    LeaveStatus.APPROVED,
    LeaveStatus.CANCELLATION_REQUESTED,
]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "leave_type",
            "allocated",
            "used",
            "balance",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "updated_at"]


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = [
            "id",
            "application",
            "actor_id",
            "action",
            "comments",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)
    calculated_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "substitute_id",
            "substitute_status",
            "is_station_leave",
            "station_address",
            "half_day",
            "half_day_type",
            "unit_head_id",
            "unit_head_recommendation",
            "sanctioning_authority_id",
            "rejection_reason",
            "created_at",
            "updated_at",
            "actions",
            "calculated_days",
        ]
        read_only_fields = [
            "id",
            "applicant_id",
            "status",
            "substitute_status",
            "unit_head_recommendation",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def get_calculated_days(self, obj) -> float:
        try:
            return calculate_leave_days(
                obj.leave_type,
                obj.start_date,
                obj.end_date,
                obj.half_day,
            )
        except (ValueError, TypeError):
            return 0.0


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "substitute_id",
            "is_station_leave",
            "station_address",
            "half_day",
            "half_day_type",
        ]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        leave_type = attrs.get("leave_type")
        half_day = attrs.get("half_day", False)
        half_day_type = attrs.get("half_day_type", "")
        substitute_id = attrs.get("substitute_id")
        is_station_leave = attrs.get("is_station_leave", False)
        station_address = attrs.get("station_address", "")

        if start and end and start > end:
            raise serializers.ValidationError({
                "end_date": "End date must be on or after start date.",
            })

        if half_day:
            if leave_type != LeaveCategory.CL:
                raise serializers.ValidationError({
                    "half_day": "Half-day option is only available for Casual Leave (CL).",
                })
            if start != end:
                raise serializers.ValidationError({
                    "half_day": "Half-day leave must be for a single date.",
                })
            if half_day_type not in ["first_half", "second_half"]:
                raise serializers.ValidationError({
                    "half_day_type": "half_day_type must be 'first_half' or 'second_half'.",
                })

        if is_station_leave and not station_address.strip():
            raise serializers.ValidationError({
                "station_address": "Station address is required for station leave.",
            })

        request = self.context.get("request")
        user_id = get_caller_id(request)
        if user_id is None:
            raise serializers.ValidationError("Authentication required.")

        # Calculate requested days
        try:
            req_days = calculate_leave_days(leave_type, start, end, half_day)
        except ValueError as e:
            raise serializers.ValidationError(str(e)) from e

        if req_days <= 0:
            raise serializers.ValidationError("Requested leave duration must be greater than 0.")

        # Balance check (BR-EL-002, BR-EL-005, BR-EL-009)
        bal_record = LeaveBalance.objects.filter(
            user_id=user_id,
            year=start.year,
            leave_type=leave_type,
        ).first()
        if not bal_record or bal_record.balance < Decimal(str(req_days)):
            available = bal_record.balance if bal_record else Decimal("0.0")
            raise serializers.ValidationError(
                f"Insufficient {leave_type} balance. Available: {available}, Required: {req_days}"
            )

        # Overlap check for applicant (BR-EL-012)
        existing_leaves = LeaveApplication.objects.filter(
            applicant_id=user_id,
            status__in=ACTIVE_STATUSES,
        )
        for ex in existing_leaves:
            if is_date_overlap(
                start, end, ex.start_date, ex.end_date,
                half_day, half_day_type, ex.half_day, ex.half_day_type,
            ):
                raise serializers.ValidationError(
                    f"Requested period overlaps with active application #{ex.id} "
                    f"({ex.start_date} to {ex.end_date})."
                )

        # Substitute eligibility check (BR-EL-014)
        if substitute_id is not None:
            try:
                validate_substitute(user_id, substitute_id)
            except ValueError as e:
                raise serializers.ValidationError({"substitute_id": str(e)}) from e

            # Substitute overlap check
            sub_leaves = LeaveApplication.objects.filter(
                applicant_id=substitute_id,
                status__in=ACTIVE_STATUSES,
            )
            for sex in sub_leaves:
                if sex.start_date <= end and sex.end_date >= start:
                    raise serializers.ValidationError({
                        "substitute_id": (
                            f"Nominated substitute has active leave during the requested "
                            f"period ({sex.start_date} to {sex.end_date})."
                        ),
                    })

        return attrs


class SubstituteActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class ReplacementSubstituteSerializer(serializers.Serializer):
    substitute_id = serializers.IntegerField(required=True)


class ApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveCancelRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")
