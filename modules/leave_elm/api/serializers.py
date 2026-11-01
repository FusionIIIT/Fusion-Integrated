from rest_framework import serializers
from modules.leave_elm.models import LeaveApplication, LeaveBalance, LeaveTask, LeavePolicy, LeaveCalendar

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'user_id', 'status'] + [field.name for field in LeaveApplication._meta.fields if field.name != 'id' and field.name != 'user_id' and field.name != 'status']
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'cancelled_by', 'extension_requested', 'extension_approved', 'extension_start_date', 'extension_end_date', 'extension_approved_by', 'extension_approved_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'


class LeaveTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = '__all__'


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = '__all__'


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = '__all__'