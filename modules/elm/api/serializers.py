from rest_framework import serializers
from modules.elm.models import (
    LeaveBalance, LeaveApplication, SubstituteAssignment, ApprovalHistory,
    LeaveCancellation, LeaveExtension, LeaveResumption, OfflineLeaveRecord,
    SLAConfig
)

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = '__all__'

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = '__all__'

class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteAssignment
        fields = '__all__'

class ApprovalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalHistory
        fields = '__all__'

class LeaveCancellationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCancellation
        fields = '__all__'

class LeaveExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveExtension
        fields = '__all__'

class LeaveResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveResumption
        fields = '__all__'

class OfflineLeaveRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineLeaveRecord
        fields = '__all__'

class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfig
        fields = '__all__'