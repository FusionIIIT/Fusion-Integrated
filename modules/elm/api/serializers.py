from rest_framework import serializers
from modules.elm.models import LeaveType, LeaveBalance, LeaveRequest, LeaveActionLog
from modules.directory.models import UserRef

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = serializers.StringRelatedField()
    user = serializers.StringRelatedField()

    class Meta:
        model = LeaveBalance
        fields = '__all__'

class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class LeaveRequestSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['id', 'status', 'substitute_status', 'created_at', 'updated_at']

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be less than or equal to end date.")
        if data['half_day'] and data['start_date'] != data['end_date']:
            raise serializers.ValidationError("If half day is True, start date must equal end date.")
        if data['half_day'] and not data.get('half_day_period'):
            raise serializers.ValidationError("Half day period must be provided if half day is True.")
        return data

class SubstituteResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['accepted', 'declined'])
    comments = serializers.CharField(required=False, allow_blank=True)

class ApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['recommended', 'not_recommended', 'approved', 'rejected'])
    role_name = serializers.CharField()
    comments = serializers.CharField(required=False, allow_blank=True)