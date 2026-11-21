from rest_framework import serializers
from modules.elm.models import (
    LeaveBalance,
    LeaveRequest,
    SubstituteAssignment,
    LeaveActionHistory,
)

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            'id',
            'user_id',
            'category',
            'year',
            'credited',
            'availed',
            'balance',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteAssignment
        fields = [
            'id',
            'leave_request_id',
            'substitute_id',
            'status',
            'remarks',
            'responded_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = [
            'id',
            'actor_id',
            'action',
            'comments',
            'created_at',
        ]
        read_only_fields = fields

class LeaveRequestSerializer(serializers.ModelSerializer):
    substitute_assignments = SubstituteAssignmentSerializer(many=True, read_only=True)
    actions = LeaveActionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            'id',
            'user_id',
            'category',
            'start_date',
            'end_date',
            'half_day',
            'leave_days',
            'purpose',
            'status',
            'is_station_leave',
            'destination',
            'emergency_contact',
            'substitute_id',
            'current_reviewer_id',
            'rejection_reason',
            'resumption_date',
            'resumption_status',
            'is_offline_recorded',
            'offline_reference',
            'created_at',
            'updated_at',
            'substitute_assignments',
            'actions',
        ]
        read_only_fields = [
            'id',
            'user_id',
            'leave_days',
            'status',
            'rejection_reason',
            'resumption_status',
            'is_offline_recorded',
            'created_at',
            'updated_at',
            'substitute_assignments',
            'actions',
        ]


class ApplyLeaveInputSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.CharField(max_length=10, required=False, allow_null=True, allow_blank=True)
    purpose = serializers.CharField()
    is_station_leave = serializers.BooleanField(default=False, required=False)
    destination = serializers.CharField(required=False, allow_blank=True, default="")
    emergency_contact = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True)

class SubstituteActionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")

class ReviewActionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject', 'recommend'])
    reason = serializers.CharField(required=False, allow_blank=True, default="")
