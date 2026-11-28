from rest_framework import serializers
from .models import (
    LeavePolicy, HolidayCalendar, AcademicCalendarVacation, LeaveBalance,
    LeaveApplication, SubstituteRequest, LeaveActionHistory, ResumptionRequest,
    OfflineLeaveRecord, SLAConfig
)


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"


class AcademicCalendarVacationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicCalendarVacation
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"


class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteRequest
        fields = "__all__"


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = "__all__"


class ResumptionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRequest
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    substitute_requests = SubstituteRequestSerializer(many=True, read_only=True)
    action_history = LeaveActionHistorySerializer(many=True, read_only=True)
    resumption = ResumptionRequestSerializer(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = "__all__"


class OfflineLeaveRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineLeaveRecord
        fields = "__all__"


class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfig
        fields = "__all__"
