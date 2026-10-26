from rest_framework import serializers
from decimal import Decimal
from modules.leave_elm.models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveAction,
    HolidayCalendar,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            'id',
            'name',
            'code',
            'max_days_per_year',
            'is_carry_forward',
            'is_active',
            'requires_vacation_period',
            'requires_medical_evidence',
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            'id',
            'username',
            'leave_type',
            'leave_type_code',
            'leave_type_name',
            'year',
            'balance',
            'credited',
            'utilized',
        ]


class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = [
            'id',
            'application',
            'actor_username',
            'action',
            'remarks',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class LeaveApplicationReadSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    actions = LeaveActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            'id',
            'applicant_username',
            'leave_type',
            'leave_type_code',
            'leave_type_name',
            'start_date',
            'end_date',
            'half_day',
            'half_day_period',
            'days_count',
            'status',
            'reason',
            'substitute_username',
            'substitute_status',
            'substitute_remarks',
            'station_leave',
            'station_details',
            'unit_head_recommendation',
            'unit_head_remarks',
            'higher_sanction_authority',
            'sanction_remarks',
            'actual_resumption_date',
            'cancellation_reason',
            'is_extension',
            'actions',
            'created_at',
            'updated_at',
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type_code = serializers.CharField(max_length=50)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=['NONE', 'FIRST_HALF', 'SECOND_HALF'],
        default='NONE'
    )
    reason = serializers.CharField(required=False, allow_blank=True, default='')
    substitute_username = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    station_leave = serializers.BooleanField(default=False)
    station_details = serializers.JSONField(required=False, allow_null=True, default=None)


class SubstituteConsentSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class SubstituteNominationSerializer(serializers.Serializer):
    new_substitute_username = serializers.CharField(max_length=150)


class UnitHeadDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVE', 'REJECT', 'RECOMMEND', 'NOT_RECOMMEND'])
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class HigherSanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVE', 'REJECT'])
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField()


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default='')


class YearEndConversionSerializer(serializers.Serializer):
    faculty_username = serializers.CharField(max_length=150)
    year = serializers.IntegerField()


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ['id', 'date', 'name', 'is_restricted_holiday', 'year']