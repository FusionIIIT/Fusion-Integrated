from rest_framework import serializers
from django.contrib.auth.models import User
from modules.leave_elm.models import LeaveType, LeaveBalance, LeaveApplication, LeaveAction

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = '__all__'


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'


class LeaveApplicationSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(read_only=True, source='employee')
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.status

    class Meta:
        model = LeaveApplication
        fields = ['employee', 'leave_type_id', 'start_date', 'end_date', 'reason', 'duration', 'status', 'created_by', 'applied_date']


class LeaveActionSerializer(serializers.ModelSerializer):
    leave = serializers.PrimaryKeyRelatedField(read_only=True, source='leave_application')
    actor = serializers.SerializerMethodField()

    def get_actor(self, obj):
        return obj.actor

    class Meta:
        model = LeaveAction
        fields = ['leave', 'actor', 'action_type', 'action_date', 'remarks']