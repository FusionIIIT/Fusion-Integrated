from rest_framework import serializers
from django.db import models
from decimal import Decimal

from modules.leave.models.policy import LeavePolicyParameter, HolidayCalendar
from modules.leave.models.ledger import LeaveBalanceLedger, LeaveLedgerTransaction
from modules.leave.models.requests import (
    LeaveRequest,
    LeaveRequestTransition,
    CancellationRequest,
    ExtensionRequest,
    ResumptionRecord,
    OfflineSanctionRecord,
)
from modules.leave.domain.constants import (
    CL, RH, SCL, EL, VL, COL,
    DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD, AWAITING_ESTABLISHMENT,
    AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION, APPROVED, REJECTED,
    WITHDRAWN, CANCELLATION_PENDING_UNIT_HEAD, CANCELLATION_PENDING_ESTABLISHMENT,
    CANCELLATION_PENDING_FINAL, CANCELLED, CANCELLATION_REJECTED,
    EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL, EXTENSION_APPROVED, EXTENSION_REJECTED,
    EXTENSION_WITHDRAWN, RESUMPTION_PENDING, RESUMPTION_NORMAL,
    RESUMPTION_EARLY, RESUMPTION_LATE,
    EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT,
    SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN, SYSTEM,
)


class LeavePolicyParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicyParameter
        fields = [
            'id', 'category', 'annual_entitlement', 'carry_forward_cap',
            'sla_threshold_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = [
            'id', 'date', 'name', 'is_rh', 'year', 'is_published',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeaveBalanceLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalanceLedger
        fields = [
            'id', 'user_id', 'year', 'category', 'balance', 'credited',
            'utilized', 'carried_forward', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeaveLedgerTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerTransaction
        fields = [
            'id', 'user_id', 'category', 'delta', 'transaction_type',
            'reference_id', 'created_at'
        ]
        read_only_fields = ['created_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    category = serializers.ChoiceField(
        choices=[CL, RH, SCL, EL, VL, COL],
        required=True
    )
    half_day_type = serializers.ChoiceField(
        choices=['none', 'first_half', 'second_half'],
        required=False,
        default='none'
    )
    substitute_status = serializers.ChoiceField(
        choices=['none', 'pending', 'accepted', 'declined'],
        required=False,
        default='none'
    )
    status = serializers.ChoiceField(
        choices=[
            DRAFT, AWAITING_SUBSTITUTE, AWAITING_UNIT_HEAD,
            AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION,
            AWAITING_DIRECTOR_SANCTION, APPROVED, REJECTED, WITHDRAWN
        ],
        required=False,
        default=DRAFT
    )
    is_faculty = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'category', 'start_date', 'end_date', 'half_day_type',
            'chargeable_days', 'purpose', 'station_leave_required',
            'station_leave_details', 'substitute_user_id', 'substitute_status',
            'status', 'is_faculty', 'current_assignee_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'chargeable_days', 'current_assignee_id',
            'created_at', 'updated_at'
        ]

    def validate_category(self, value):
        from modules.leave.domain.constants import (
            CL, RH, SCL, EL, VL, COL
        )
        if value not in [CL, RH, SCL, EL, VL, COL]:
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {CL}, {RH}, {SCL}, {EL}, {VL}, {COL}"
            )
        return value

    def validate_start_date(self, value):
        from datetime import datetime
        if value > datetime.now().date():
            raise serializers.ValidationError(
                "Start date cannot be in the future"
            )
        return value

    def validate_end_date(self, value):
        from datetime import datetime
        if value < datetime.now().date():
            raise serializers.ValidationError(
                "End date cannot be in the past"
            )
        if value < self.validated_data.get('start_date'):
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        return value


class LeaveRequestTransitionSerializer(serializers.ModelSerializer):
    actor_role = serializers.ChoiceField(
        choices=[
            EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT,
            SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN, SYSTEM
        ],
        required=True
    )

    class Meta:
        model = LeaveRequestTransition
        fields = [
            'id', 'leave_request_id', 'from_status', 'to_status',
            'actor_user_id', 'actor_role', 'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationRequest
        fields = [
            'id', 'leave_request', 'reason', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtensionRequest
        fields = [
            'id', 'leave_request', 'requested_end_date',
            'incremental_days', 'substitute_user_id', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ResumptionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRecord
        fields = [
            'id', 'leave_request', 'actual_resumption_date',
            'diff_days', 'status', 'adjustment_applied',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OfflineSanctionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineSanctionRecord
        fields = [
            'id', 'user_id', 'category', 'start_date', 'end_date',
            'chargeable_days', 'sanction_order_ref',
            'recorded_by_user_id', 'created_at'
        ]
        read_only_fields = ['created_at']
