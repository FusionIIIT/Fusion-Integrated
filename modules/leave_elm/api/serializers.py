"""Leave Management serializers."""
from rest_framework import serializers
from datetime import date
from decimal import Decimal
from modules.leave_elm.models import (
    LeaveApplication, LeaveBalance, WorkflowTask,
    SLAEventLog, HolidayCalendar, VacationPeriod,
    OrganizationalUnit, LeaveHierarchy, LeaveHierarchyStep, LeavePolicy
)

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ['id', 'category', 'start_date', 'end_date', 'purpose', 
                  'station_leave_required', 'substitute_user_id', 'status',
                  'final_decision_type', 'final_decision_date', 'created_at']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['effective_date', 'cl_balance', 'rh_balance', 'scl_balance',
                  'el_balance', 'col_balance', 'vl_balance']

class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = ['id', 'task_type', 'assigned_to_user_id', 'status',
                  'reminder_threshold_seconds', 'escalation_threshold_seconds',
                  'last_reminder_sent_at', 'last_escalation_sent_at']

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ['year', 'is_effective', 'created_by_user_id']

class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ['year', 'start_date', 'end_date', 'name']

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ['CL_DAYS', 'RH_DAYS', 'SCL_MAX_DAYS', 'EL_DAYS', 
                  'COL_DAYS', 'VL_DAYS', 'VL_TO_EL_RATIO']
