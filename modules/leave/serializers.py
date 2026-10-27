from rest_framework import serializers
from .models import LeaveType, LeaveBalance, Leave


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ['id', 'user', 'leave_type', 'leave_type_code', 'leave_type_name', 'balance', 'year']


class LeaveSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    applicant_name = serializers.CharField(source='user.get_full_name', read_only=True)
    substitute_name = serializers.CharField(source='substitute.get_full_name', read_only=True)

    class Meta:
        model = Leave
        fields = '__all__'
        read_only_fields = ['user', 'status', 'substitute_accepted', 'unit_head_recommendation', 'created_at', 'updated_at']

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})

        # BR-EL-014: Substitute cannot be the applicant
        request = self.context.get('request')
        if request and request.user and data.get('substitute') == request.user:
            raise serializers.ValidationError({"substitute": "You cannot nominate yourself as substitute."})

        return data